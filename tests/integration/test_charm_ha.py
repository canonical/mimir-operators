#!/usr/bin/env python3
# Copyright 2023 Ubuntu
# See LICENSE file for licensing details.

# pyright: reportAttributeAccessIssue=false

import logging

import jubilant
import pytest
import requests
from helpers import (
    charm_resources,
    deploy_swfs,
    get_grafana_datasources_from_client_localhost,
    get_mimir_rules_from_grafana,
    get_prometheus_targets_from_client_localhost,
    get_traefik_proxied_endpoints,
    push_and_verify_exemplars,
    query_mimir_from_client_localhost,
)
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


def test_build_and_deploy(juju: jubilant.Juju, mimir_charm: str, cos_channel):
    """Build the charm-under-test and deploy it together with related charms."""
    juju.deploy(mimir_charm, "mimir", resources=charm_resources(), trust=True, config={"max_global_exemplars_per_user": 100000})
    juju.deploy("prometheus-k8s", "prometheus", channel=cos_channel, trust=True)
    juju.deploy("loki-k8s", "loki", channel=cos_channel, trust=True)
    juju.deploy("grafana-k8s", "grafana", channel=cos_channel, trust=True)
    juju.deploy("traefik-k8s", "traefik", channel="latest/edge", trust=True)
    juju.deploy("opentelemetry-collector-k8s", "otelcol", channel=cos_channel, trust=True)
    deploy_swfs(juju)

    juju.wait(
        lambda s: jubilant.all_active(s, "prometheus", "loki", "grafana", "swfs", "otelcol"),
        timeout=1000,
    )

    juju.integrate("mimir:s3", "swfs")
    juju.wait(lambda s: jubilant.all_blocked(s, "mimir"), timeout=1000)


def test_deploy_workers(juju: jubilant.Juju, cos_channel):
    """Deploy the Mimir workers."""
    juju.deploy(
        "mimir-worker-k8s",
        "worker-read",
        channel=cos_channel,
        config={"role-read": True},
        trust=True,
    )
    juju.deploy(
        "mimir-worker-k8s",
        "worker-write",
        channel=cos_channel,
        config={"role-write": True},
        trust=True,
    )
    juju.deploy(
        "mimir-worker-k8s",
        "worker-backend",
        channel=cos_channel,
        config={"role-backend": True},
        trust=True,
    )
    juju.wait(
        lambda s: jubilant.all_blocked(s, "worker-read", "worker-write", "worker-backend"),
        timeout=1000,
    )


def test_integrate(juju: jubilant.Juju):
    juju.integrate("mimir:mimir-cluster", "worker-read")
    juju.integrate("mimir:mimir-cluster", "worker-write")
    juju.integrate("mimir:mimir-cluster", "worker-backend")
    juju.integrate("mimir:self-metrics-endpoint", "prometheus")
    juju.integrate("mimir:grafana-dashboards-provider", "grafana")
    juju.integrate("mimir:grafana-source", "grafana")
    juju.integrate("mimir:logging-consumer", "loki")
    juju.integrate("mimir:ingress", "traefik")
    juju.integrate("mimir:receive-remote-write", "otelcol:send-remote-write")
    juju.integrate("otelcol:metrics-endpoint", "grafana:metrics-endpoint")

    juju.wait(
        lambda s: jubilant.all_active(
            s, "mimir", "prometheus", "loki", "grafana", "otelcol",
            "swfs", "worker-read", "worker-write", "worker-backend", "traefik",
        ),
        timeout=2000,
    )


@retry(wait=wait_fixed(10), stop=stop_after_attempt(6))
def test_grafana_source(juju: jubilant.Juju):
    """Test the grafana-source integration, by checking that Mimir appears in the Datasources."""
    datasources = get_grafana_datasources_from_client_localhost(juju)
    assert "mimir" in datasources[0]["name"]


@retry(wait=wait_fixed(20), stop=stop_after_attempt(10))
def test_mimir_rules_from_grafana(juju: jubilant.Juju):
    """Test that Mimir alert rules can be queried through Grafana's Prometheus API.

    This validates the nginx routing in the Mimir coordinator correctly handles
    the /prometheus/api/v1/rules endpoint that Grafana uses to fetch alert rules.
    """
    result = get_mimir_rules_from_grafana(juju)
    assert result["status"] == "success"


@retry(wait=wait_fixed(10), stop=stop_after_attempt(6))
def test_metrics_endpoint(juju: jubilant.Juju):
    """Check that Mimir appears in the Prometheus Scrape Targets."""
    targets = get_prometheus_targets_from_client_localhost(juju)
    mimir_targets = [
        target
        for target in targets["activeTargets"]
        if target["discoveredLabels"]["juju_charm"] == "mimir-coordinator-k8s"
    ]
    assert mimir_targets


@retry(wait=wait_fixed(10), stop=stop_after_attempt(6))
def test_metrics_in_mimir(juju: jubilant.Juju):
    """Check that otelcol-scraped metrics appear in Mimir."""
    result = query_mimir_from_client_localhost(juju, query='up{juju_charm=~"grafana-k8s"}')
    assert result


@retry(wait=wait_fixed(10), stop=stop_after_attempt(6))
def test_traefik(juju: jubilant.Juju):
    """Check the ingress integration, by checking if Mimir is reachable through Traefik."""
    proxied_endpoints = get_traefik_proxied_endpoints(juju)
    assert "mimir" in proxied_endpoints

    response = requests.get(f"{proxied_endpoints['mimir']['url']}/status")
    assert response.status_code == 200


def test_exemplars(juju: jubilant.Juju):
    """Check that Mimir successfully receives and stores exemplars."""
    push_and_verify_exemplars(juju, coordinator_app="mimir")
