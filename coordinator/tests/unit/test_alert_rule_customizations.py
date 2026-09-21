# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the alert_rule_customizations config option."""

import json
from typing import Any, Dict, List, Set

import yaml
from ops import ActiveStatus, BlockedStatus
from scenario import Container, Exec, Relation, State

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def nginx_container():
    """Override the conftest fixture to match mimirtool with any number of rule file paths."""
    return Container(
        "nginx",
        can_connect=True,
        execs={
            Exec(["mimirtool", "rules", "sync"], return_code=0),
            Exec(["update-ca-certificates", "--fresh"], return_code=0),
            Exec(["nginx", "-s", "reload"], return_code=0),
        },
    )

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _alert_rules_json(groups: List[Dict[str, Any]]) -> str:
    return json.dumps({"groups": groups})


def _make_remote_write_relation(app_name: str, groups: List[Dict[str, Any]]) -> Relation:
    return Relation(
        "receive-remote-write",
        remote_app_name=app_name,
        remote_app_data={"alert_rules": _alert_rules_json(groups)},
    )


def _read_all_rules(context, state_out) -> Dict[str, List[Dict[str, Any]]]:
    fs = state_out.get_container("nginx").get_filesystem(context)
    rules_dir = fs / "etc" / "mimir-alerts" / "rules"
    if not rules_dir.exists():
        return {}
    result: Dict[str, List[Dict[str, Any]]] = {}
    for rule_file in sorted(p for p in rules_dir.iterdir() if p.is_file()):
        data = yaml.safe_load(rule_file.read_text())
        for group in data.get("groups", []):
            result[group["name"]] = group.get("rules", [])
    return result


def _alert_names_in_group(rules_by_group: Dict[str, List[Dict[str, Any]]], group_name: str) -> Set[str]:
    return {r["alert"] for r in rules_by_group.get(group_name, []) if "alert" in r}


# ---------------------------------------------------------------------------
# Shared rule fixtures
# ---------------------------------------------------------------------------

RULE_ALPHA = {
    "alert": "AlphaFiring",
    "expr": 'up{job="alpha"} == 0',
    "for": "5m",
    "labels": {"severity": "critical", "juju_application": "app-alpha"},
    "annotations": {"summary": "Alpha is down"},
}

RULE_BETA = {
    "alert": "BetaFiring",
    "expr": 'up{job="beta"} == 0',
    "for": "2m",
    "labels": {"severity": "warning", "juju_application": "app-beta"},
    "annotations": {"summary": "Beta is degraded"},
}

RULE_GAMMA = {
    "alert": "GammaFiring",
    "expr": 'rate(errors_total[5m]) > 0',
    "for": "1m",
    "labels": {"severity": "warning"},
    "annotations": {"summary": "Gamma has errors"},
}

