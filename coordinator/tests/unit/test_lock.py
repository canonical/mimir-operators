# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

import json
from unittest.mock import MagicMock

import pytest

from lock import LOCK_STATE_KEY, Lock


def _charm(app_data=None, *, leader=True, has_relation=True):
    """Build a stand-in charm exposing just what `Lock` uses."""
    charm = MagicMock()
    charm.unit.is_leader.return_value = leader
    if has_relation:
        relation = MagicMock()
        relation.data = {charm.app: dict(app_data or {})}
        charm.model.get_relation.return_value = relation
    else:
        charm.model.get_relation.return_value = None
    return charm


def test_state_is_empty_without_peer_relation():
    assert Lock(_charm(has_relation=False)).state == {}


def test_state_is_empty_when_nothing_persisted():
    assert Lock(_charm()).state == {}


def test_state_is_loaded_from_peer_databag():
    charm = _charm({LOCK_STATE_KEY: json.dumps({"ingester": True, "store-gateway": False})})
    assert Lock(charm).state == {"ingester": True, "store-gateway": False}


@pytest.mark.parametrize("raw", ["not-json", json.dumps(["ingester"]), json.dumps("x")])
def test_corrupt_state_is_ignored(raw):
    assert Lock(_charm({LOCK_STATE_KEY: raw})).state == {}


def test_save_writes_state_to_peer_databag():
    charm = _charm()
    lock = Lock(charm)
    lock.state["ingester"] = True

    lock.save()

    relation = charm.model.get_relation.return_value
    assert json.loads(relation.data[charm.app][LOCK_STATE_KEY]) == {"ingester": True}


def test_save_roundtrips_through_a_new_instance():
    charm = _charm()
    lock = Lock(charm)
    lock.state["alertmanager"] = True
    lock.save()

    assert Lock(charm).state == {"alertmanager": True}


def test_save_is_a_noop_for_non_leaders():
    charm = _charm(leader=False)
    lock = Lock(charm)
    lock.state["ingester"] = True

    lock.save()

    relation = charm.model.get_relation.return_value
    assert LOCK_STATE_KEY not in relation.data[charm.app]


def test_save_is_a_noop_without_peer_relation():
    lock = Lock(_charm(has_relation=False))
    lock.state["ingester"] = True
    lock.save()  # must not raise
