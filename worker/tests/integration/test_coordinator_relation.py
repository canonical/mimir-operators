#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import json
import logging
from types import SimpleNamespace

import pytest
import pytimeparse
import yaml
from helpers import get_address, oci_image
from pytest_operator.plugin import OpsTest
from workload import Mimir

logger = logging.getLogger(__name__)

mimir_worker = SimpleNamespace(
    name="mimir-worker", resources={"mimir-image": oci_image("./metadata.yaml", "mimir-image")}
)
mimir_coordinator = SimpleNamespace(charm="mimir-coordinator-k8s", name="mimir-coordinator")


@pytest.mark.abort_on_fail
async def test_deploy_and_relate_to_coordinator(ops_test: OpsTest, mimir_charm):
    """Test that Mimir Worker can be related with Mimir coordinator."""
    # Build charm from local source folder
    # mimir_charm = await ops_test.build_charm(".")
    await asyncio.gather(
        ops_test.model.deploy(
            mimir_charm,
            resources=mimir_worker.resources,
            application_name=mimir_worker.name,
            trust=True,
        ),
        ops_test.model.deploy(
            mimir_coordinator.charm,
            application_name=mimir_coordinator.name,
            channel="edge",
        ),
    )

    await ops_test.model.add_relation(f"{mimir_worker.name}:mimir-worker", mimir_coordinator.name)
    await ops_test.model.wait_for_idle(status="active")
