import unittest
from unittest.mock import MagicMock

import pytest
import yaml
from deepdiff import DeepDiff

from src.mimir_config import MimirConfig

# Regression tests for https://github.com/canonical/mimir-operators/issues/503:
# replication_factor must not flip 3 -> 1 -> 3 as the live unit count for a role
# transiently dips below REPLICATION_MIN_WORKERS and recovers.
RING_BUILDERS = {
    "ingester": ("_build_ingester_config", ("ring", "replication_factor")),
    "store-gateway": ("_build_store_gateway_config", ("sharding_ring", "replication_factor")),
    "alertmanager": ("_build_alertmanager_config", ("sharding_ring", "replication_factor")),
}


@pytest.fixture(scope="module")
def topology():
    top = MagicMock()
    top.as_dict = MagicMock(
        return_value={
            "model": "some-model",
            "model_uuid": "some-uuid",
            "application": "mimir",
            "unit": "mimir-0",
            "charm_name": "mimir-coordinator-k8s",
        }
    )
    return top

@pytest.fixture(scope="module")
def mimir_config(topology):
    return MimirConfig(topology=topology, alertmanager_urls={"http://some.am.0:9093", "http://some.am.1:9093"})


@pytest.fixture(scope="module")
def coordinator():
    coord = MagicMock()
    coord.cluster = MagicMock()
    coord.cluster.gather_addresses_by_role = MagicMock(
        return_value={
            "alertmanager": ["http://some.mimir.worker.0:8080"],
            "overrides-exporter": ["http://some.mimir.worker.0:8080"],
            "flusher": ["http://some.mimir.worker.0:8080"],
            "query-frontend": ["http://some.mimir.worker.0:8080"],
            "querier": ["http://some.mimir.worker.0:8080"],
            "store-gateway": ["http://some.mimir.worker.1:8080"],
            "ingester": ["http://some.mimir.worker.1:8080"],
            "distributor": ["http://some.mimir.worker.1:8080"],
            "ruler": ["http://some.mimir.worker.1:8080"],
            "compactor": ["http://some.mimir.worker.0:8080", "http://some.mimir.worker.1:8080"],
        }
    )
    coord.cluster.gather_addresses = MagicMock(
        return_value=["http://some.mimir.worker.0:8080", "http://some.mimir.worker.1:8080"]
    )
    coord.s3_ready = True
    coord._s3_config = {
        "endpoint": "http://s3.example.com:9000",
        "access_key_id": "test-key",
        "secret_access_key": "test-secret",
        "bucket_name": "mimir",
        "region": "us-east-1",
    }
    coord.nginx = MagicMock()
    coord.nginx.are_certificates_on_disk = MagicMock(return_value=True)
    return coord





@pytest.mark.parametrize(
    "addresses_by_role, replication",
    [
        ({"alertmanager": ["address.one"]}, 1),
        ({"alertmanager": ["address.one", "address.two"]}, 1),
        ({"alertmanager": ["address.one", "address.two", "address.three"]}, 3),
    ],
)
def test_build_alertmanager_config(mimir_config, coordinator, addresses_by_role, replication):
    coordinator.cluster.gather_addresses_by_role.return_value = addresses_by_role
    alertmanager_config = mimir_config._build_alertmanager_config(coordinator.cluster)
    expected_config = {
        "data_dir": "/data/data-alertmanager",
        "sharding_ring": {"replication_factor": replication},
    }
    assert alertmanager_config == expected_config

@pytest.mark.parametrize(
    "max_global_exemplars_per_user, expected_value",
    [
        (None, 0),             # When value is None, it should return 0
        (0, 0),                # When value is 0 or negative, it should return 0
        (-1, 0),
        (50_000, 100_000),       # When value is between 1 and 100000, it should return 100000
        (99_999, 100_000),
        (100_000, 100_000),      # When value is exactly 100000, it should return 100000
        (150_000, 150_000),      # When value is greater than 100000, it should remain unchanged
        (100_001, 100_001)
    ],
)
def test_max_global_exemplars_per_user_logic(mimir_config, max_global_exemplars_per_user, expected_value):
    # Set the _max_global_exemplars_per_user to the value being tested
    mimir_config._max_global_exemplars_per_user = max_global_exemplars_per_user

    # Build the limits config
    limits_config = mimir_config._build_limits_config()

    # Assert that the value for max_global_exemplars_per_user matches the expected value
    assert limits_config["max_global_exemplars_per_user"] == expected_value


