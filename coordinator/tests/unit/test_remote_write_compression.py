# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Feature: compression of the alert rules received over receive-remote-write.

The coordinator advertises the alert rule encodings it can read, so that requirers know
they may compress large rule sets, and ingests the rules in either encoding.
"""

import json

import pytest
import yaml
from charms.prometheus_k8s.v1.prometheus_remote_write import (
    ALERT_RULES_ENCODINGS_KEY,
    ALERT_RULES_KEY,
    JSON_ENCODING,
    LZMA_ENCODING,
)
from cosl.utils import LZMABase64
from scenario import Container, Exec, Relation, State

ALERT_RULES = {
    "groups": [
        {
            "name": "compressed-remote-write-group",
            "rules": [
                {
                    "alert": "CompressedRuleFiring",
                    "expr": 'sum(rate({job="valid"}[5m])) > 0',
                    "for": "1m",
                    "labels": {"severity": "warning"},
                    "annotations": {"summary": "compressed"},
                }
            ],
        }
    ]
}

METADATA = json.dumps(
    {
        "model": "test",
        "model_uuid": "20ce8299-3634-4bef-8bd8-5ace6c8816b4",
        "application": "remote-write-compressed",
        "charm_name": "remote-write-compressed-charm",
    }
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


@pytest.mark.parametrize(
    "published",
    [
        pytest.param(json.dumps(ALERT_RULES), id="plain_json"),
        pytest.param(LZMABase64.compress(json.dumps(ALERT_RULES)), id="compressed"),
    ],
)
def test_alert_rules_are_ingested_in_either_encoding(
    context, s3, all_worker, nginx_prometheus_exporter_container, published
):
    # GIVEN a requirer that published its alert rules, compressed or not
    remote_write_relation = Relation(
        "receive-remote-write",
        remote_app_name="remote-write-compressed",
        remote_app_data={ALERT_RULES_KEY: published, "scrape_metadata": METADATA},
    )
    state_in = State(
        leader=True,
        relations=[s3, all_worker, remote_write_relation],
        containers=[_nginx_container_for_alert_rules(), nginx_prometheus_exporter_container],
    )

    # WHEN the relation changed event is processed
    state_out = context.run(context.on.relation_changed(remote_write_relation), state_in)

    # THEN the rules are written to disk regardless of the encoding they arrived in
    assert _written_group_names(context, state_out) == {"compressed-remote-write-group"}


def test_coordinator_advertises_the_encodings_it_can_read(
    context, s3, all_worker, nginx_prometheus_exporter_container
):
    # GIVEN a requirer related over receive-remote-write
    remote_write_relation = Relation(
        "receive-remote-write", remote_app_name="remote-write-compressed"
    )
    state_in = State(
        leader=True,
        relations=[s3, all_worker, remote_write_relation],
        containers=[_nginx_container_for_alert_rules(), nginx_prometheus_exporter_container],
    )

    # WHEN the relation joined event is processed
    state_out = context.run(context.on.relation_joined(remote_write_relation), state_in)

    # THEN requirers are told that compressed alert rules are supported
    advertised = state_out.get_relation(remote_write_relation.id).local_app_data[
        ALERT_RULES_ENCODINGS_KEY
    ]
    assert json.loads(advertised) == [LZMA_ENCODING, JSON_ENCODING]
