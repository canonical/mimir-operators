#!/usr/bin/env python3
# Copyright 2023 Ubuntu
# See LICENSE file for licensing details.

# pyright: reportAttributeAccessIssue=false

import asyncio
import logging

import pytest
from helpers import (
    charm_resources,
    configure_minio,
    configure_s3_integrator,
    deploy_tempo_cluster,
    get_application_ip,
    get_traces_patiently,
)
from pytest_operator.plugin import OpsTest

APP_NAME = "mimir"
APP_WORKER_NAME = "worker"
TEMPO_APP_NAME = "tempo"
TEMPO_WORKER_APP_NAME = "tempo-worker"
SSC = "self-signed-certificates"
SSC_APP_NAME = "ssc"

logger = logging.getLogger(__name__)


@pytest.mark.setup
@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest, worker_charm: str):
    """Build the charm-under-test and deploy it together with related charms."""
    assert ops_test.model
    # deploy charms of interest
    await asyncio.gather(
        ops_test.model.deploy("mimir-coordinator-k8s", APP_NAME, channel="latest/edge"),
        ops_test.model.deploy(
            worker_charm,
            APP_WORKER_NAME,
            config={"role-all": True},
            resources=charm_resources(),
        ),
        ops_test.model.deploy(
            "minio",
            channel="ckf-1.9/stable",
            config={"access-key": "access", "secret-key": "secretsecret"},
        ),
        ops_test.model.deploy("s3-integrator", "s3", channel="latest/stable"),
    )

    # configure s3 integrator and minio for mimir
    await ops_test.model.wait_for_idle(apps=["minio"], status="active")
    await ops_test.model.wait_for_idle(apps=["s3"], status="blocked")
    await configure_minio(ops_test)
    await configure_s3_integrator(ops_test)
    await asyncio.gather(
        ops_test.model.integrate(f"{APP_NAME}:s3", "s3"),
        ops_test.model.integrate(f"{APP_NAME}:mimir-cluster", APP_WORKER_NAME),
    )

    # deploy Tempo cluster
    await deploy_tempo_cluster(ops_test)

    # wait until charms settle down
    await ops_test.model.wait_for_idle(
        apps=[APP_WORKER_NAME, APP_NAME, "minio", "s3", TEMPO_APP_NAME, TEMPO_WORKER_APP_NAME],
        status="active",
        timeout=1000,
    )


@pytest.mark.abort_on_fail
async def test_workload_traces(ops_test):
    # integrate workload-tracing only to not affect search results with charm traces
    await ops_test.model.integrate(f"{APP_NAME}:workload-tracing", f"{TEMPO_APP_NAME}:tracing")

    # stimulate mimir to generate traces
    await ops_test.model.integrate(
        f"{APP_NAME}:receive-remote-write", f"{TEMPO_APP_NAME}:send-remote-write"
    )

    await ops_test.model.wait_for_idle(
        apps=[APP_NAME, TEMPO_APP_NAME, TEMPO_WORKER_APP_NAME, APP_WORKER_NAME],
        status="active",
        timeout=300,
    )

    # verify workload traces are ingested into Tempo
    assert await get_traces_patiently(
        await get_application_ip(ops_test, TEMPO_APP_NAME),
        service_name="mimir-all",
        tls=False,
    )
