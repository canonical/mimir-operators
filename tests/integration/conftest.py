#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
import os
import subprocess
from pathlib import Path
from typing import Literal, Optional, Tuple

import jubilant
import pytest

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
_BUILD_RETRIES = 3


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


def _charm_and_channel_and_resources(
    role: Literal["coordinator", "worker"],
    charm_path_key: str,
    charm_channel_key: str,
) -> Tuple[Optional[Path], Optional[str], Optional[dict]]:
    """Return a (charm_path, channel, resources) tuple for the given Mimir role.

    The return value is used by upgrade tests to either refresh from a channel
    or from a locally built charm file, mirroring the approach in
    https://github.com/canonical/loki-operators/pull/25.

    Precedence:
      1. ``charm_channel_key`` env var  → refresh from that Charmhub channel.
      2. ``charm_path_key`` env var     → refresh from that local ``.charm`` file.
      3. Build from source via ``charmcraft pack``.
    """
    from helpers import charm_resources

    charm_name = f"mimir-{role}-k8s"
    metadata_file = str(REPO_ROOT / role / "charmcraft.yaml")

    if channel := os.environ.get(charm_channel_key):
        logger.info("Using published %s charm from channel %s", charm_name, channel)
        return charm_name, channel, None

    if charm_file := os.environ.get(charm_path_key):
        charm_path = Path(charm_file).absolute()
        logger.info("Using local %s charm: %s", role, charm_path)
        return charm_path, None, charm_resources(metadata_file)

    for _ in range(_BUILD_RETRIES):
        logger.info("Packing Mimir %s charm...", role)
        try:
            subprocess.run(
                ["charmcraft", "pack"],
                check=True,
                cwd=str(REPO_ROOT / role),
            )
        except subprocess.CalledProcessError:
            logger.warning("Failed to build Mimir %s charm. Trying again!", role)
            continue
        charm_files = sorted((REPO_ROOT / role).glob("*.charm"))
        if charm_files:
            charm_path = charm_files[-1].resolve()
            return charm_path, None, charm_resources(metadata_file)

    raise subprocess.CalledProcessError(1, f"charmcraft pack {role}")


@pytest.fixture(scope="session")
def coordinator_charm():
    """Mimir coordinator charm used for integration testing.

    Returns a ``(charm_path_or_name, channel_or_none, resources_or_none)`` tuple
    consumed by upgrade tests to refresh the deployed coordinator.
    """
    return _charm_and_channel_and_resources(
        "coordinator", "COORDINATOR_CHARM_PATH", "COORDINATOR_CHARM_CHANNEL"
    )


@pytest.fixture(scope="session")
def worker_charm():
    """Mimir worker charm used for integration testing.

    Returns a ``(charm_path_or_name, channel_or_none, resources_or_none)`` tuple
    consumed by upgrade tests to refresh the deployed worker.
    """
    return _charm_and_channel_and_resources(
        "worker", "WORKER_CHARM_PATH", "WORKER_CHARM_CHANNEL"
    )
