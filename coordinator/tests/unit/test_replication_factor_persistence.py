# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm-level regression tests for https://github.com/canonical/mimir-operators/issues/503.

Covers the replication-factor lock end to end, including persistence across hooks via the
`mimir-peers` peer relation app databag.
"""

import dataclasses
import json

import yaml
from scenario import PeerRelation, Relation, State


def _write_relation(num_units: int) -> Relation:
    """Build a mimir-cluster relation with `num_units` related `write`-role worker units."""
    return Relation(
        "mimir-cluster",
        remote_app_name="worker-write",
        remote_app_data={"role": '"write"'},
        remote_units_data={
            i: {
                "address": json.dumps(f"worker-write-{i}.worker-write-endpoints"),
                "juju_topology": json.dumps(
                    {
                        "application": "worker-write",
                        "unit": f"worker-write/{i}",
                        "charm_name": "mimir-worker-k8s",
                    }
                ),
            }
            for i in range(num_units)
        },
    )


def _role_relation(app_name: str, role: str) -> Relation:
    """Build a single-unit mimir-cluster relation for a given meta-role.

    Used alongside `_write_relation` to satisfy MINIMAL_DEPLOYMENT.
    """
    return Relation(
        "mimir-cluster",
        remote_app_name=app_name,
        remote_app_data={"role": json.dumps(role)},
        remote_units_data={
            0: {
                "address": json.dumps(f"{app_name}-0.{app_name}-endpoints"),
                "juju_topology": json.dumps(
                    {
                        "application": app_name,
                        "unit": f"{app_name}/0",
                        "charm_name": "mimir-worker-k8s",
                    }
                ),
            }
        },
    )


def _ingester_replication_factor(state) -> int:
    relation = state.get_relation(
        [r.id for r in state.relations if r.endpoint == "mimir-cluster"][0]
    )
    worker_config_str = relation.local_app_data["worker_config"]
    worker_config = yaml.safe_load(yaml.safe_load(worker_config_str))
    return worker_config["ingester"]["ring"]["replication_factor"]


def test_losing_one_of_three_write_units_does_not_drop_replication_factor(
    context, s3, nginx_container, nginx_prometheus_exporter_container,
):
    """RF must stay 3 across a 3 -> 2 -> 3 write-unit transition."""
    peers = PeerRelation("mimir-peers")
    write_3 = _write_relation(3)
    read = _role_relation("worker-read", "read")
    backend = _role_relation("worker-backend", "backend")
    state = State(
        relations=[s3, write_3, read, backend, peers],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        leader=True,
    )

    state = context.run(context.on.relation_changed(write_3), state)
    assert _ingester_replication_factor(state) == 3

    peers_out = state.get_relation(peers.id)
    lock_state = json.loads(peers_out.local_app_data["replication-lock-state"])
    assert lock_state["ingester"] is True

    # One write unit is lost: the relation id is kept so the same relation is modified.
    write_2 = dataclasses.replace(_write_relation(2), id=write_3.id)
    state = dataclasses.replace(
        state, relations=[s3, write_2, read, backend, state.get_relation(peers.id)]
    )
    state = context.run(context.on.relation_departed(write_2, remote_unit=2), state)
    assert _ingester_replication_factor(state) == 3

    # The lost unit rejoins: RF stays at 3, no spurious 1 -> 3 flip.
    write_3_again = dataclasses.replace(_write_relation(3), id=write_3.id)
    state = dataclasses.replace(
        state, relations=[s3, write_3_again, read, backend, state.get_relation(peers.id)]
    )
    state = context.run(context.on.relation_changed(write_3_again), state)
    assert _ingester_replication_factor(state) == 3


def test_scaling_down_to_a_single_write_unit_releases_the_lock(
    context, s3, nginx_container, nginx_prometheus_exporter_container,
):
    """Scaling down to 1 unit releases the RF lock."""
    peers = PeerRelation("mimir-peers")
    write_3 = _write_relation(3)
    read = _role_relation("worker-read", "read")
    backend = _role_relation("worker-backend", "backend")
    state = State(
        relations=[s3, write_3, read, backend, peers],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        leader=True,
    )
    state = context.run(context.on.relation_changed(write_3), state)
    assert _ingester_replication_factor(state) == 3

    write_1 = dataclasses.replace(_write_relation(1), id=write_3.id)
    state = dataclasses.replace(
        state, relations=[s3, write_1, read, backend, state.get_relation(peers.id)]
    )
    state = context.run(context.on.relation_departed(write_1, remote_unit=1), state)

    assert _ingester_replication_factor(state) == 1

    peers_out = state.get_relation(peers.id)
    lock_state = json.loads(peers_out.local_app_data["replication-lock-state"])
    assert lock_state["ingester"] is False
