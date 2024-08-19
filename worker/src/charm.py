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

from charms.tempo_k8s.v1.charm_tracing import trace_charm
from cosl.coordinated_workers.worker import CONFIG_FILE, Worker
from ops.charm import CharmBase
from ops.main import main
from ops.pebble import Layer

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)


@trace_charm(tracing_endpoint="_charm_tracing_endpoint", server_cert="_charm_tracing_cert")
class MimirWorkerK8SOperatorCharm(CharmBase):
    """A Juju Charmed Operator for Mimir."""

    _name = "mimir"
    _mimir_port = 8080

    def __init__(self, *args):
        super().__init__(*args)
        self.worker = Worker(
            charm=self,
            name="mimir",
            pebble_layer=self.pebble_layer,
            endpoints={"cluster": "mimir-cluster"},
            readiness_check_endpoint=f"http://localhost:{self._mimir_port}/ready",
        )
        self._charm_tracing_endpoint, self._charm_tracing_cert = self.worker.charm_tracing_config()

        self._container = self.model.unit.get_container(self._name)
        self.unit.set_ports(self._mimir_port)

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


if __name__ == "__main__":  # pragma: nocover
    main(MimirWorkerK8SOperatorCharm)
