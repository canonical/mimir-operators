# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
import json

import pytest
from mimir_cluster import MimirClusterRequirerAppData, MimirRole
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus
from scenario import Container, ExecOutput, Relation, State

from tests.scenario.conftest import MIMIR_VERSION_EXEC_OUTPUT


@pytest.mark.parametrize("evt", ["update-status", "config-changed"])
def test_status_cannot_connect_no_relation(ctx, evt):
    state_out = ctx.run(evt, state=State(containers=[Container("mimir", can_connect=False)]))
    assert state_out.unit_status == BlockedStatus(
        "Missing mimir-cluster relation to a mimir-coordinator charm"
    )


@pytest.mark.parametrize("evt", ["update-status", "config-changed"])
def test_status_cannot_connect(ctx, evt):
    container = Container(
        "mimir",
        can_connect=False,
        exec_mock={
            ("update-ca-certificates", "--fresh"): ExecOutput(),
        },
    )
    state_out = ctx.run(
        evt,
        state=State(
            config={"role-ruler": True},
            containers=[container],
            relations=[Relation("mimir-cluster")],
        ),
    )
    assert state_out.unit_status == WaitingStatus("Waiting for `mimir` container")


@pytest.mark.parametrize("evt", ["update-status", "config-changed"])
def test_status_no_config(ctx, evt):
    state_out = ctx.run(
        evt,
        state=State(
            containers=[Container("mimir", can_connect=True)],
            relations=[Relation("mimir-cluster")],
        ),
    )
    assert state_out.unit_status == BlockedStatus("No roles assigned: please configure some roles")


@pytest.mark.parametrize(
    "roles",
    (
        ["alertmanager", "compactor"],
        ["alertmanager", "distributor"],
        ["alertmanager"],
        ["alertmanager", "query-frontend"],
        ["alertmanager", "ruler", "store-gateway"],
        ["alertmanager", "overrides-exporter", "ruler", "store-gateway"],  # order matters
    ),
)
def test_pebble_ready_plan(ctx, roles):
    expected_plan = {
        "services": {
            "mimir": {
                "override": "replace",
                "summary": "mimir worker daemon",
                "command": f"/bin/mimir --config.file=/etc/mimir/mimir-config.yaml -target {','.join(sorted(roles))} -auth.multitenancy-enabled=false",
                "startup": "enabled",
            }
        },
    }

    mimir_container = Container(
        "mimir",
        can_connect=True,
        exec_mock={
            ("/bin/mimir", "-version"): MIMIR_VERSION_EXEC_OUTPUT,
            ("update-ca-certificates", "--fresh"): ExecOutput(),
        },
    )
    state_out = ctx.run(
        mimir_container.pebble_ready_event,
        state=State(
            config={f"role-{role}": True for role in roles},
            containers=[mimir_container],
            relations=[
                Relation(
                    "mimir-cluster",
                    remote_app_data={
                        "mimir_config": json.dumps({"alive": "beef"}),
                    },
                )
            ],
        ),
    )

    mimir_container_out = state_out.get_container(mimir_container)
    assert mimir_container_out.services.get("mimir").is_running() is True
    assert mimir_container_out.plan.to_dict() == expected_plan

    assert state_out.unit_status == ActiveStatus("")


@pytest.mark.parametrize(
    "roles_config, expected",
    (
        ("querier", (MimirRole.querier,)),
        ("querier,ingester", (MimirRole.querier, MimirRole.ingester)),
        ("read,ingester", (MimirRole.query_frontend, MimirRole.querier, MimirRole.ingester)),
        ("read", (MimirRole.query_frontend, MimirRole.querier)),
        ("write", (MimirRole.distributor, MimirRole.ingester)),
        (
            "backend",
            (
                MimirRole.store_gateway,
                MimirRole.compactor,
                MimirRole.ruler,
                MimirRole.alertmanager,
                MimirRole.query_scheduler,
                MimirRole.overrides_exporter,
            ),
        ),
        ("all", tuple(MimirRole)),
    ),
)
def test_roles(ctx, roles_config, expected):
    out = ctx.run(
        "config-changed",
        state=State(
            leader=True,
            config={f"role-{x}": True for x in roles_config.split(",")},
            containers=[Container("mimir", can_connect=True)],
            relations=[Relation("mimir-cluster")],
        ),
    )
    if expected:
        data = MimirClusterRequirerAppData.load(
            out.get_relations("mimir-cluster")[0].local_app_data
        )
        assert set(data.roles) == set(expected)
    else:
        assert not out.get_relations("mimir-cluster")[0].local_app_data
