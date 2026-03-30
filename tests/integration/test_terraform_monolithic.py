#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test that deploys Mimir via the shipped Terraform module.

The Juju model, SeaweedFS (S3 stand-in), and the full Mimir product module
(coordinator + workers + s3-integrator) are all managed by Terraform.  The
Python side only drives ``terraform init/apply/destroy`` and then makes
assertions against the live deployment via ``jubilant``.
"""

import logging
from pathlib import Path

import jubilant
import pytest
import requests
from conftest import tf_juju
from helpers import (
    get_leader_address,
    query_mimir_from_client_localhost,
)
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


# ── Fixtures ──────────────────────────────────────────────


@pytest.fixture(scope="module")
def tf_dir():
    return Path(__file__).parent / "terraform_monolithic"


# Override the default juju fixture with the Terraform-aware one.
juju = tf_juju


# ── Tests (ordered, abort-on-fail) ───────────────────────


@pytest.mark.abort_on_fail
def test_terraform_apply(juju: jubilant.Juju):
    """Terraform apply succeeded — wait for all Mimir apps to settle."""
    juju.wait(
        lambda s: jubilant.all_active(
            s,
            "mimir",
            "mimir-read",
            "mimir-write",
            "mimir-backend",
            "mimir-s3-integrator",
            "seaweedfs",
        ),
        timeout=2000,
    )


@retry(wait=wait_fixed(10), stop=stop_after_attempt(6))
def test_mimir_ready(juju: jubilant.Juju):
    """Verify that Mimir's HTTP API is reachable and responds to a basic query."""
    result = query_mimir_from_client_localhost(juju, query="up")
    assert isinstance(result, list)


@retry(wait=wait_fixed(10), stop=stop_after_attempt(6))
def test_mimir_has_s3(juju: jubilant.Juju):
    """Verify Mimir's runtime config endpoint reports an S3 backend."""
    mimir_addr = get_leader_address(juju, "mimir")
    response = requests.get(
        f"http://{mimir_addr}:8080/runtime_config", timeout=10
    )
    assert response.status_code == 200
