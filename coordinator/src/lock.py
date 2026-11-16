# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Persistence of the per-role replication-factor lock.

Once a role has reached the minimum worker count, its replication factor is "locked" so that a
transient dip in the number of units does not downgrade it. The lock state must outlive a single
hook (and be shared between coordinator units), so it is stored in the peer relation app databag.
"""

import json
import logging
from typing import Dict

import ops

logger = logging.getLogger(__name__)

# Peer relation app databag key under which the lock state is stored.
LOCK_STATE_KEY = "replication-lock-state"


class Lock:
    """Per-role replication-factor lock, persisted in the peer relation app databag.

    The state is loaded on instantiation and exposed through `state`, a mapping of
    role name to "locked" flag. Callers mutate `state` in place and call `save` to persist it.
    """

    def __init__(self, charm: ops.CharmBase, relation_name: str = "mimir-peers"):
        self._charm = charm
        self._relation_name = relation_name
        self.state: Dict[str, bool] = self._load()

    def _load(self) -> Dict[str, bool]:
        """Load the persisted lock state from the peer relation."""
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation:
            return {}
        raw = relation.data[self._charm.app].get(LOCK_STATE_KEY)
        if not raw:
            return {}
        try:
            state = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to decode replication lock state from peer relation data")
            return {}
        if not isinstance(state, dict):
            return {}
        return {str(k): bool(v) for k, v in state.items()}

    def save(self) -> None:
        """Persist the lock state to the peer relation app databag (leader only)."""
        if not self._charm.unit.is_leader():
            return
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation:
            return
        relation.data[self._charm.app][LOCK_STATE_KEY] = json.dumps(self.state)
