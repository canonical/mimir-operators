from typing import Union
from unittest.mock import MagicMock, patch

import pytest as pytest
from coordinated_workers.coordinator import Coordinator
from helpers import get_key_from_worker_config_exemplars
from ops.testing import ActiveStatus, BlockedStatus
from scenario import Container, Exec, State
    import socket

from charm import ALERTS_HASH_PATH, NGINX_PORT
from src.mimir_config import (
    MIMIR_ROLES_CONFIG,
    MINIMAL_DEPLOYMENT,
)


@patch("coordinated_workers.coordinator.Coordinator.__init__", return_value=None)
@pytest.mark.parametrize(
    "roles, expected",
    (
        ({"querier": 1}, False),
        ({"distributor": 1}, False),
        ({"distributor": 1, "ingester": 1}, False),
        (dict.fromkeys(MINIMAL_DEPLOYMENT, 1), True),
    ),
)
def test_coherent(mock_coordinator, roles, expected):
    mc = Coordinator(None, None, "", "", 0, None, None, None)  # pyright: ignore
    cluster_mock = MagicMock()
    cluster_mock.gather_roles = MagicMock(return_value=roles)
    mc.cluster = cluster_mock
    mc._override_coherency_checker = None
    mc._roles_config = MIMIR_ROLES_CONFIG

    assert mc.is_coherent is expected


@pytest.mark.parametrize(
    "set_config, expected_exemplars",
    [
        (0, 0),               # when max_global_exemplars_per_user is 0
        (99_999, 100_000),      # when max_global_exemplars_per_user is between 1 and 100k
        (100_001, 100_001),     # when max_global_exemplars_per_user is above 100k
    ]
)
def test_config_exemplars(context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container, set_config, expected_exemplars):
    """Ensure the correct config for max_global_exemplars_per_user are sent to the worker by the coordinator."""
    # GIVEN that the exemplars are enabled in Mimir Coordinator
    config_value: Union[str, int, float, bool] = set_config
    config = {"max_global_exemplars_per_user": config_value}

    state_in = State(
        relations=[
            s3,
            all_worker,
        ],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        leader=True,
        config=config
    )

    # WHEN a worker joins a relation to a coordinator
    with context(context.on.relation_joined(all_worker), state_in) as mgr:
        state_out = mgr.run()

        # THEN the worker should have the correct exemplar limit
        config = get_key_from_worker_config_exemplars(state_out.relations, "mimir-cluster", "max_global_exemplars_per_user")
        assert config == expected_exemplars

@pytest.mark.parametrize(
    "set_config, expected_value, expected_status",
    [
        ("1m", "1m", ActiveStatus),
        ("1w", "1w", ActiveStatus),
        ("1d", "1d", ActiveStatus),
        ("1y", "1y", ActiveStatus),
        ("1xyz", 0, BlockedStatus),
        ("0", 0, ActiveStatus),
    ]
)
def test_config_retention_period(context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container, set_config, expected_value, expected_status):
    """Ensure the correct config for max_global_exemplars_per_user are sent to the worker by the coordinator."""
    # GIVEN that the retention period is set in Mimir Coordinator
    config = {"metrics_retention_period": set_config}

    state_in = State(
        relations=[
            s3,
            all_worker,
        ],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        leader=True,
        config=config
    )

    # WHEN a worker joins a relation to a coordinator
    with context(context.on.relation_joined(all_worker), state_in) as mgr:
        state_out = mgr.run()
        # THEN the worker should have the correct expected value
        config = get_key_from_worker_config_exemplars(state_out.relations, "mimir-cluster", "compactor_blocks_retention_period")
        assert config == expected_value
        assert isinstance(state_out.unit_status, expected_status)


def test_alerts_hash_not_written_on_mimirtool_failure(
    context,
    s3,
    all_worker,
    nginx_prometheus_exporter_container,
):
    """The alerts hash must NOT be persisted when mimirtool exits non-zero.

    If the hash were written before confirming success, subsequent hook runs
    would see "no change" and silently skip the sync, leaving Mimir without
    the updated alert rules indefinitely.
    """

    address_arg = f"--address=http://{socket.getfqdn()}:{NGINX_PORT}"
    failing_container = Container(
        "nginx",
        can_connect=True,
        execs={
            Exec(
                ["mimirtool", "rules", "sync", address_arg, "--id=anonymous"],
                return_code=1,
            ),
            Exec(["update-ca-certificates", "--fresh"], return_code=0),
        },
    )

    state_in = State(
        relations=[s3, all_worker],
        containers=[failing_container, nginx_prometheus_exporter_container],
        leader=True,
    )

    with context(context.on.relation_changed(all_worker), state_in) as mgr:
        state_out = mgr.run()

    # THEN the hash file is absent so the next hook run retries the sync
    nginx_fs = state_out.get_container("nginx").get_filesystem(context)
    assert not (nginx_fs / ALERTS_HASH_PATH.lstrip("/")).exists()
