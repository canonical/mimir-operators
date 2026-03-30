#!/usr/bin/env python3
# Copyright 2023 Ubuntu
# See LICENSE file for licensing details.

# pyright: reportAttributeAccessIssue=false

import logging

import jubilant
import pytest
from helpers import (
    charm_resources,
    configure_minio,
    configure_s3_integrator,
)

logger = logging.getLogger(__name__)

ROLES = [
    "alertmanager",
    "compactor",
    "distributor",
    "flusher",
    "ingester",
    "overrides-exporter",
    "querier",
    "query-frontend",
    "query-scheduler",
    "ruler",
    "store-gateway",
]
WORKER_APPS = [f"worker-{role}" for role in ROLES]


@pytest.mark.abort_on_fail
def test_build_and_deploy(juju: jubilant.Juju, mimir_charm: str, cos_channel):
    """Build the charm-under-test and deploy it together with related charms."""
    juju.deploy(mimir_charm, "mimir", resources=charm_resources(), trust=True)
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

    juju.wait(lambda s: jubilant.all_active(s, "minio", "s3"), timeout=1000)
    juju.wait(lambda s: jubilant.all_blocked(s, "mimir"), timeout=1000)


@pytest.mark.abort_on_fail
def test_deploy_workers(juju: jubilant.Juju, cos_channel):
    """Deploy one Mimir worker per individual role."""
    for role in ROLES:
        juju.deploy(
            "mimir-worker-k8s",
            f"worker-{role}",
            channel=cos_channel,
            config={f"role-{role}": True},
            trust=True,
        )
    juju.wait(lambda s: jubilant.all_blocked(s, *WORKER_APPS), timeout=1000)


@pytest.mark.abort_on_fail
def test_integrate(juju: jubilant.Juju):
    """Integrate all workers with the coordinator and wait for active/idle."""
    juju.integrate("mimir:s3", "s3")
    for app in WORKER_APPS:
        juju.integrate("mimir:mimir-cluster", app)

    juju.wait(
        lambda s: jubilant.all_active(s, "mimir", "minio", "s3", *WORKER_APPS),
        timeout=2000,
    )
