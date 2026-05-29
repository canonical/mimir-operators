#!/usr/bin/env python3
# Copyright 2023 Ubuntu
# See LICENSE file for licensing details.

# pyright: reportAttributeAccessIssue=false

import logging

import jubilant
import pytest
from helpers import (
    charm_resources,
    deploy_swfs,
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


def test_build_and_deploy(juju: jubilant.Juju, mimir_charm: str, cos_channel):
    """Build the charm-under-test and deploy it together with related charms."""
    juju.deploy(mimir_charm, "mimir", resources=charm_resources(), trust=True)
    deploy_swfs(juju)

    juju.wait(lambda s: jubilant.all_active(s, "swfs"), timeout=1000)

    juju.integrate("mimir:s3", "swfs")
    juju.wait(lambda s: jubilant.all_blocked(s, "mimir"), timeout=1000)


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


def test_integrate(juju: jubilant.Juju):
    """Integrate all workers with the coordinator and wait for active/idle."""
    for app in WORKER_APPS:
        juju.integrate("mimir:mimir-cluster", app)

    juju.wait(
        lambda s: jubilant.all_active(s, "mimir", "swfs", *WORKER_APPS),
        timeout=2000,
    )