GROUP_MAIN = {"name": "main-group", "rules": [RULE_ALPHA, RULE_BETA]}
GROUP_SECONDARY = {"name": "secondary-group", "rules": [RULE_GAMMA]}

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRemove:
    def test_remove_by_alert_name(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        rw_relation = _make_remote_write_relation("myapp", [GROUP_MAIN])
        state_in = State(
            leader=True,
            relations=[s3, all_worker, rw_relation],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={"alert_rule_customizations": "remove:\n  - where:\n      alert: AlphaFiring\n"},
        )
        state_out = context.run(context.on.config_changed(), state_in)
        rules = _read_all_rules(context, state_out)
        assert "AlphaFiring" not in _alert_names_in_group(rules, "main-group")
        assert "BetaFiring" in _alert_names_in_group(rules, "main-group")

    def test_remove_by_label(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        rw_relation = _make_remote_write_relation("myapp", [GROUP_MAIN])
        state_in = State(
            leader=True,
            relations=[s3, all_worker, rw_relation],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={
                "alert_rule_customizations": (
                    "remove:\n  - where:\n      labels:\n        juju_application: app-alpha\n"
                )
            },
        )
        state_out = context.run(context.on.config_changed(), state_in)
        rules = _read_all_rules(context, state_out)
        assert "AlphaFiring" not in _alert_names_in_group(rules, "main-group")
        assert "BetaFiring" in _alert_names_in_group(rules, "main-group")

    def test_remove_by_alert_and_label_and_semantics(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        rw_relation = _make_remote_write_relation("myapp", [GROUP_MAIN])
        state_in = State(
            leader=True,
            relations=[s3, all_worker, rw_relation],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={
                "alert_rule_customizations": (
                    "remove:\n"
                    "  - where:\n"
                    "      alert: BetaFiring\n"
                    "      labels:\n"
                    "        severity: warning\n"
                )
            },
        )
        state_out = context.run(context.on.config_changed(), state_in)
        rules = _read_all_rules(context, state_out)
        assert "AlphaFiring" in _alert_names_in_group(rules, "main-group")
        assert "BetaFiring" not in _alert_names_in_group(rules, "main-group")

    def test_remove_entire_group_by_group_selector(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        rw_relation = _make_remote_write_relation("myapp", [GROUP_MAIN, GROUP_SECONDARY])
        state_in = State(
            leader=True,
            relations=[s3, all_worker, rw_relation],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={"alert_rule_customizations": "remove:\n  - where:\n      group: main-group\n"},
        )
        state_out = context.run(context.on.config_changed(), state_in)
        rules = _read_all_rules(context, state_out)
        assert "main-group" not in rules
        assert "secondary-group" in rules

    def test_remove_last_rule_in_group_prunes_empty_group(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        rw_relation = _make_remote_write_relation("myapp", [GROUP_SECONDARY])
        state_in = State(
            leader=True,
            relations=[s3, all_worker, rw_relation],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={"alert_rule_customizations": "remove:\n  - where:\n      alert: GammaFiring\n"},
        )
        state_out = context.run(context.on.config_changed(), state_in)
        rules = _read_all_rules(context, state_out)
        assert "secondary-group" not in rules

    def test_remove_nonexistent_rule_is_noop(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        rw_relation = _make_remote_write_relation("myapp", [GROUP_MAIN])
        state_in = State(
            leader=True,
            relations=[s3, all_worker, rw_relation],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={"alert_rule_customizations": "remove:\n  - where:\n      alert: TotallyMadeUpAlert\n"},
        )
        state_out = context.run(context.on.config_changed(), state_in)
        rules = _read_all_rules(context, state_out)
        assert _alert_names_in_group(rules, "main-group") == {"AlphaFiring", "BetaFiring"}


class TestPatch:
    def test_patch_for_field(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        rw_relation = _make_remote_write_relation("myapp", [GROUP_MAIN])
        state_in = State(
            leader=True,
            relations=[s3, all_worker, rw_relation],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={
                "alert_rule_customizations": (
                    "patch:\n  - where:\n      alert: AlphaFiring\n    set:\n      for: 30m\n"
                )
            },
        )
        state_out = context.run(context.on.config_changed(), state_in)
        rules = _read_all_rules(context, state_out)
        alpha = next(r for r in rules["main-group"] if r.get("alert") == "AlphaFiring")
        assert alpha["for"] == "30m"
        beta = next(r for r in rules["main-group"] if r.get("alert") == "BetaFiring")
        assert beta["for"] == "2m"

    def test_patch_expr_field(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        new_expr = 'up{job="alpha", env="prod"} == 0'
        rw_relation = _make_remote_write_relation("myapp", [GROUP_MAIN])
        state_in = State(
            leader=True,
            relations=[s3, all_worker, rw_relation],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={
                "alert_rule_customizations": (
                    "patch:\n  - where:\n      alert: AlphaFiring\n    set:\n" f"      expr: '{new_expr}'\n"
                )
            },
        )
        state_out = context.run(context.on.config_changed(), state_in)
        rules = _read_all_rules(context, state_out)
        alpha = next(r for r in rules["main-group"] if r.get("alert") == "AlphaFiring")
        assert alpha["expr"] == new_expr

    def test_patch_adds_new_label(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        rw_relation = _make_remote_write_relation("myapp", [GROUP_MAIN])
        state_in = State(
            leader=True,
            relations=[s3, all_worker, rw_relation],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={
                "alert_rule_customizations": (
                    "patch:\n  - where:\n      alert: AlphaFiring\n    set:\n      labels:\n        team: platform\n"
                )
            },
        )
        state_out = context.run(context.on.config_changed(), state_in)
        rules = _read_all_rules(context, state_out)
        alpha = next(r for r in rules["main-group"] if r.get("alert") == "AlphaFiring")
        assert alpha["labels"]["team"] == "platform"
        assert alpha["labels"]["severity"] == "critical"

    def test_patch_overwrites_existing_label(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        rw_relation = _make_remote_write_relation("myapp", [GROUP_MAIN])
        state_in = State(
            leader=True,
            relations=[s3, all_worker, rw_relation],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={
                "alert_rule_customizations": (
                    "patch:\n  - where:\n      alert: AlphaFiring\n    set:\n      labels:\n        severity: info\n"
                )
            },
        )
        state_out = context.run(context.on.config_changed(), state_in)
        rules = _read_all_rules(context, state_out)
        alpha = next(r for r in rules["main-group"] if r.get("alert") == "AlphaFiring")
        assert alpha["labels"]["severity"] == "info"

    def test_patch_by_label_selector(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        rw_relation = _make_remote_write_relation("myapp", [GROUP_MAIN])
        state_in = State(
            leader=True,
            relations=[s3, all_worker, rw_relation],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={
                "alert_rule_customizations": (
                    "patch:\n  - where:\n      labels:\n        severity: warning\n    set:\n      for: 10m\n"
                )
            },
        )
        state_out = context.run(context.on.config_changed(), state_in)
        rules = _read_all_rules(context, state_out)
        alpha = next(r for r in rules["main-group"] if r.get("alert") == "AlphaFiring")
        beta = next(r for r in rules["main-group"] if r.get("alert") == "BetaFiring")
        assert alpha["for"] == "5m"
        assert beta["for"] == "10m"

    def test_patch_multiple_operations_each_applied(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        rw_relation = _make_remote_write_relation("myapp", [GROUP_MAIN])
        state_in = State(
            leader=True,
            relations=[s3, all_worker, rw_relation],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={
                "alert_rule_customizations": (
                    "patch:\n"
                    "  - where:\n      alert: AlphaFiring\n    set:\n      for: 15m\n"
                    "  - where:\n      alert: BetaFiring\n    set:\n      for: 20m\n"
                )
            },
        )
        state_out = context.run(context.on.config_changed(), state_in)
        rules = _read_all_rules(context, state_out)
        alpha = next(r for r in rules["main-group"] if r.get("alert") == "AlphaFiring")
        beta = next(r for r in rules["main-group"] if r.get("alert") == "BetaFiring")
        assert alpha["for"] == "15m"
        assert beta["for"] == "20m"


class TestCombined:
    def test_remove_and_patch_combined(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        rw_relation = _make_remote_write_relation("myapp", [GROUP_MAIN])
        state_in = State(
            leader=True,
            relations=[s3, all_worker, rw_relation],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={
                "alert_rule_customizations": (
                    "remove:\n  - where:\n      alert: AlphaFiring\n"
                    "patch:\n  - where:\n      alert: BetaFiring\n    set:\n      for: 25m\n"
                )
            },
        )
        state_out = context.run(context.on.config_changed(), state_in)
        rules = _read_all_rules(context, state_out)
        assert "AlphaFiring" not in _alert_names_in_group(rules, "main-group")
        beta = next(r for r in rules["main-group"] if r.get("alert") == "BetaFiring")
        assert beta["for"] == "25m"


class TestErrorHandling:
    def test_invalid_yaml_still_writes_rules(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        rw_relation = _make_remote_write_relation("myapp", [GROUP_MAIN])
        state_in = State(
            leader=True,
            relations=[s3, all_worker, rw_relation],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={"alert_rule_customizations": "remove: [unclosed bracket"},
        )
        state_out = context.run(context.on.config_changed(), state_in)
        rules = _read_all_rules(context, state_out)
        assert _alert_names_in_group(rules, "main-group") == {"AlphaFiring", "BetaFiring"}

    def test_unknown_top_level_key_still_writes_rules(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        rw_relation = _make_remote_write_relation("myapp", [GROUP_MAIN])
        state_in = State(
            leader=True,
            relations=[s3, all_worker, rw_relation],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={"alert_rule_customizations": "replace:\n  - where:\n      alert: AlphaFiring\n"},
        )
        state_out = context.run(context.on.config_changed(), state_in)
        rules = _read_all_rules(context, state_out)
        assert _alert_names_in_group(rules, "main-group") == {"AlphaFiring", "BetaFiring"}

    def test_empty_config_is_noop(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        rw_relation = _make_remote_write_relation("myapp", [GROUP_MAIN])
        state_in = State(
            leader=True,
            relations=[s3, all_worker, rw_relation],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={"alert_rule_customizations": ""},
        )
        state_out = context.run(context.on.config_changed(), state_in)
        rules = _read_all_rules(context, state_out)
        assert _alert_names_in_group(rules, "main-group") == {"AlphaFiring", "BetaFiring"}


class TestCollectUnitStatus:
    def test_invalid_customizations_set_blocked_status(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        state_in = State(
            leader=True,
            relations=[s3, all_worker],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={"alert_rule_customizations": "remove: [unclosed bracket"},
        )
        state_out = context.run(context.on.collect_unit_status(), state_in)
        assert isinstance(state_out.unit_status, BlockedStatus)

    def test_unknown_top_level_key_sets_blocked_status(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        state_in = State(
            leader=True,
            relations=[s3, all_worker],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={"alert_rule_customizations": "replace:\n  - where:\n      alert: AlphaFiring\n"},
        )
        state_out = context.run(context.on.collect_unit_status(), state_in)
        assert isinstance(state_out.unit_status, BlockedStatus)

    def test_valid_customizations_does_not_block(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        state_in = State(
            leader=True,
            relations=[s3, all_worker],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={"alert_rule_customizations": "remove:\n  - where:\n      alert: AlphaFiring\n"},
        )
        state_out = context.run(context.on.collect_unit_status(), state_in)
        assert isinstance(state_out.unit_status, ActiveStatus)

    def test_empty_config_does_not_block(self, context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
        state_in = State(
            leader=True,
            relations=[s3, all_worker],
            containers=[nginx_container, nginx_prometheus_exporter_container],
            config={"alert_rule_customizations": ""},
        )
        state_out = context.run(context.on.collect_unit_status(), state_in)
        assert isinstance(state_out.unit_status, ActiveStatus)