@pytest.mark.parametrize(
    "ingestion_rate, expected_rate, expected_burst",
    [
        (None,    100_000,  2_000_000),   # None → charm defaults unchanged
        (0,       0,        0),           # 0 → limit disabled, burst also 0
        (50_000,  50_000,   1_000_000),   # custom value → burst = 20x
        (200_000, 200_000,  4_000_000),   # larger custom value
    ],
)
def test_ingestion_rate_and_burst_logic(topology, ingestion_rate, expected_rate, expected_burst):
    cfg = MimirConfig(topology=topology, ingestion_rate=ingestion_rate)
    limits = cfg._build_limits_config()
    assert limits["ingestion_rate"] == expected_rate
    assert limits["ingestion_burst_size"] == expected_burst


@pytest.mark.parametrize(
    "max_global_series_per_user, expected_value",
    [
        (None, 0),          # unset → retains the previous hardcoded behavior
        (0, 0),             # 0 → limit disabled
        (150_000, 150_000), # positive value → passed through unchanged
    ],
)
def test_max_global_series_per_user_logic(
    topology, max_global_series_per_user, expected_value
):
    cfg = MimirConfig(
        topology=topology, max_global_series_per_user=max_global_series_per_user
    )
    limits = cfg._build_limits_config()
    assert limits["max_global_series_per_user"] == expected_value


def test_cardinality_analysis_disabled_by_default(topology):
    cfg = MimirConfig(topology=topology)
    assert cfg._build_limits_config()["cardinality_analysis_enabled"] is False


@pytest.mark.parametrize(
    "cardinality_analysis_enabled, expected_value",
    [
        (False, False),  # disabled (matches upstream default)
        (True, True),    # explicitly enabled
    ],
)
def test_cardinality_analysis_enabled_logic(
    topology, cardinality_analysis_enabled, expected_value
):
    cfg = MimirConfig(
        topology=topology,
        cardinality_analysis_enabled=cardinality_analysis_enabled,
    )
    limits = cfg._build_limits_config()
    assert limits["cardinality_analysis_enabled"] == expected_value


def test_build_alertmanager_storage_config(mimir_config):
    alertmanager_storage_config = mimir_config._build_alertmanager_storage_config()
    expected_config = {"filesystem": {"dir": "/recovery-data/data-alertmanager"}}
    assert DeepDiff(alertmanager_storage_config, expected_config) == {}


def test_build_compactor_config(mimir_config):
    compactor_config = mimir_config._build_compactor_config()
    expected_config = {"data_dir": "/data/data-compactor"}
    assert compactor_config == expected_config


def test_get_grpc_addresses_returns_sorted_addresses(mimir_config, coordinator):
    # We ensure that we return a sorted list to avoid issues such as: https://github.com/canonical/cos-coordinated-workers/issues/158.
    # GIVEN the coordinated workers' cluster interface returns the query-scheduler units' addresses in a non-deterministic order
    coordinator.cluster.gather_addresses_by_role.return_value = {
        "query-scheduler": [
            "http://mimir-2.mimir-endpoints.model.svc.cluster.local:8080",
            "http://mimir-0.mimir-endpoints.model.svc.cluster.local:8080",
            "http://mimir-1.mimir-endpoints.model.svc.cluster.local:8080",
        ]
    }

    # WHEN we call the _get_grpc_addresses method for the query-scheduler role
    grpc_addresses = mimir_config._get_grpc_addresses(coordinator.cluster, "query-scheduler")

    # THEN we should get back a sorted list of gRPC addresses (host:port) for the query-scheduler units
    # Note that the port should be transformed from 8080 (HTTP) to 9095 (gRPC) in the output
    assert grpc_addresses == [
        "mimir-0.mimir-endpoints.model.svc.cluster.local:9095",
        "mimir-1.mimir-endpoints.model.svc.cluster.local:9095",
        "mimir-2.mimir-endpoints.model.svc.cluster.local:9095",
    ]


