#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
import os
from pathlib import Path

import jubilant
import pytest
import requests
from helpers import (
    charm_resources,
    configure_minio,
    configure_s3_integrator,
    get_grafana_datasources_from_client_pod,
    get_istio_ingress_ip,
    get_prometheus_targets_from_client_pod,
    query_mimir_from_client_pod,
    service_mesh,
)
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
def test_build_and_deploy(juju: jubilant.Juju, mimir_charm: str, cos_channel, mesh_channel):
    """Build the charm-under-test and deploy it together with related charms."""
    juju.deploy(mimir_charm, "mimir", resources=charm_resources(), trust=True)
    juju.deploy("prometheus-k8s", "prometheus", channel=cos_channel, trust=True)
    juju.deploy("grafana-k8s", "grafana", channel=cos_channel, trust=True)
    juju.deploy("grafana-agent-k8s", "agent", channel=cos_channel)
    juju.deploy("istio-k8s", "istio", channel=mesh_channel, trust=True)
    juju.deploy("istio-beacon-k8s", "istio-beacon", channel=mesh_channel, trust=True)
    juju.deploy("istio-ingress-k8s", "istio-ingress", channel=mesh_channel, trust=True)
    # Secret must be at least 8 characters: https://github.com/canonical/minio-operator/issues/137
    juju.deploy(
        "minio",
        channel="ckf-1.9/stable",
        config={"access-key": "access", "secret-key": "secretsecret"},
        trust=True,
    )
    juju.deploy("s3-integrator", "s3", channel="latest/stable", trust=True)

    juju.wait(lambda s: jubilant.all_active(s, "minio"), timeout=1000)
    juju.wait(lambda s: jubilant.all_blocked(s, "s3"), timeout=1000)
    configure_minio(juju)
    configure_s3_integrator(juju)

    juju.wait(
        lambda s: jubilant.all_active(
            s, "prometheus", "grafana", "minio", "s3",
            "istio", "istio-beacon", "istio-ingress",
        ),
        timeout=1000,
    )
    juju.wait(lambda s: jubilant.all_blocked(s, "mimir", "agent"), timeout=1000)


@pytest.mark.abort_on_fail
def test_deploy_workers(juju: jubilant.Juju, cos_channel):
    """Deploy the Mimir workers."""
    if worker_charm := os.environ.get("WORKER_CHARM_PATH"):
        worker_resources = {"mimir-image": "docker.io/ubuntu/mimir:2-22.04"}
        juju.deploy(
            Path(worker_charm),
            "worker",
            resources=worker_resources,
            config={"role-all": True},
            trust=True,
        )
    else:
        juju.deploy(
            "mimir-worker-k8s",
            "worker",
            channel=cos_channel,
            config={"role-all": True},
            trust=True,
        )
    juju.wait(lambda s: jubilant.all_blocked(s, "worker"), timeout=1000)


@pytest.mark.abort_on_fail
def test_integrate(juju: jubilant.Juju):
    juju.integrate("mimir:s3", "s3")
    juju.integrate("mimir:mimir-cluster", "worker")
    juju.integrate("mimir:self-metrics-endpoint", "prometheus")
    juju.integrate("mimir:grafana-dashboards-provider", "grafana")
    juju.integrate("mimir:grafana-source", "grafana")
    juju.integrate("mimir:ingress", "istio-ingress:ingress")
    juju.integrate("mimir:receive-remote-write", "agent")
    juju.integrate("agent:metrics-endpoint", "grafana")

    juju.wait(
        lambda s: jubilant.all_active(
            s, "mimir", "prometheus", "grafana", "agent",
            "minio", "s3", "worker", "istio-ingress",
        ),
        timeout=1000,
        successes=10,
        delay=3,
    )


@pytest.mark.abort_on_fail
def test_enable_service_mesh(juju: jubilant.Juju):
    """Enable service mesh."""
    service_mesh(
        enable=True,
        juju=juju,
        beacon_app_name="istio-beacon",
        apps_to_be_related_with_beacon=["mimir"],
    )


def test_ingress(juju: jubilant.Juju):
    """Check the ingress integration, by checking if Mimir is reachable through the ingress endpoint."""
    model_name = juju.status().model.name
    ingress_address = get_istio_ingress_ip(juju, "istio-ingress")
    proxied_endpoint = f"http://{ingress_address}/{model_name}-mimir"
    response = requests.get(f"{proxied_endpoint}/status")
    assert response.status_code == 200


@retry(wait=wait_fixed(10), stop=stop_after_attempt(6))
def test_grafana_source(juju: jubilant.Juju):
    """Test the grafana-source integration, by checking that Mimir appears in the Datasources when mesh is enabled."""
    source_pod = "grafana/0"
    datasources = get_grafana_datasources_from_client_pod(juju, source_pod)
    assert "mimir" in datasources[0]["name"]


@retry(wait=wait_fixed(10), stop=stop_after_attempt(6))
def test_metrics_endpoint(juju: jubilant.Juju):
    """Check that Mimir appears in the Prometheus Scrape Targets when mesh is enabled."""
    source_pod = "prometheus/0"
    targets = get_prometheus_targets_from_client_pod(juju, source_pod)
    mimir_targets = [
        target
        for target in targets["activeTargets"]
        if target["discoveredLabels"]["juju_charm"] == "mimir-coordinator-k8s"
    ]
    assert mimir_targets


@retry(wait=wait_fixed(10), stop=stop_after_attempt(6))
def test_metrics_in_mimir(juju: jubilant.Juju):
    """Check that the agent metrics appear in Mimir when mesh is enabled."""
    source_pod = "worker/0"
    result = query_mimir_from_client_pod(juju, source_pod, query='up{juju_charm=~"grafana-agent-k8s"}')
    assert result
