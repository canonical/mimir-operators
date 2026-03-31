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
    configure_minio,
    configure_s3_integrator,
    get_grafana_datasources_from_client_localhost,
    get_prometheus_targets_from_client_localhost,
    get_traefik_proxied_endpoints,
    push_to_otelcol,
    query_exemplars,
    query_mimir_from_client_localhost,
    wait_for_active_or_resolve,
)
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
def test_build_and_deploy(juju: jubilant.Juju, mimir_charm: str, cos_channel):
    """Build the charm-under-test and deploy it together with related charms."""
    juju.deploy(
        mimir_charm,
        "mimir",
        config={"max_global_exemplars_per_user": 100000},
        num_units=3,
        resources=charm_resources(),
        trust=True,
    )
    juju.deploy("prometheus-k8s", "prometheus", channel=cos_channel, trust=True)
    juju.deploy("loki-k8s", "loki", channel=cos_channel, trust=True)
    juju.deploy("grafana-k8s", "grafana", channel=cos_channel, trust=True)
    juju.deploy("grafana-agent-k8s", "agent", channel=cos_channel, trust=True)
    juju.deploy("traefik-k8s", "traefik", channel="latest/edge", trust=True)
    juju.deploy("opentelemetry-collector-k8s", "otelcol", trust=True, channel=cos_channel)
    # Secret must be at least 8 characters: https://github.com/canonical/minio-operator/issues/137
    juju.deploy(
        "minio",
        channel="ckf-1.9/stable",
        config={"access-key": "access", "secret-key": "secretsecret"},
    )
    juju.deploy("s3-integrator", "s3", channel="latest/stable")

    juju.wait(lambda s: jubilant.all_active(s, "minio"), timeout=1000)
    juju.wait(lambda s: jubilant.all_blocked(s, "s3"), timeout=1000)
    configure_minio(juju)
    configure_s3_integrator(juju)

    juju.wait(
        lambda s: jubilant.all_active(s, "prometheus", "loki", "grafana", "minio", "s3", "otelcol"),
        timeout=1000,
    )
    juju.wait(lambda s: jubilant.all_blocked(s, "mimir", "agent"), timeout=1000)


@pytest.mark.abort_on_fail
def test_deploy_workers(juju: jubilant.Juju, cos_channel):
    """Deploy the Mimir workers."""
    juju.deploy(
        "mimir-worker-k8s",
        "worker-read",
        channel=cos_channel,
        config={"role-read": True},
        num_units=1,
        trust=True,
    )
    juju.deploy(
        "mimir-worker-k8s",
        "worker-write",
        channel=cos_channel,
        config={"role-write": True},
        num_units=1,
        trust=True,
    )
    juju.deploy(
        "mimir-worker-k8s",
        "worker-backend",
        channel=cos_channel,
        config={"role-backend": True},
        num_units=1,
        trust=True,
    )
    juju.wait(
        lambda s: jubilant.all_blocked(s, "worker-read", "worker-write", "worker-backend"),
        timeout=1000,
    )


@pytest.mark.abort_on_fail
def test_integrate(juju: jubilant.Juju):
    juju.integrate("mimir:s3", "s3")
    juju.integrate("mimir:mimir-cluster", "worker-read")
    juju.integrate("mimir:mimir-cluster", "worker-write")
    juju.integrate("mimir:mimir-cluster", "worker-backend")
    juju.integrate("mimir:self-metrics-endpoint", "prometheus")
    juju.integrate("mimir:grafana-dashboards-provider", "grafana")
    juju.integrate("mimir:grafana-source", "grafana")
    juju.integrate("mimir:logging-consumer", "loki")
    juju.integrate("mimir:ingress", "traefik")
    juju.integrate("mimir:receive-remote-write", "agent")
    juju.integrate("agent:metrics-endpoint", "grafana")
    juju.integrate("mimir:receive-remote-write", "otelcol:send-remote-write")

    wait_for_active_or_resolve(
        juju,
        "mimir", "prometheus", "loki", "grafana", "agent",
        "minio", "s3", "worker-read", "worker-write", "worker-backend", "traefik",
        timeout=2000,
    )


def test_scale_workers(juju: jubilant.Juju):
    """Scale the Mimir workers to 3 units each."""
    juju.cli("scale-application", "worker-read", "3")
    juju.cli("scale-application", "worker-write", "3")
    juju.cli("scale-application", "worker-backend", "3")
    wait_for_active_or_resolve(
        juju,
        "worker-read", "worker-write", "worker-backend",
        timeout=1000,
    )


@retry(wait=wait_fixed(10), stop=stop_after_attempt(6))
def test_grafana_source(juju: jubilant.Juju):
    """Test the grafana-source integration, by checking that Mimir appears in the Datasources."""
    datasources = get_grafana_datasources_from_client_localhost(juju)
    mimir_datasources = ["mimir" in d["name"] for d in datasources]
    assert any(mimir_datasources)
    assert len(mimir_datasources) == 1


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
    """Check that the agent metrics appear in Mimir."""
    result = query_mimir_from_client_localhost(juju, query='up{juju_charm=~"grafana-agent-k8s"}')
    assert result


def test_traefik(juju: jubilant.Juju):
    """Check the ingress integration, by checking if Mimir is reachable through Traefik."""
    proxied_endpoints = get_traefik_proxied_endpoints(juju)
    assert "mimir" in proxied_endpoints

    response = requests.get(f"{proxied_endpoints['mimir']['url']}/status")
    assert response.status_code == 200


def test_exemplars(juju: jubilant.Juju):
    """Check that Mimir successfully receives and stores exemplars."""
    metric_name = "sample_metric"
    trace_id = push_to_otelcol(juju, metric_name=metric_name)

    found_trace_id = query_exemplars(
        juju, query_name=metric_name, coordinator_app="mimir"
    )
    assert found_trace_id == trace_id