@pytest.mark.parametrize(
    "addresses_by_role, expected_config",
    [
        # With query-scheduler: frontend registers with scheduler
        (
            {"query-scheduler": ["http://scheduler.host:8080"]},
            {"scheduler_address": "scheduler.host:9095"},
        ),
        # Multiple schedulers: only first address used (Mimir expects single host:port)
        (
            {"query-scheduler": ["http://sched.0:8080", "http://sched.1:8080"]},
            {"scheduler_address": "sched.0:9095"},
        ),
        # No scheduler: empty config
        ({}, {}),
        # Only query-frontend present, no scheduler: empty config (frontend section doesn't need self-reference)
        ({"query-frontend": ["http://frontend.host:8080"]}, {}),
        # Plain hostname (no scheme/port) as returned by real deployments
        (
            {"query-scheduler": ["sched-0.sched-endpoints.model.svc.cluster.local"]},
            {"scheduler_address": "sched-0.sched-endpoints.model.svc.cluster.local:9095"},
        ),
    ],
)
def test_build_frontend_config(mimir_config, coordinator, addresses_by_role, expected_config):
    coordinator.cluster.gather_addresses_by_role.return_value = addresses_by_role
    frontend_config = mimir_config._build_frontend_config(coordinator.cluster)
    assert frontend_config == expected_config


@pytest.mark.parametrize(
    "addresses_by_role, expected_config",
    [
        # With query-scheduler: querier connects to scheduler
        (
            {"query-scheduler": ["http://scheduler.host:8080"]},
            {"scheduler_address": "scheduler.host:9095"},
        ),
        # No scheduler but query-frontend exists: querier connects directly to frontend
        (
            {"query-frontend": ["http://frontend.host:8080"]},
            {"frontend_address": "frontend.host:9095"},
        ),
        # Both scheduler and frontend: scheduler takes precedence
        (
            {
                "query-scheduler": ["http://scheduler.host:8080"],
                "query-frontend": ["http://frontend.host:8080"],
            },
            {"scheduler_address": "scheduler.host:9095"},
        ),
        # Neither: empty config
        ({}, {}),
        # Multiple frontends (no scheduler): only first address used (Mimir expects single host:port)
        (
            {"query-frontend": ["http://fe.0:8080", "http://fe.1:8080"]},
            {"frontend_address": "fe.0:9095"},
        ),
        # Plain hostnames (no scheme/port) as returned by real deployments
        (
            {"query-frontend": ["fe-0.fe-endpoints.model.svc.cluster.local"]},
            {"frontend_address": "fe-0.fe-endpoints.model.svc.cluster.local:9095"},
        ),
        # Plain hostname with scheduler
        (
            {
                "query-scheduler": ["sched-0.sched-endpoints.model.svc.cluster.local"],
                "query-frontend": ["fe-0.fe-endpoints.model.svc.cluster.local"],
            },
            {"scheduler_address": "sched-0.sched-endpoints.model.svc.cluster.local:9095"},
        ),
    ],
)
def test_build_frontend_worker_config(mimir_config, coordinator, addresses_by_role, expected_config):
    coordinator.cluster.gather_addresses_by_role.return_value = addresses_by_role
    frontend_worker_config = mimir_config._build_frontend_worker_config(coordinator.cluster)
    assert frontend_worker_config == expected_config


@pytest.mark.parametrize(
    "addresses_by_role, replication",
    [
        ({"ingester": ["address.one"]}, 1),
        ({"ingester": ["address.one", "address.two"]}, 1),
        ({"ingester": ["address.one", "address.two", "address.three"]}, 3),
    ],
)
def test_build_ingester_config(mimir_config, coordinator, addresses_by_role, replication):
    coordinator.cluster.gather_addresses_by_role.return_value = addresses_by_role
    ingester_config = mimir_config._build_ingester_config(coordinator.cluster)
    expected_config = {"ring": {"replication_factor": replication}}
    assert ingester_config == expected_config


@pytest.mark.parametrize(
    "time_window, expected_key_present, expected_value",
    [
        (None, False, None),
        ("0s", True, "0s"),
        ("0m", True, "0m"),
        ("10m", True, "10m"),
        ("1h", True, "1h"),
        ("30m", True, "30m"),
    ],
)
def test_out_of_order_time_window(topology, time_window, expected_key_present, expected_value):
    cfg = MimirConfig(topology=topology, out_of_order_time_window=time_window)
    limits_config = cfg._build_limits_config()
    if expected_key_present:
        assert limits_config["out_of_order_time_window"] == expected_value
    else:
        assert "out_of_order_time_window" not in limits_config


def test_build_ruler_config(mimir_config):
    ruler_config = mimir_config._build_ruler_config()
    expected_config = {
        "rule_path": "/data/data-ruler",
        "alertmanager_url": "http://some.am.0:9093,http://some.am.1:9093",
    }
    assert ruler_config == expected_config


