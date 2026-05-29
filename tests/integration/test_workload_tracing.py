#!/usr/bin/env python3
# Copyright 2024 Ubuntu
# See LICENSE file for licensing details.

# pyright: reportAttributeAccessIssue=false

import logging

import jubilant
from helpers import (
    charm_resources,
    deploy_swfs,
    deploy_tempo_cluster,
    get_application_ip,
    get_traces_patiently,
)
from jubilant import Juju

APP_NAME = "mimir"
APP_WORKER_NAME = "worker"
TEMPO_APP_NAME = "tempo"
TEMPO_WORKER_APP_NAME = "tempo-worker"

logger = logging.getLogger(__name__)


def test_build_and_deploy(juju: Juju, mimir_charm, cos_channel):
    """Build the charm-under-test and deploy it together with related charms."""
    # deploy charms of interest
    juju.deploy(mimir_charm, app=APP_NAME, resources=charm_resources(), trust=True)
    juju.deploy(
        "mimir-worker-k8s",
        app=APP_WORKER_NAME,
        channel=cos_channel,
        config={"role-all": True},
        trust=True,
    )
    juju.deploy(
        "minio",
        channel="ckf-1.9/stable",
        config={"access-key": "access", "secret-key": "secretsecret"},
    )
    juju.deploy("s3-integrator", app="s3", channel="latest/stable")

    # configure s3 integrator and minio for loki
    juju.wait(lambda status: jubilant.all_active(status, "minio"), timeout=1000)
    juju.wait(lambda status: jubilant.all_blocked(status, "s3"), timeout=1000)
    deploy_swfs(juju)
    juju.integrate(f"{APP_NAME}:s3", "swfs")
    juju.integrate(f"{APP_NAME}:mimir-cluster", APP_WORKER_NAME)

    # deploy Tempo cluster
    deploy_tempo_cluster(juju, cos_channel)

    # wait until charms settle down
    juju.wait(
        lambda status: jubilant.all_agents_idle(status) and jubilant.all_active(
            status, APP_WORKER_NAME, APP_NAME, "minio", "s3", TEMPO_APP_NAME, TEMPO_WORKER_APP_NAME
        ),
        timeout=1000,
    )


def test_workload_traces(juju: Juju):
    # integrate workload-tracing only to not affect search results with charm traces
    juju.integrate(f"{APP_NAME}:workload-tracing", f"{TEMPO_APP_NAME}:tracing")

    juju.wait(
        lambda status: jubilant.all_agents_idle(status) and jubilant.all_active(
            status, APP_NAME, TEMPO_APP_NAME, TEMPO_WORKER_APP_NAME, APP_WORKER_NAME
        ),
        timeout=300,
    )

    # verify workload traces are ingested into Tempo
    assert get_traces_patiently(
        get_application_ip(juju, TEMPO_APP_NAME),
        service_name="mimir",
        tls=False,
    )