#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
import os
import subprocess
from pathlib import Path

import jubilant
import pytest

logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    parser.addoption("--keep-models", action="store_true", default=False, help="Keep Juju models after tests")


@pytest.fixture(scope="module")
def juju(request: pytest.FixtureRequest):
    keep = request.config.getoption("--keep-models")
    with jubilant.temp_model(keep=keep) as juju:
        juju.wait_timeout = 30 * 60
        yield juju
        if request.session.testsfailed:
            log = juju.debug_log(limit=1000)
            print(log, end="")


@pytest.fixture(scope="session")
def cos_channel():
    return "dev/edge"


@pytest.fixture(scope="session")
def mesh_channel():
    return "2/edge"


@pytest.fixture(scope="session")
def mimir_charm():
    """Mimir charm used for integration testing."""
    if charm_file := os.environ.get("CHARM_PATH"):
        return charm_file

    coordinator_dir = Path(__file__).resolve().parents[2] / "coordinator"
    result = subprocess.run(
        ["charmcraft", "pack"], cwd=coordinator_dir, capture_output=True, text=True,
    )
    if result.returncode != 0:
        logger.error("charmcraft pack failed (cwd=%s):\n%s\n%s", coordinator_dir, result.stdout, result.stderr)
        result.check_returncode()
    charm_files = sorted(coordinator_dir.glob("*.charm"))
    assert charm_files, "No .charm file found after charmcraft pack"
    return str(charm_files[-1].resolve())
