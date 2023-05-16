#!/usr/bin/env python3
# Copyright 2023 Canonical
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Charm the service.

Refer to the following post for a quick-start guide that will help you
develop a new k8s charm using the Operator Framework:

https://discourse.charmhub.io/t/4208
"""

import logging
import re
import socket
from dataclasses import asdict
from pathlib import Path
from typing import List, Literal, Optional, Union

import yaml
from charms.observability_libs.v0.juju_topology import JujuTopology
from charms.observability_libs.v1.kubernetes_service_patch import (
    KubernetesServicePatch,
)
from lightkube.models.core_v1 import ServicePort
from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, Relation, WaitingStatus
from ops.pebble import PathError, ProtocolError
from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass

DEFAULT_ROLES = ["all", "alertmanager"]
MIMIR_CONFIG = "/etc/mimir/mimir-config.yaml"
MIMIR_DIR = "/mimir"

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)


class InvalidConfigurationError(Exception):
    """Invalid configuration."""

    pass


class Memberlist(BaseModel):
    """Memberlist schema."""

    join_members: List[str]


class Tsdb(BaseModel):
    """Tsdb schema."""

    dir: str = "/data/ingester"


class BlocksStorage(BaseModel):
    """Blocks storage schema."""

    storage_prefix: str = "blocks"
    tsdb: Tsdb


class Limits(BaseModel):
    """Limits schema."""

    ingestion_rate: int = 0
    ingestion_burst_size: int = 0
    max_global_series_per_user: int = 0
    ruler_max_rules_per_rule_group: int = 0
    ruler_max_rule_groups_per_tenant: int = 0


class Kvstore(BaseModel):
    """Kvstore schema."""

    store: str = "memberlist"


class Ring(BaseModel):
    """Ring schema."""

    kvstore: Kvstore


class Distributor(BaseModel):
    """Distributor schema."""

    ring: Ring


class Ingester(BaseModel):
    """Ingester schema."""

    ring: Ring


class Ruler(BaseModel):
    """Ruler schema."""

    rule_path: str = "/data/ruler"
    alertmanager_url: Optional[str]


class Alertmanager(BaseModel):
    """Alertmanager schema."""

    data_dir: str = "/data/alertmanager"
    external_url: Optional[str]


class _S3StorageBackend(BaseModel):
    endpoint: str
    access_key_id: str
    secret_access_key: str
    insecure: bool = False
    signature_version: str = "v4"


class _FilesystemStorageBackend(BaseModel):
    dir: str


_StorageBackend = Union[_S3StorageBackend, _FilesystemStorageBackend]
_StorageKey = Union[Literal["filesystem"], Literal["s3"]]


@pydantic_dataclass
class CommonConfig:
    """Common config schema."""

    backend: _StorageKey
    _StorageKey: _StorageBackend

    def __post_init__(self):
        if not asdict(self).get("s3", "") and not asdict(self).get("s3", ""):
            raise InvalidConfigurationError("Common storage configuration must specify a type!")
        elif (asdict(self).get("filesystem", "") and not self.backend != "filesystem") or (
            asdict(self).get("s3", "") and not self.backend != "s3"
        ):
            raise InvalidConfigurationError(
                "Mimir `backend` type must include a configuration block which matches that type"
            )


class MimirBaseConfig(BaseModel):
    """Base class for mimir config schema."""

    target: str
    memberlist: Memberlist
    multitenancy_enabled: bool = True
    common: CommonConfig
    limits: Limits
    blocks_storage: Optional[BlocksStorage]
    distributor: Optional[Distributor]
    ingester: Optional[Ingester]
    ruler: Optional[Ruler]
    alertmanager: Optional[Alertmanager]


class MimirWorkerK8SOperatorCharm(CharmBase):
    """A Juju Charmed Operator for Mimir Worker."""

    _name = "mimir-worker"
    _instance_addr = "127.0.0.1"

    def __init__(self, *args):
        super().__init__(*args)
        self._container = self.unit.get_container(self._name)
        self._root_data_dir = Path(self.meta.containers["mimir-worker"].mounts["data"].location)

        self.topology = JujuTopology.from_charm(self)

        self.service_path = KubernetesServicePatch(
            self, [ServicePort(8080, name=self.app.name)]  # Same API endpoint for all components
        )

        self.framework.observe(
            self.on.mimir_worker_pebble_ready, self._on_pebble_ready  # pyright: ignore
        )
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.update_status, self._on_update_status)

        self._mimir_relation_names = [
            "compactor",
            "distributor",
            "ingester",
            "querier",
            "query-frontend",
            "store-gateway",
            "alertmanager",
            "ruler",
            "overrides-exporter",
            "query-scheduler",
        ]
        for rel_name in self._mimir_relation_names:
            self.framework.observe(
                self.on[rel_name.replace("-", "_")].relation_joined, self._on_mimir_relation_joined
            )

        self.framework.observe(self.on.upgrade_charm, self._update_all_endpoint_urls)

    def _on_mimir_relation_joined(self, event):
        self._update_endpoint_url(event.relation)
        self._update_config()
        # TODO update config on departed too, which a bit trickier because the departing relation
        #  is still listed.

    def _update_endpoint_url(self, relation: Relation):
        relation.data[self.unit]["api-endpoint"] = socket.getfqdn()  # TODO: add to schema

    def _update_all_endpoint_urls(self, _):
        for rel_name in self._mimir_relation_names:
            for relation in self.model.relations.get(rel_name, []):
                self._update_endpoint_url(relation)

    def _on_update_status(self, _):
        if not self._container.can_connect():
            self.unit.status = WaitingStatus("Waiting for Pebble ready")

    def _on_config_changed(self, event):
        if not self._container.can_connect():
            self.unit.status = WaitingStatus("Waiting for Pebble ready")
            return

        self._update_config()

    def _update_config(self):
        """Updates config."""
        restart = any(
            [
                self._update_mimir_config(),
                self._set_pebble_layer(),
            ]
        )

        if restart:
            self.restart()

    def _on_pebble_ready(self, event):
        self.unit.set_workload_version(self._mimir_version or "")
        self._update_config()
        self.unit.status = ActiveStatus()

    def _set_pebble_layer(self) -> bool:
        """Set Pebble layer.

        Returns: True if Pebble layer was added, otherwise False.
        """
        current_layer = self._container.get_plan()
        new_layer = self._pebble_layer

        if (
            "services" not in current_layer.to_dict()
            or current_layer.services != new_layer["services"]
        ):
            self._container.add_layer(self._name, new_layer, combine=True)
            return True

        return False

    @property
    def _pebble_layer(self):
        """Return a dictionary representing a Pebble layer."""
        return {
            "summary": "mimir worker layer",
            "description": "pebble config layer for mimir worker",
            "services": {
                "mimir-worker": {
                    "override": "replace",
                    "summary": "mimir worker daemon",
                    "command": f"/bin/mimir --config.file={MIMIR_CONFIG} -target {','.join(self._mimir_roles)}",
                    "startup": "enabled",
                }
            },
        }

    @property
    def _mimir_roles(self) -> List[str]:
        """Return a set of the roles Mimir worker should take on."""
        # Filter out of all possible relations those that actually are active
        active_rel_names = [k for k in self._mimir_relation_names if self.model.relations.get(k)]
        # Assuming relation names match exactly Mimir roles.
        return sorted(active_rel_names) or DEFAULT_ROLES

    @property
    def _mimir_version(self) -> Optional[str]:
        if not self._container.can_connect():
            return None

        version_output, _ = self._container.exec(["/bin/mimir", "-version"]).wait_output()
        # Output looks like this:
        # Mimir, version 2.4.0 (branch: HEAD, revision 32137ee)
        if result := re.search(r"[Vv]ersion:?\s*(\S+)", version_output):
            return result.group(1)
        return None

    def _update_mimir_config(self) -> bool:
        """Set Mimir config.

        Returns: True if config has changed, otherwise False.
        Raises: BlockedStatusError exception if PebbleError, ProtocolError, PathError exceptions
            are raised by container.remove_path
        """
        config = self._build_mimir_config()

        if self._running_mimir_config() != config:
            config_as_yaml = yaml.safe_dump(config)
            self._container.push(MIMIR_CONFIG, config_as_yaml, make_dirs=True)
            logger.info("Pushed new Mimir configuration")
            return True

        return False

    def _build_mimir_config(self) -> dict:
        """Build mimir config.

        - Place all data dirs under a common root data dir, so files are persisted across upgrades.
          Following the default names from official docs:
          https://grafana.com/docs/mimir/latest/references/configuration-parameters/
        """
        return {
            "alertmanager": {
                "data_dir": str(self._root_data_dir / "data-alertmanager"),
            },
            "compactor": {
                "data_dir": str(self._root_data_dir / "data-compactor"),
            },
            "blocks_storage": {
                "bucket_store": {
                    "sync_dir": str(self._root_data_dir / "tsdb-sync"),
                },
            },
        }

    def _running_mimir_config(self) -> Optional[dict]:
        """Return the Mimir config as dict, or None if retrieval failed."""
        if not self._container.can_connect():
            logger.debug("Could not connect to Mimir container")
            return None

        try:
            raw_current = self._container.pull(MIMIR_CONFIG).read()
            return yaml.safe_load(raw_current)
        except (ProtocolError, PathError) as e:
            logger.warning(
                "Could not check the current Mimir configuration due to "
                "a failure in retrieving the file: %s",
                e,
            )
            return None

    def restart(self):
        """Restart the pebble service or start if not already running."""
        if self._container.get_service(self._name).is_running():
            self._container.restart(self._name)
        else:
            self._container.start(self._name)


if __name__ == "__main__":  # pragma: nocover
    main(MimirWorkerK8SOperatorCharm)
