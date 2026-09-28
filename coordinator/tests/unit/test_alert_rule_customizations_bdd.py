# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest-bdd step definitions for the alert_rule_customizations feature file.

Feature file: tests/unit/features/alert_rule_customizations.feature
"""

import pytest
import yaml
from _alert_rule_customization_helpers import (
    _make_remote_write_relation,
    read_all_rules,
)
from ops.model import ActiveStatus, BlockedStatus
from pytest_bdd import given, parsers, scenarios, then, when
from scenario import Container, Exec, State

scenarios("features/alert_rule_customizations.feature")


# ---------------------------------------------------------------------------
# Fixtures: override nginx_container to accept any mimirtool invocation
# (the rule file paths are dynamic and cannot be predicted in advance)
# ---------------------------------------------------------------------------


@pytest.fixture
def nginx_container():
    """Override the conftest fixture to match mimirtool with any rule file paths."""
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
# Given
# ---------------------------------------------------------------------------


@given(
    parsers.parse("the charm provides the following alert rules:\n{docstring}"),
    target_fixture="rw_relation",
)
def given_charm_provides_alert_rules(docstring):
    """Build a receive-remote-write relation carrying the rule groups from the docstring."""
    groups = _docstring_to_groups(docstring)
    return _make_remote_write_relation("myapp", groups)


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------


def _run_config_changed(context, nginx_container, nginx_prometheus_exporter_container, config, rw_relation, s3, all_worker):
    """Run config_changed through the charm for the given relation and config."""
    state_in = State(
        leader=True,
        relations=[s3, all_worker, rw_relation],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        config=config,
    )
    return context.run(context.on.config_changed(), state_in)


@when(
    parsers.parse("the customization is applied:\n{docstring}"),
    target_fixture="state_out",
)
def when_customization_is_applied(docstring, rw_relation, context, nginx_container, nginx_prometheus_exporter_container, s3, all_worker):
    """Set the customization config and run config_changed through the charm."""
    return _run_config_changed(
        context,
        nginx_container,
        nginx_prometheus_exporter_container,
        {"alert_rule_customizations": docstring},
        rw_relation,
        s3,
        all_worker,
    )


@when(
    parsers.parse('the customization is set to invalid YAML: "{config_string}"'),
    target_fixture="state_out",
)
def when_customization_is_invalid_yaml(config_string, rw_relation, context, nginx_container, nginx_prometheus_exporter_container, s3, all_worker):
    return _run_config_changed(
        context,
        nginx_container,
        nginx_prometheus_exporter_container,
        {"alert_rule_customizations": config_string},
        rw_relation,
        s3,
        all_worker,
    )


@when(
    "the customization contains an unknown top-level key",
    target_fixture="state_out",
)
def when_customization_unknown_top_level_key(rw_relation, context, nginx_container, nginx_prometheus_exporter_container, s3, all_worker):
    config = {
        "alert_rule_customizations": (
            "replace:\n"
            "  - where:\n"
            "      alert: AlphaFiring\n"
        )
    }
    return _run_config_changed(context, nginx_container, nginx_prometheus_exporter_container, config, rw_relation, s3, all_worker)


@when(
    "the customization contains an invalid key within an operation",
    target_fixture="state_out",
)
def when_customization_invalid_operation_key(rw_relation, context, nginx_container, nginx_prometheus_exporter_container, s3, all_worker):
    config = {
        "alert_rule_customizations": (
            "patch:\n"
            "  - where:\n"
            "      alert: AlphaFiring\n"
            "    set:\n"
            "      duration: 5m\n"
        )
    }
    return _run_config_changed(context, nginx_container, nginx_prometheus_exporter_container, config, rw_relation, s3, all_worker)


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------


def _written_alert_names(state_out, context) -> set:
    rules = read_all_rules(context, state_out)
    return {
        r["alert"]
        for group_rules in rules.values()
        for r in group_rules
        if "alert" in r
    }


@then(parsers.parse('alert "{name}" is not written'))
def then_alert_not_written(name, state_out, context):
    written = _written_alert_names(state_out, context)
    assert name not in written, f"alert {name!r} was written but should not be"


@then(parsers.parse('alert "{name}" is written'))
def then_alert_written(name, state_out, context):
    written = _written_alert_names(state_out, context)
    assert name in written, f"alert {name!r} was not written"


@then(parsers.re(r'alert "(?P<name>[^"]+)" has "(?P<field>[^"]+)" equal to ["\'](?P<value>.+)["\']'))
def then_alert_field(name, field, value, state_out, context):
    rule = _find_alert(state_out, context, name)
    assert rule.get(field) == value, f"expected {field}={value!r}, got {rule.get(field)!r}"


@then(parsers.parse('alert "{name}" has label "{key}" equal to "{value}"'))
def then_alert_label(name, key, value, state_out, context):
    rule = _find_alert(state_out, context, name)
    labels = rule.get("labels", {})
    assert labels.get(key) == value, f"expected label {key}={value!r}, got {labels.get(key)!r}"


@then("the charm is in BlockedStatus for alert_rule_customizations")
def then_blocked_customizations(state_out):
    status = state_out.unit_status
    assert isinstance(status, BlockedStatus), f"expected BlockedStatus, got {status!r}"
    assert "customization" in status.message.lower() or "validate" in status.message.lower(), (
        f"BlockedStatus message does not mention customizations: {status.message!r}"
    )


@then("the charm is in ActiveStatus for alert_rule_customizations")
def then_active_customizations(state_out):
    status = state_out.unit_status
    assert isinstance(status, ActiveStatus), f"expected ActiveStatus, got {status!r}"


@then("all provided alert rules are still written unchanged")
def then_all_rules_still_written(state_out, context):
    rules = read_all_rules(context, state_out)
    assert rules, "no alert rules were written to disk"


@then("the written alert rules are unchanged")
def then_written_rules_unchanged(state_out, rw_relation, context, nginx_container, nginx_prometheus_exporter_container, s3, all_worker):
    """Compare the on-disk rules against a baseline run with no customizations applied."""
    baseline = _run_config_changed(
        context,
        nginx_container,
        nginx_prometheus_exporter_container,
        {"alert_rule_customizations": ""},
        rw_relation,
        s3,
        all_worker,
    )
    baseline_rules = read_all_rules(context, baseline)
    actual_rules = read_all_rules(context, state_out)
    assert actual_rules == baseline_rules, (
        f"the written alert rules changed:\nactual={actual_rules!r}\nbaseline={baseline_rules!r}"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _docstring_to_groups(docstring):
    """Parse a feature-file docstring into a list of rule groups.

    The docstring maps group name -> list of rules (see the feature file).
    """
    parsed = yaml.safe_load(docstring)
    return [
        {"name": group_name, "rules": rules}
        for group_name, rules in parsed.items()
    ]


def _find_alert(state_out, context, name):
    """Return the rule dict for an alert of the given name across all written groups."""
    rules = read_all_rules(context, state_out)
    for group_rules in rules.values():
        for rule in group_rules:
            if rule.get("alert") == name:
                return rule
    raise AssertionError(f"alert {name!r} not found in written rules")
