# Copyright 2023 Canonical
# See LICENSE file for licensing details.
"""Nginx workload."""

import logging
from typing import Dict, List

from coordinated_workers.nginx import (
    NginxLocationConfig,
    NginxUpstream,
)

from mimir_config import MimirRole

logger = logging.getLogger(__name__)


class NginxHelper:
    """Helper class to generate the nginx configuration."""

    _locations_distributor = [
        NginxLocationConfig(path="/distributor", backend="distributor"),
        NginxLocationConfig(path="/api/v1/push", backend="distributor"),
        NginxLocationConfig(path="/otlp/v1/metrics", backend="distributor"),
    ]

    _locations_ruler = [
        NginxLocationConfig(path="/prometheus/config/v1/rules", backend="ruler"),
        NginxLocationConfig(path="/prometheus/api/v1/rules", backend="ruler"),
        NginxLocationConfig(path="/prometheus/api/v1/alerts", backend="ruler"),
        NginxLocationConfig(path="/ruler/ring", backend="ruler", modifier="="),
    ]

    _locations_alertmanager = [
        NginxLocationConfig(path="/alertmanager", backend="alertmanager"),
        NginxLocationConfig(path="/multitenant_alertmanager/status", backend="alertmanager"),
        NginxLocationConfig(path="/api/v1/alerts", backend="alertmanager"),
    ]

    _locations_query_frontend = [
        NginxLocationConfig(path="/prometheus", backend="query-frontend"),
        # Buildinfo endpoint can go to any component
        NginxLocationConfig(
            path="/api/v1/status/buildinfo", backend="query-frontend", modifier="="
        ),
    ]

    _locations_compactor = [
        NginxLocationConfig(path="/api/v1/upload/block/", backend="compactor", modifier="="),
    ]

    _port = 8080
    _tls_port = 443

    def upstreams(self) -> List[NginxUpstream]:
        """Generate the list of Nginx upstream metadata configurations."""
        return [NginxUpstream(role.value, self._port, role.value) for role in MimirRole]

    def server_ports_to_locations(self) -> Dict[int, List[NginxLocationConfig]]:
        """Generate a mapping from server ports to a list of Nginx location configurations.

        Locations are provided for both the plain HTTP and TLS ports so that the
        nginx server block is valid regardless of when TLS certificates become
        available.  The Coordinator library controls which port actually receives
        traffic via ``listen_tls`` and ``unit.set_ports``.
        """
        all_locations = (
            self._locations_distributor
            + self._locations_ruler
            + self._locations_alertmanager
            + self._locations_query_frontend
            + self._locations_compactor
        )
        return {
            self._port: all_locations,
            self._tls_port: all_locations,
        }
