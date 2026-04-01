#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# pyright: reportAttributeAccessIssue=false

"""Upgrade integration test: deploy from channel, refresh to locally built charms."""

import logging

import jubilant
import pytest
from helpers import (
    configure_minio,
    configure_s3_integrator,
    query_mimir_from_client_localhost,
)
from jubilant import Juju
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


@pytest.mark.setup
def test_deploy_from_channel(juju: Juju, cos_channel):
    """Deploy the coordinator and infrastructure from the channel."""
    juju.deploy(
        "mimir-coordinator-k8s",
        app="mimir",
        channel=cos_channel,
        trust=True,
    )
    juju.deploy(
        "minio",
        channel="ckf-1.9/stable",
        config={"access-key": "access", "secret-key": "secretsecret"},
        trust=True,
    )
    juju.deploy("s3-integrator", app="s3", channel="latest/stable", trust=True)
    juju.deploy(
        "grafana-agent-k8s",
        app="agent",
        channel=cos_channel,
        trust=True,
    )

    juju.wait(lambda status: jubilant.all_active(status, "minio"), timeout=1000)
    juju.wait(lambda status: jubilant.all_blocked(status, "s3"), timeout=1000)
    configure_minio(juju)
    configure_s3_integrator(juju)

    juju.wait(
        lambda status: jubilant.all_active(status, "minio", "s3"),
        timeout=1000,
    )
    juju.wait(lambda status: jubilant.all_blocked(status, "mimir"), timeout=1000)


@pytest.mark.setup
def test_deploy_worker_from_channel(juju: Juju, cos_channel):
    """Deploy the Mimir worker from the channel."""
    juju.deploy(
        "mimir-worker-k8s",
        app="worker",
        channel=cos_channel,
        config={"role-all": True},
        trust=True,
    )
    juju.wait(lambda status: jubilant.all_blocked(status, "worker"), timeout=1000)


@pytest.mark.setup
def test_integrate(juju: Juju):
    """Set up the integrations between all applications."""
    juju.integrate("mimir:s3", "s3")
    juju.integrate("mimir:mimir-cluster", "worker")
    juju.integrate("mimir:receive-remote-write", "agent")

    juju.wait(
        lambda status: jubilant.all_active(
            status, "mimir", "minio", "s3", "worker", "agent"
        ),
        timeout=2000,
    )


@pytest.mark.setup
def test_upgrade(juju: Juju, coordinator_charm, worker_charm):
    """Refresh the coordinator and worker from the locally built charms."""
    coord_charm, coord_channel, coord_resources = coordinator_charm
    if coord_channel:
        juju.refresh("mimir", channel=coord_channel)
    else:
        juju.refresh("mimir", path=coord_charm, resources=coord_resources)

    wkr_charm, wkr_channel, wkr_resources = worker_charm
    if wkr_channel:
        juju.refresh("worker", channel=wkr_channel)
    else:
        juju.refresh("worker", path=wkr_charm, resources=wkr_resources)

    juju.wait(
        lambda status: jubilant.all_active(
            status, "mimir", "minio", "s3", "worker", "agent"
        ),
        timeout=2000,
    )


@retry(wait=wait_fixed(10), stop=stop_after_attempt(6))
def test_metrics_in_mimir(juju: Juju):
    """Check that metrics are still accessible in Mimir after the upgrade."""
    result = query_mimir_from_client_localhost(
        juju, query='up{juju_charm=~"grafana-agent-k8s"}'
    )
    assert result
