#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

# pyright: reportAttributeAccessIssue=false

import logging

import jubilant
from helpers import (
    charm_resources,
    deploy_swfs,
    get_replication_factor,
    get_worker_rendered_config,
    push_and_verify_metric,
    verify_metric_queryable,
)
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

# Set by test_baseline_push_and_query_and_replication_factor, read by later tests to confirm
# the metric pushed before scaling survives the write-unit churn.
baseline_metric: str = ""


def test_build_and_deploy(juju: jubilant.Juju, mimir_charm: str, cos_channel):
    """Build the charm-under-test and deploy it with 3 worker-write, 1 read, 1 backend."""
    juju.deploy(mimir_charm, "mimir", resources=charm_resources(), trust=True)
    juju.deploy("opentelemetry-collector-k8s", "otelcol", channel=cos_channel, trust=True)
    deploy_swfs(juju)
    juju.wait(lambda s: jubilant.all_active(s, "swfs", "otelcol"), timeout=1000)

    juju.integrate("mimir:s3", "swfs")
    juju.integrate("mimir:receive-remote-write", "otelcol:send-remote-write")
    juju.wait(lambda s: jubilant.all_blocked(s, "mimir"), timeout=1000)

    juju.deploy(
        "mimir-worker-k8s",
        "worker-write",
        channel=cos_channel,
        config={"role-write": True},
        num_units=3,
        trust=True,
    )
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

    juju.integrate("mimir:mimir-cluster", "worker-read")
    juju.integrate("mimir:mimir-cluster", "worker-write")
    juju.integrate("mimir:mimir-cluster", "worker-backend")

    juju.wait(
        lambda s: jubilant.all_active(
            s, "mimir", "swfs", "otelcol", "worker-read", "worker-write", "worker-backend"
        ),
        timeout=2000,
    )


@retry(wait=wait_fixed(10), stop=stop_after_attempt(10))
def test_baseline_push_and_query_and_replication_factor(juju: jubilant.Juju):
    """With 3/3 healthy write units, push+query work and replication_factor is 3."""
    global baseline_metric  # noqa: PLW0603
    baseline_metric = push_and_verify_metric(juju, coordinator_app="mimir")

    config = get_worker_rendered_config(juju, "worker-write/0")
    assert get_replication_factor(config, "ingester") == 3


def test_removing_one_write_unit_keeps_mimir_available(juju: jubilant.Juju):
    """Losing 1 of 3 write units must not disrupt writes/queries or drop replication_factor."""
    juju.cli("remove-unit", "worker-write", "--num-units", "1")

    juju.wait(
        lambda s: jubilant.all_active(s, "mimir", "worker-read", "worker-write", "worker-backend")
        and len(s.apps["worker-write"].units) == 2,
        timeout=1000,
    )

    push_and_verify_metric(juju, coordinator_app="mimir")
    verify_metric_queryable(juju, baseline_metric, coordinator_app="mimir")

    config = get_worker_rendered_config(juju, "worker-write/0")
    assert get_replication_factor(config, "ingester") == 3


def test_adding_the_unit_back_keeps_mimir_available(juju: jubilant.Juju):
    """Scaling back up to 3 write units must not cause a second disruption either."""
    juju.cli("add-unit", "worker-write")

    juju.wait(
        lambda s: jubilant.all_active(s, "mimir", "worker-read", "worker-write", "worker-backend")
        and len(s.apps["worker-write"].units) == 3,
        timeout=1000,
    )

    push_and_verify_metric(juju, coordinator_app="mimir")
    verify_metric_queryable(juju, baseline_metric, coordinator_app="mimir")

    config = get_worker_rendered_config(juju, "worker-write/0")
    assert get_replication_factor(config, "ingester") == 3
