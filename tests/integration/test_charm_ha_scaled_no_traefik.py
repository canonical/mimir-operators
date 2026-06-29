#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# pyright: reportAttributeAccessIssue=false

"""HA scaled test without traefik, for debugging flaky deploy issues."""

import logging

import jubilant
import pytest
from helpers import (
    charm_resources,
    deploy_swfs,
)

logger = logging.getLogger(__name__)


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
    juju.deploy("opentelemetry-collector-k8s", "otelcol", channel=cos_channel, trust=True)
    deploy_swfs(juju)

    juju.wait(
        lambda s: jubilant.all_active(s, "swfs", "otelcol"),
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


def test_integrate(juju: jubilant.Juju):
    juju.integrate("mimir:mimir-cluster", "worker-read")
    juju.integrate("mimir:mimir-cluster", "worker-write")
    juju.integrate("mimir:mimir-cluster", "worker-backend")
    juju.integrate("mimir:receive-remote-write", "otelcol:send-remote-write")

    juju.wait(
        lambda s: jubilant.all_active(
            s, "mimir", "swfs",
            "worker-read", "worker-write", "worker-backend",
        ),
        timeout=2000,
    )


def test_scale_workers(juju: jubilant.Juju):
    """Scale the Mimir workers to 3 units each."""
    juju.cli("scale-application", "worker-read", "3")
    juju.cli("scale-application", "worker-write", "3")
    juju.cli("scale-application", "worker-backend", "3")
    juju.wait(
        lambda s: jubilant.all_active(s, "worker-read", "worker-write", "worker-backend"),
        timeout=1000,
    )
