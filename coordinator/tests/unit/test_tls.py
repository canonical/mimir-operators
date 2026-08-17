# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import PropertyMock, patch

import scenario
from charmlibs.nginx_k8s import Nginx
from helpers import get_relation_data
from scenario import Relation, State

from charm import NGINX_PORT, MimirCoordinatorK8SOperatorCharm


def test_ingress_tls(
    context,
    s3,
    all_worker,
    nginx_container,
    nginx_prometheus_exporter_container,
):
    # GIVEN Loki is related over the ingress and certificates endpoints
    ingress = Relation("ingress")
    certificates = Relation("certificates")

    state_in = State(
        relations=[
            s3,
            all_worker,
            ingress,
            certificates,
        ],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=scenario.ActiveStatus(),
        leader=True,
    )

    # WHEN TLS is not yet available
    with context(context.on.relation_joined(ingress), state_in) as mgr:
        charm = mgr.charm
        state_out = mgr.run()

        # THEN there are no certificates on disk
        assert not charm.coordinator.nginx.are_certificates_on_disk

        # AND Loki publishes its Nginx non-TLS port in the ingress databag
        assert get_relation_data(state_out.relations, "ingress", "port") == str(NGINX_PORT)

    # AND WHEN TLS is enabled
    with patch.object(Nginx, "are_certificates_on_disk", return_value=True):
        # AND the ingress databag is updated
        state_out = context.run(context.on.relation_changed(ingress), state_in)

        # THEN Loki publishes its Nginx TLS scheme in the ingress databag (port stays the same)
        assert get_relation_data(state_out.relations, "ingress", "scheme") == '"https"'
        assert get_relation_data(state_out.relations, "ingress", "port") == str(NGINX_PORT)


def _rules_sync_state(s3, all_worker, nginx_container, nginx_prometheus_exporter_container):
    return State(
        relations=[s3, all_worker],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=scenario.ActiveStatus(),
        leader=True,
    )


def test_rules_sync_command_omits_tls_ca_path_over_http(
    context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container
):
    # GIVEN Mimir is served over HTTP (no certificates on disk)
    state_in = _rules_sync_state(
        s3, all_worker, nginx_container, nginx_prometheus_exporter_container
    )
    with context(context.on.update_status(), state_in) as mgr:
        charm = mgr.charm
        # WHEN the mimirtool rules sync command is built
        command = charm._rules_sync_command(["/etc/mimir-alerts/rules/example.rules"])

    # THEN the address is http and no TLS CA path is passed
    assert any(arg.startswith("--address=http://") for arg in command)
    assert not any(arg.startswith("--tls-ca-path=") for arg in command)


def test_rules_sync_command_adds_tls_ca_path_over_https(
    context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container
):
    # GIVEN Mimir is served over HTTPS (the cert is internally-issued; its CA is on disk)
    state_in = _rules_sync_state(
        s3, all_worker, nginx_container, nginx_prometheus_exporter_container
    )
    with context(context.on.update_status(), state_in) as mgr:
        charm = mgr.charm
        with patch.object(
            MimirCoordinatorK8SOperatorCharm,
            "internal_url",
            new_callable=PropertyMock,
            return_value="https://mimir.test:8080",
        ):
            # WHEN the mimirtool rules sync command is built
            command = charm._rules_sync_command(["/etc/mimir-alerts/rules/example.rules"])

    # THEN mimirtool is told to verify against Mimir's CA bundle (otelcol-operator#328)
    assert any(arg.startswith("--tls-ca-path=") for arg in command)