@pytest.mark.parametrize(
    "addresses_by_role, replication",
    [
        ({"store-gateway": ["address.one"]}, 1),
        ({"store-gateway": ["address.one", "address.two"]}, 1),
        ({"store-gateway": ["address.one", "address.two", "address.three"]}, 3),
    ],
)
def test_build_store_gateway_config(mimir_config, coordinator, addresses_by_role, replication):
    coordinator.cluster.gather_addresses_by_role.return_value = addresses_by_role
    store_gateway_config = mimir_config._build_store_gateway_config(coordinator.cluster)
    expected_config = {"sharding_ring": {"replication_factor": replication}}
    assert store_gateway_config == expected_config


def test_build_ruler_storage_config(mimir_config):
    ruler_storage_config = mimir_config._build_ruler_storage_config()
    expected_config = {"filesystem": {"dir": "/data/rules"}}
    assert ruler_storage_config == expected_config


def test_build_blocks_storage_config(mimir_config):
    blocks_storage_config = mimir_config._build_blocks_storage_config()
    expected_config = {
        "bucket_store": {"sync_dir": "/data/tsdb-sync"},
        "filesystem": {"dir": "/data/blocks"},
        "tsdb": {"dir": "/data/tsdb"},
    }
    assert blocks_storage_config == expected_config


def test_build_s3_storage_config(mimir_config, coordinator):
    # HTTP endpoint
    s3_data_http = {
        "endpoint": "s3.com:port",
        "access_key_id": "your_access_key",
        "secret_access_key": "your_secret_key",
        "bucket_name": "your_bucket",
        "region": "your_region",
        "insecure": "true",
    }
    s3_storage_config_http = mimir_config._build_s3_storage_config(s3_data_http.copy())
    expected_config_http = {"backend": "s3", "s3": s3_data_http}
    assert s3_storage_config_http == expected_config_http

    # HTTPS endpoint
    s3_data_https = {
        "endpoint": "https://s3.com:port",
        "access-key": "your_access_key",
        "secret-key": "your_secret_key",
        "bucket": "your_bucket",
        "region": "your_region",
        "insecure": "false",
    }
    s3_storage_config_https = mimir_config._build_s3_storage_config(s3_data_https.copy())
    expected_config_https = {"backend": "s3", "s3": s3_data_https}
    assert s3_storage_config_https == expected_config_https


def test_update_s3_storage_config(mimir_config):
    storage_config = {"filesystem": {"dir": "/data/blocks"}}
    mimir_config._update_s3_storage_config(storage_config, "blocks")
    expected_config = {"storage_prefix": "blocks"}
    assert storage_config == expected_config


def test_empty_update_s3_storage_config(mimir_config):
    storage_config = {"storage_prefix": "blocks"}
    mimir_config._update_s3_storage_config(storage_config, "blocks")
    expected_config = {"storage_prefix": "blocks"}
    assert storage_config == expected_config


def test_build_memberlist_config(mimir_config, coordinator):
    memberlist_config = mimir_config._build_memberlist_config(coordinator.cluster)
    expected_config = {
        "cluster_label": "some-model_some-uuid_mimir",
        "join_members": ["http://some.mimir.worker.0:8080", "http://some.mimir.worker.1:8080"],
    }
    assert memberlist_config == expected_config


def test_build_tls_config(mimir_config):
    tls_config = mimir_config._build_tls_config()
    expected_config = {
        "http_tls_config": {
            "cert_file": "/etc/worker/server.cert",
            "key_file": "/etc/worker/private.key",
            "client_ca_file": "/etc/worker/ca.cert",
            "client_auth_type": "RequestClientCert",
        },
        # FIXME: investigate adding grpc_tls_config: https://github.com/canonical/mimir-coordinator-k8s-operator/issues/141
    }
    assert tls_config == expected_config

@pytest.mark.parametrize(
    "retention_period_config, expected_value",
    [
        ("1m", "1m"),
        ("1w", "1w"),
        ("0", 0),
    ],
)
def test_retention_period_logic(mimir_config, retention_period_config, expected_value):
    # Set the compactor_blocks_retention_period to the value being tested
    mimir_config._metrics_retention_period = retention_period_config

    # Build the limits config
    limits_config = mimir_config._build_limits_config()

    # Assert that the value for compactor_blocks_retention_period matches the expected value
    assert limits_config["compactor_blocks_retention_period"] == expected_value


def test_reporting_enabled_by_default(topology, coordinator):
    """When reporting_enabled is True (default), no usage_stats section should appear."""
    cfg = MimirConfig(topology=topology)
    config_yaml = cfg.config(coordinator)
    config_dict = yaml.safe_load(config_yaml)
    assert "usage_stats" not in config_dict


