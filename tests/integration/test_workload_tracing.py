#!/usr/bin/env python3
# Copyright 2023 Ubuntu
# See LICENSE file for licensing details.

# pyright: reportAttributeAccessIssue=false

import logging
import os
from pathlib import Path

import jubilant
import pytest
from helpers import (
    REPO_ROOT,
    charm_resources,
    configure_minio,
    configure_s3_integrator,
    deploy_tempo_cluster,
    get_application_ip,
    get_traces_patiently,
)

APP_NAME = "mimir"
APP_WORKER_NAME = "worker"
TEMPO_APP_NAME = "tempo"
TEMPO_WORKER_APP_NAME = "tempo-worker"

logger = logging.getLogger(__name__)


@pytest.mark.setup
@pytest.mark.abort_on_fail
def test_build_and_deploy(juju: jubilant.Juju):
    """Build the charm-under-test and deploy it together with related charms."""
    juju.deploy("mimir-coordinator-k8s", app=APP_NAME, channel="2/edge", trust=True)

    if worker_charm := os.environ.get("WORKER_CHARM_PATH"):
        worker_resources = charm_resources(str(REPO_ROOT / "worker" / "charmcraft.yaml"))
        juju.deploy(
            Path(worker_charm),
            app=APP_WORKER_NAME,
            config={"role-all": True},
            resources=worker_resources,
            trust=True,
        )
    else:
        juju.deploy(
            "mimir-worker-k8s",
            app=APP_WORKER_NAME,
            channel="2/edge",
            config={"role-all": True},
            trust=True,
        )

    juju.deploy(
        "minio",
        channel="ckf-1.9/stable",
        config={"access-key": "access", "secret-key": "secretsecret"},
    )
    juju.deploy("s3-integrator", app="s3", channel="latest/stable")

    # configure s3 integrator and minio for mimir
    juju.wait(lambda s: jubilant.all_active(s, "minio"), timeout=1000)
    juju.wait(lambda s: jubilant.all_blocked(s, "s3"), timeout=300)
    configure_minio(juju)
    configure_s3_integrator(juju)

    juju.integrate(f"{APP_NAME}:s3", "s3")
    juju.integrate(f"{APP_NAME}:mimir-cluster", APP_WORKER_NAME)

    # deploy Tempo cluster
    deploy_tempo_cluster(juju)

    # wait until charms settle down
    juju.wait(
        lambda s: jubilant.all_active(
            s, APP_WORKER_NAME, APP_NAME, "minio", "s3",
            TEMPO_APP_NAME, TEMPO_WORKER_APP_NAME,
        ),
        timeout=1000,
    )


@pytest.mark.skip(
    "tracing-relation-joined fails - "
    "https://github.com/canonical/cos-coordinated-workers/issues/19"
)
def test_workload_traces(juju: jubilant.Juju):
    # integrate workload-tracing only to not affect search results with charm traces
    juju.integrate(f"{APP_NAME}:workload-tracing", f"{TEMPO_APP_NAME}:tracing")

    # stimulate mimir to generate traces
    juju.integrate(
        f"{APP_NAME}:receive-remote-write", f"{TEMPO_APP_NAME}:send-remote-write"
    )

    juju.wait(
        lambda s: jubilant.all_active(
            s, APP_NAME, TEMPO_APP_NAME, TEMPO_WORKER_APP_NAME, APP_WORKER_NAME,
        ),
        timeout=300,
    )

    # verify workload traces are ingested into Tempo
    assert get_traces_patiently(
        get_application_ip(juju, TEMPO_APP_NAME),
        service_name="mimir-all",
        tls=False,
    )
