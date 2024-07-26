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

from charms.tempo_k8s.v1.charm_tracing import trace_charm
from cosl.coordinated_workers.worker import CERT_FILE, CONFIG_FILE, Worker
from ops.charm import CharmBase
from ops.main import main
from ops.pebble import Layer

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)


@trace_charm(
    tracing_endpoint="tempo_endpoint",
    server_cert="server_cert_path",
)
class MimirWorkerK8SOperatorCharm(CharmBase):
    """A Juju Charmed Operator for Mimir."""

    _name = "mimir"
    _instance_addr = "127.0.0.1"
    _mimir_port = 8080

    def __init__(self, *args):
        super().__init__(*args)
        self.worker = Worker(
            charm=self,
            name="mimir",
            pebble_layer=self.pebble_layer,
            endpoints={"cluster": "mimir-cluster"},
        )

        self._container = self.model.unit.get_container(self._name)
        self.unit.set_ports(self._mimir_port)

        self.framework.observe(
            self.on.mimir_pebble_ready, self._on_pebble_ready  # pyright: ignore
        )

    def _on_pebble_ready(self, _):
        self.unit.set_workload_version(self._mimir_version or "")

    def pebble_layer(self, worker: Worker) -> Layer:
        """Return a dictionary representing a Pebble layer."""
        targets = ",".join(sorted(worker.roles))

        return Layer(
            {
                "summary": "mimir worker layer",
                "description": "pebble config layer for mimir worker",
                "services": {
                    "mimir": {
                        "override": "replace",
                        "summary": "mimir worker daemon",
                        "command": f"/bin/mimir --config.file={CONFIG_FILE} -target {targets} -auth.multitenancy-enabled=false",
                        "startup": "enabled",
                    }
                },
            }
        )

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

    @property
    def tempo_endpoint(self) -> Optional[str]:
        """Tempo endpoint for charm tracing."""
        if endpoints := self.worker.cluster.get_tracing_receivers():
            return endpoints.get("otlp_http", None)

    @property
    def server_cert_path(self) -> Optional[str]:
        """Server certificate path for tls tracing."""
        return CERT_FILE


if __name__ == "__main__":  # pragma: nocover
    main(MimirWorkerK8SOperatorCharm)
