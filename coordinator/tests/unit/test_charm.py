from typing import Union
from unittest.mock import MagicMock, patch

import pytest as pytest
from coordinated_workers.coordinator import Coordinator
from helpers import get_key_from_worker_config_exemplars
from ops.testing import ActiveStatus, BlockedStatus, WaitingStatus
from scenario import State

from src.mimir_config import (
    MIMIR_ROLES_CONFIG,
    MINIMAL_DEPLOYMENT,
    RECOMMENDED_DEPLOYMENT,
)


@patch("coordinated_workers.coordinator.Coordinator.__init__", return_value=None)
@pytest.mark.parametrize(
    "roles, expected",
    (
        ({"querier": 1}, False),
        ({"distributor": 1}, False),
        ({"distributor": 1, "ingester": 1}, False),
        (dict.fromkeys(MINIMAL_DEPLOYMENT, 1), True),
        (RECOMMENDED_DEPLOYMENT, True),
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


@patch("coordinated_workers.coordinator.Coordinator.__init__", return_value=None)
@pytest.mark.parametrize(
    "roles, expected",
    (
        ({"query-frontend": 1}, False),
        ({"distributor": 1}, False),
        ({"distributor": 1, "ingester": 1}, False),
        (dict.fromkeys(MINIMAL_DEPLOYMENT, 1), False),
        (RECOMMENDED_DEPLOYMENT, True),
    ),
)
def test_recommended(mock_coordinator, roles, expected):
    mc = Coordinator(None, None, "", "", 0, None, None, None)  # pyright: ignore
    cluster_mock = MagicMock()
    cluster_mock.gather_roles = MagicMock(return_value=roles)
    mc.cluster = cluster_mock
    mc._override_recommended_checker = None
    mc._roles_config = MIMIR_ROLES_CONFIG

    assert mc.is_recommended is expected

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


def test_validation_wrapper_no_error_on_success(context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
    """When config generation succeeds, no validation error is flagged."""
    state_in = State(
        relations=[s3, all_worker],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        leader=True,
    )

    with context(context.on.relation_joined(all_worker), state_in) as mgr:
        mgr.run()

        assert mgr.charm._config_validation_error is False


def test_validation_wrapper_returns_existing_config_on_failure(context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
    """When config validation fails, the wrapper returns the config already in relation data."""
    from pydantic import ValidationError

    from src.mimir_config import ShardingRing

    state_in = State(
        relations=[s3, all_worker],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        leader=True,
    )

    with context(context.on.relation_joined(all_worker), state_in) as mgr:
        state_out = mgr.run()

        # Grab the config that was published during the successful run
        import json
        published = None
        for rel in state_out.relations:
            if rel.endpoint == "mimir-cluster" and "worker_config" in rel.local_app_data:
                published = json.loads(rel.local_app_data["worker_config"])
                break
        assert published

        # Now simulate a validation failure
        try:
            ShardingRing(replication_factor="bad")  # type: ignore
        except ValidationError as exc:
            mgr.charm._mimir_config.config = MagicMock(side_effect=exc)

        result = mgr.charm._validated_workers_config(MagicMock())
        # Should return the config already in the databag (no change for workers)
        assert result == published
        assert mgr.charm._config_validation_error is True


def test_validation_error_sets_waiting_status(context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
    """When validation has failed, collect_unit_status adds WaitingStatus."""
    from pydantic import ValidationError

    from src.mimir_config import ShardingRing

    state_in = State(
        relations=[s3, all_worker],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        leader=True,
    )

    with context(context.on.relation_joined(all_worker), state_in) as mgr:
        # After __init__ (which succeeds), make config generation fail for the event
        try:
            ShardingRing(replication_factor="bad")  # type: ignore
        except ValidationError as exc:
            mgr.charm._mimir_config.config = MagicMock(side_effect=exc)

        state_out = mgr.run()
        assert mgr.charm._config_validation_error is True
        assert isinstance(state_out.unit_status, WaitingStatus)
