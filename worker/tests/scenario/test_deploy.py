# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
from ops.model import ActiveStatus, WaitingStatus
from scenario import Container, Relation, State

from tests.scenario.conftest import MIMIR_VERSION_EXEC_OUTPUT


@pytest.mark.parametrize("evt", ["update-status", "config-changed"])
def test_update_status_cannot_connect(ctx, evt):
    mimir_container = Container("mimir-worker", can_connect=False)

    state_out = ctx.run(evt, state=State(containers=[mimir_container]))
    assert state_out.status.unit == WaitingStatus("Waiting for Pebble ready")


@pytest.mark.parametrize(
    "relations",
    (
        ["alertmanager", "compactor"],
        ["alertmanager", "distributor"],
        ["alertmanager"],
        ["alertmanager", "query-frontend"],
        ["alertmanager", "ruler", "store-gateway"],
        ["alertmanager", "overrides-exporter", "ruler", "store-gateway"],  # order matters
    ),
)
def test_pebble_ready_plan(ctx, relations):
    mimir_relations = tuple("mimir-" + relation for relation in relations)

    expected_plan = {
        "services": {
            "mimir-worker": {
                "override": "replace",
                "summary": "mimir worker daemon",
                "command": f"/bin/mimir --config.file=/etc/mimir/mimir-config.yaml -target {','.join(mimir_relations)}",
                "startup": "enabled",
            }
        },
    }

    mimir_container = Container(
        "mimir-worker",
        can_connect=True,
        exec_mock={("/bin/mimir", "-version"): MIMIR_VERSION_EXEC_OUTPUT},
    )

    state_out = ctx.run(
        mimir_container.pebble_ready_event,
        state=State(
            containers=[mimir_container],
            relations=[
                Relation(endpoint, interface="mimir_worker", remote_app_name=f"{endpoint} app")
                for endpoint in mimir_relations
            ],
        ),
    )

    mimir_container_out = state_out.get_container(mimir_container)
    assert mimir_container_out.services.get("mimir-worker").is_running() is True
    assert mimir_container_out.plan.to_dict() == expected_plan

    assert state_out.status.unit == ActiveStatus("")
