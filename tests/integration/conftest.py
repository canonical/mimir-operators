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


@pytest.fixture(scope="module")
def juju(request: pytest.FixtureRequest):
    keep = request.config.getoption("--keep-models", default=False)
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

    subprocess.run(["charmcraft", "pack"], check=True)
    charm_files = sorted(Path(".").glob("*.charm"))
    assert charm_files, "No .charm file found after charmcraft pack"
    return str(charm_files[-1].resolve())
