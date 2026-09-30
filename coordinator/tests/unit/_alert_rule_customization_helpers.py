# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Shared helpers for the alert_rule_customizations BDD feature tests.

These helpers are reused by :mod:`tests.unit.test_alert_rule_customizations_bdd`
to drive the charm through the scenario framework and assert on the resulting
alert rule files and charm status.
"""

import json
from typing import Any, Dict, List

import yaml
from ops import BlockedStatus
from scenario import Relation

# ---------------------------------------------------------------------------
# Relation construction
# ---------------------------------------------------------------------------


def _make_remote_write_relation(app_name: str, groups: List[Dict[str, Any]]) -> Relation:
    """Build a receive-remote-write relation carrying the given rule groups."""
    return Relation(
        "receive-remote-write",
        remote_app_name=app_name,
        remote_app_data={"alert_rules": json.dumps({"groups": groups})},
    )


# ---------------------------------------------------------------------------
# Reading results
# ---------------------------------------------------------------------------


def read_all_rules(context, state_out) -> Dict[str, List[Dict[str, Any]]]:
    """Return all alert rules written to /etc/mimir-alerts/rules/.

    Returns a mapping of group_name -> list[rule_dict].
    """
    fs = state_out.get_container("nginx").get_filesystem(context)
    rules_dir = fs / "etc" / "mimir-alerts" / "rules"
    if not rules_dir.exists():
        return {}

    result: Dict[str, List[Dict[str, Any]]] = {}
    for rule_file in sorted(path for path in rules_dir.iterdir() if path.is_file()):
        data = yaml.safe_load(rule_file.read_text())
        for group in data.get("groups", []):
            result[group["name"]] = group.get("rules", [])
    return result


def customization_status(state_out) -> Any:
    """Return whether the charm has a BlockedStatus due to alert rule customizations.

    Checks the unit status for a BlockedStatus message related to customizations.
    """
    status = state_out.unit_status
    if isinstance(status, BlockedStatus) and "customization" in status.message.lower():
        return status
    # Return Active placeholder if not blocked due to customizations
    from ops import ActiveStatus

    return ActiveStatus()