def test_reporting_disabled(topology, coordinator):
    """When reporting_enabled is False, usage_stats.enabled should be False."""
    cfg = MimirConfig(topology=topology, reporting_enabled=False)
    config_yaml = cfg.config(coordinator)
    config_dict = yaml.safe_load(config_yaml)
    assert config_dict["usage_stats"] == {"enabled": False}


def _replication_factor(config: dict, path) -> int:
    for key in path:
        config = config[key]
    return config


def _make_cluster(role: str, scale: int):
    cluster = MagicMock()
    addresses = [f"http://worker-{role}-{i}:8080" for i in range(scale)]
    cluster.gather_addresses_by_role = MagicMock(return_value={role: addresses})
    return cluster


@pytest.mark.parametrize("role", list(RING_BUILDERS.keys()))
def test_replication_factor_does_not_downgrade_after_losing_one_of_three_units(topology, role):
    """3 units -> RF 3, then lose 1 unit -> RF must stay 3, then back to 3 units -> still 3."""
    method_name, path = RING_BUILDERS[role]
    cfg = MimirConfig(topology=topology)
    builder = getattr(cfg, method_name)

    assert _replication_factor(builder(_make_cluster(role, 3)), path) == 3
    assert _replication_factor(builder(_make_cluster(role, 2)), path) == 3
    assert _replication_factor(builder(_make_cluster(role, 3)), path) == 3


@pytest.mark.parametrize("role", list(RING_BUILDERS.keys()))
def test_replication_factor_never_locked_below_three_units(topology, role):
    """Before ever reaching 3 units, RF stays at 1."""
    method_name, path = RING_BUILDERS[role]
    cfg = MimirConfig(topology=topology)
    builder = getattr(cfg, method_name)

    assert _replication_factor(builder(_make_cluster(role, 1)), path) == 1
    assert _replication_factor(builder(_make_cluster(role, 2)), path) == 1


@pytest.mark.parametrize("role", list(RING_BUILDERS.keys()))
def test_replication_factor_unlocks_on_scale_down_to_single_unit(topology, role):
    """Scaling down to a single unit releases the lock until 3 units are reached again."""
    method_name, path = RING_BUILDERS[role]
    cfg = MimirConfig(topology=topology)
    builder = getattr(cfg, method_name)

    assert _replication_factor(builder(_make_cluster(role, 3)), path) == 3
    assert _replication_factor(builder(_make_cluster(role, 1)), path) == 1
    assert _replication_factor(builder(_make_cluster(role, 2)), path) == 1
    assert _replication_factor(builder(_make_cluster(role, 3)), path) == 3


def test_replication_lock_state_shared_across_roles_is_independent():
    """The lock for one role must not affect another role's replication factor."""
    topology = MagicMock()
    topology.as_dict = MagicMock(
        return_value={
            "model": "m",
            "model_uuid": "u",
            "application": "mimir",
            "unit": "mimir-0",
            "charm_name": "mimir-coordinator-k8s",
        }
    )
    shared_state: dict = {}
    cfg = MimirConfig(topology=topology, replication_lock_state=shared_state)

    ingester_cluster = MagicMock()
    ingester_cluster.gather_addresses_by_role = MagicMock(
        return_value={"ingester": ["a", "b", "c"]}
    )
    assert cfg._build_ingester_config(ingester_cluster)["ring"]["replication_factor"] == 3
    assert shared_state == {"ingester": True}

    sg_cluster = MagicMock()
    sg_cluster.gather_addresses_by_role = MagicMock(return_value={"store-gateway": ["a"]})
    assert cfg._build_store_gateway_config(sg_cluster)["sharding_ring"]["replication_factor"] == 1
    assert shared_state == {"ingester": True, "store-gateway": False}


def test_replication_lock_state_is_externally_persistable(topology):
    """The lock state dict passed by the caller is mutated in place and can be reused."""
    persisted_state: dict = {}
    cfg = MimirConfig(topology=topology, replication_lock_state=persisted_state)

    cfg._build_ingester_config(_make_cluster("ingester", 3))
    assert persisted_state == {"ingester": True}

    cfg2 = MimirConfig(topology=topology, replication_lock_state=persisted_state)
    rf = cfg2._build_ingester_config(_make_cluster("ingester", 2))["ring"]["replication_factor"]
    assert rf == 3


if __name__ == "__main__":
    unittest.main()
