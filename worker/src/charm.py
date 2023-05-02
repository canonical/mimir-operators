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
from typing import Optional

import yaml
from charms.observability_libs.v0.juju_topology import JujuTopology
from charms.observability_libs.v1.kubernetes_service_patch import (
    KubernetesServicePatch,
    ServicePort,
)
from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus
from ops.pebble import PathError, ProtocolError

MIMIR_CONFIG = "/etc/mimir/mimir-config.yaml"
MIMIR_DIR = "/mimir"

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)

VALID_LOG_LEVELS = ["info", "debug", "warning", "error", "critical"]


class MimirWorkerK8SOperatorCharm(CharmBase):
    """A Juju Charmed Operator for Mimir Worker."""

    _name = "mimir-worker"
    _http_listen_port = 9009
    _instance_addr = "127.0.0.1"

    def __init__(self, *args):
        super().__init__(*args)
        self._container = self.unit.get_container(self._name)

        self.topology = JujuTopology.from_charm(self)

        self.service_path = KubernetesServicePatch(
            self, [ServicePort(self._http_listen_port, name=self.app.name)]
        )

        self.framework.observe(self.on.mimir_worker_pebble_ready, self._on_pebble_ready)
        self.framework.observe(self.on.config_changed, self._on_config_changed)

    def _on_config_changed(self, event):
        if not self._container.can_connect():
            return

        restart = any(
            [
                self._update_mimir_config(),
                self._set_pebble_layer(),
            ]
        )

        if restart:
            self.restart()

    def _on_pebble_ready(self, event):
        # Temp: Please remove when a real config file is written.
        self._container.push(MIMIR_CONFIG, "", make_dirs=True)

        self.unit.set_workload_version(self._mimir_version)
        self._update_mimir_config()
        self._set_pebble_layer()
        self.restart()
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
                    "command": f"/bin/mimir --config.file={MIMIR_CONFIG} -target {self.config.get('roles')}",
                    "startup": "enabled",
                }
            },
        }

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
        # TODO: Implement this!
        return {}

    def _running_mimir_config(self) -> dict:
        if not self._container.can_connect():
            logger.debug("Could not connect to Mimir container")
            return {}

        try:
            raw_current = self._container.pull(MIMIR_CONFIG).read()
            return yaml.safe_load(raw_current)
        except (ProtocolError, PathError) as e:
            logger.warning(
                "Could not check the current Mimir configuration due to "
                "a failure in retrieving the file: %s",
                e,
            )
            return {}

    def restart(self):
        """Restart the pebble service or start if not already running."""
        if self._container.get_service(self._name).is_running():
            self._container.restart(self._name)
        else:
            self._container.start(self._name)


if __name__ == "__main__":  # pragma: nocover
    main(MimirWorkerK8SOperatorCharm)
