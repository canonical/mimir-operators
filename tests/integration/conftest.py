#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
import os
import subprocess
from pathlib import Path

import jubilant
import pytest

from helpers import Terraform

logger = logging.getLogger(__name__)


# ── Jubilant-based fixtures (non-Terraform tests) ────────


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


# ── Terraform-based fixtures ─────────────────────────────
#
# Test modules that deploy via Terraform should define a module-scoped
# ``tf_dir`` fixture returning a ``Path`` to their Terraform directory,
# and then override ``juju`` locally:
#
#     @pytest.fixture(scope="module")
#     def tf_dir():
#         return Path(__file__).parent / "terraform_monolithic"
#
#     # Override the default juju fixture with the Terraform-aware one.
#     juju = tf_juju
#


@pytest.fixture(scope="module")
def terraform(tf_dir: Path, request: pytest.FixtureRequest):
    """Run ``terraform init`` + ``apply``; on teardown run ``destroy`` and clean up.

    Requires a module-scoped ``tf_dir`` fixture that returns the path to a
    Terraform working directory.  The TF configuration is expected to create
    its own ``juju_model`` resource and expose a ``model_name`` output.
    """
    tf = Terraform(tf_dir)
    tf.run("init")
    tf.run("apply", "-auto-approve")
    yield tf
    keep = request.config.getoption("--keep-models", default=False)
    if not keep:
        tf.run("destroy", "-auto-approve", check=False)
        tf.cleanup()


@pytest.fixture(scope="module")
def tf_juju(terraform: Terraform, request: pytest.FixtureRequest):
    """Return a Juju handle pointed at the Terraform-managed model.

    The ``terraform`` fixture is declared as a dependency so that the model
    is guaranteed to exist before any test tries to interact with it.

    To use this in a test module, alias it to ``juju``::

        juju = tf_juju
    """
    model_name = terraform.output("model_name")
    juju = jubilant.Juju(model=model_name)
    juju.wait_timeout = 30 * 60
    yield juju
    if request.session.testsfailed:
        log = juju.debug_log(limit=1000)
        print(log, end="")
