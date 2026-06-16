# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

import dataclasses
import json
from unittest.mock import patch

import yaml
from ops import ActiveStatus, BlockedStatus
from scenario import Container, Exec, Relation, State


def _alert_rules(group_name: str, valid: bool) -> str:
    invalid_expr = 'sum(rate({job="invalid"}[5m])) >'
    alert_name = group_name.replace("-", "_")
    return json.dumps(
        {
            "groups": [
                {
                    "name": group_name,
                    "rules": [
                        {
                            "alert": f"{alert_name}ValidA",
                            "expr": 'sum(rate({job="valid"}[5m])) > 0',
                            "for": "1m",
                            "labels": {"severity": "warning"},
                            "annotations": {"summary": "valid-a"},
                        },
                        {
                            "alert": f"{alert_name}ValidB",
                            "expr": 'sum(rate({job="valid"}[10m])) > 0'
                            if valid
                            else invalid_expr,
                            "for": "1m",
                            "labels": {"severity": "warning"},
                            "annotations": {"summary": "valid-b"},
                        },
                    ],
                }
            ]
        }
    )


def _metadata(app_name: str) -> str:
    return json.dumps(
        {
            "model": "test",
            "model_uuid": "20ce8299-3634-4bef-8bd8-5ace6c8816b4",
            "application": app_name,
            "charm_name": f"{app_name}-charm",
        }
    )


VALID_REMOTE_WRITE_RELATION = Relation(
    "receive-remote-write",
    remote_app_name="remote-write-valid",
    remote_app_data={
        "alert_rules": _alert_rules("remote-write-valid-group", valid=True),
        "scrape_metadata": _metadata("remote-write-valid"),
    },
)

INVALID_REMOTE_WRITE_RELATION = Relation(
    "receive-remote-write",
    remote_app_name="remote-write-invalid",
    remote_app_data={
        "alert_rules": _alert_rules("remote-write-invalid-group", valid=False),
        "scrape_metadata": _metadata("remote-write-invalid"),
    },
)


def _nginx_container_for_alert_rules():
    return Container(
        "nginx",
        can_connect=True,
        execs={
            Exec(["mimirtool", "rules", "sync"], return_code=0),
            Exec(["update-ca-certificates", "--fresh"], return_code=0),
            Exec(["nginx", "-s", "reload"], return_code=0),
        },
    )


def _written_group_names(context, state_out):
    fs = state_out.get_container("nginx").get_filesystem(context)
    rules_dir = fs.joinpath("etc", "mimir-alerts", "rules")
    if not rules_dir.exists():
        return set()

    written_group_names = set()
    for rule_file in sorted(path for path in rules_dir.iterdir() if path.is_file()):
        written_rules = yaml.safe_load(rule_file.read_text())
        for group in written_rules["groups"]:
            written_group_names.add(group["name"])
    return written_group_names


def _relation_errors(relation: Relation) -> str:
    event = json.loads(relation.local_app_data.get("event", "{}"))
    return event.get("errors", "")


def _validate_alert_rules(_, rules):
    group_name = rules["groups"][0]["name"]
    if "invalid" in group_name:
        return False, f"{group_name} is invalid"
    return True, ""


def test_invalid_remote_write_relation_becoming_valid_recovers_to_active(
    context, s3, all_worker, nginx_prometheus_exporter_container
):
    # GIVEN a remote-write relation with invalid rules has already reported errors
    state_in = State(
        leader=True,
        relations=[s3, all_worker, INVALID_REMOTE_WRITE_RELATION],
        containers=[_nginx_container_for_alert_rules(), nginx_prometheus_exporter_container],
    )

    with patch(
        "charms.prometheus_k8s.v1.prometheus_remote_write.CosTool.validate_alert_rules",
        autospec=True,
        side_effect=_validate_alert_rules,
    ):
        invalid_state = context.run(
            context.on.relation_changed(INVALID_REMOTE_WRITE_RELATION), state_in
        )
        relation_after_invalid = invalid_state.get_relation(INVALID_REMOTE_WRITE_RELATION.id)

        assert _relation_errors(relation_after_invalid)
        assert _written_group_names(context, invalid_state) == set()
        assert isinstance(invalid_state.unit_status, BlockedStatus)

        # WHEN the same remote-write relation updates its rules to become valid
        now_valid_relation = dataclasses.replace(
            relation_after_invalid,
            remote_app_data={
                **relation_after_invalid.remote_app_data,
                "alert_rules": VALID_REMOTE_WRITE_RELATION.remote_app_data["alert_rules"],
            },
        )

        recovered_state = context.run(
            context.on.relation_changed(now_valid_relation),
            dataclasses.replace(
                invalid_state,
                relations=[s3, all_worker, now_valid_relation],
                containers=[
                    _nginx_container_for_alert_rules(),
                    nginx_prometheus_exporter_container,
                ],
            ),
        )
        recovered_relation = recovered_state.get_relation(INVALID_REMOTE_WRITE_RELATION.id)

        # THEN the previous invalid relation error is cleared and valid rules are written
        assert not _relation_errors(recovered_relation)
        assert _written_group_names(context, recovered_state) == {"remote-write-valid-group"}
        assert isinstance(recovered_state.unit_status, ActiveStatus)


