# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests that relation data falls back to the internal URL when ingress is revoked."""

import dataclasses
import json
from unittest.mock import MagicMock, PropertyMock, patch

from scenario import Relation, State

MIMIR_URL = "http://internal.com/"
MIMIR_INGRESS_URL = "http://ingress.test/mimir"
MIMIR_INGRESS_URL_HTTPS = "https://ingress.test/mimir"


@patch("charm.MimirCoordinatorK8SOperatorCharm._service_url", PropertyMock(return_value=MIMIR_URL))
@patch("charm.MimirCoordinatorK8SOperatorCharm.internal_url", PropertyMock(return_value=MIMIR_URL))
@patch("charm.MimirCoordinatorK8SOperatorCharm._set_alerts", MagicMock())
def test_remote_write_url_uses_internal_url_after_ingress_revoked(
    context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container,
):
    """After ingress is revoked, remote-write and grafana-source URLs fall back to the internal URL."""
    # GIVEN ingress is ready with a URL, a receive-remote-write consumer, and a grafana-source consumer
    ingress = Relation(
        "ingress",
        remote_app_data={"ingress": json.dumps({"url": MIMIR_INGRESS_URL})},
    )
    remote_write = Relation("receive-remote-write")
    grafana_source = Relation("grafana-source")

    state = State(
        relations=[s3, all_worker, ingress, remote_write, grafana_source],
        leader=True,
        containers=[nginx_container, nginx_prometheus_exporter_container],
    )

    # WHEN ingress becomes ready
    state = context.run(context.on.relation_changed(ingress), state)

    # THEN remote-write URL contains the ingress URL
    rw_url_after_ready = json.loads(
        state.get_relation(remote_write.id).local_unit_data["remote_write"]
    )["url"]
    assert MIMIR_INGRESS_URL.rstrip("/") in rw_url_after_ready

    # AND grafana-source URL contains the ingress URL
    gs_url_after_ready = state.get_relation(grafana_source.id).local_app_data["grafana_source_app_host"]
    assert MIMIR_INGRESS_URL.rstrip("/") in gs_url_after_ready

    # WHEN ingress is revoked
    state = context.run(context.on.relation_broken(state.get_relation(ingress.id)), state)

    # THEN remote-write URL falls back to the internal URL
    rw_url_after_revoked = json.loads(
        state.get_relation(remote_write.id).local_unit_data["remote_write"]
    )["url"]
    assert rw_url_after_revoked == f"{MIMIR_URL.rstrip('/')}/api/v1/push", (
        f"Expected internal URL but got: {rw_url_after_revoked}"
    )

    # AND grafana-source URL falls back to the internal URL
    gs_url_after_revoked = state.get_relation(grafana_source.id).local_app_data["grafana_source_app_host"]
    assert MIMIR_URL.rstrip("/") in gs_url_after_revoked
    assert MIMIR_INGRESS_URL.rstrip("/") not in gs_url_after_revoked


@patch("charm.MimirCoordinatorK8SOperatorCharm._service_url", PropertyMock(return_value=MIMIR_URL))
@patch("charm.MimirCoordinatorK8SOperatorCharm.internal_url", PropertyMock(return_value=MIMIR_URL))
@patch("charm.MimirCoordinatorK8SOperatorCharm._set_alerts", MagicMock())
def test_related_charms_updated_when_traefik_switches_ingress_url_to_https(
    context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container,
):
    """When Traefik updates the ingress URL from http to https, downstream relations are updated."""
    # GIVEN ingress is ready with an http URL, a receive-remote-write consumer, and a grafana-source consumer
    ingress = Relation(
        "ingress",
        remote_app_data={"ingress": json.dumps({"url": MIMIR_INGRESS_URL})},
    )
    remote_write = Relation("receive-remote-write")
    grafana_source = Relation("grafana-source")

    state = State(
        relations=[s3, all_worker, ingress, remote_write, grafana_source],
        leader=True,
        containers=[nginx_container, nginx_prometheus_exporter_container],
    )

    # WHEN ingress becomes ready with an http URL
    state = context.run(context.on.relation_changed(ingress), state)

    # THEN remote-write URL contains the http ingress URL
    rw_url_before = json.loads(
        state.get_relation(remote_write.id).local_unit_data["remote_write"]
    )["url"]
    assert rw_url_before.startswith("http://"), f"Expected http URL but got: {rw_url_before}"
    assert MIMIR_INGRESS_URL.rstrip("/") in rw_url_before

    # AND grafana-source URL contains the http ingress URL
    gs_url_before = state.get_relation(grafana_source.id).local_app_data["grafana_source_app_host"]
    assert MIMIR_INGRESS_URL.rstrip("/") in gs_url_before

    # WHEN Traefik updates the ingress relation data to provide an https URL
    ingress_after = dataclasses.replace(
        state.get_relation(ingress.id),
        remote_app_data={"ingress": json.dumps({"url": MIMIR_INGRESS_URL_HTTPS})},
    )
    state = dataclasses.replace(
        state,
        relations=frozenset(
            ingress_after if r.id == ingress.id else r for r in state.relations
        ),
    )
    state = context.run(context.on.relation_changed(ingress_after), state)

    # THEN remote-write URL is updated to the https ingress URL
    rw_url_after = json.loads(
        state.get_relation(remote_write.id).local_unit_data["remote_write"]
    )["url"]
    assert rw_url_after.startswith("https://"), (
        f"Expected https URL after Traefik switched to https, but got: {rw_url_after}"
    )
    assert MIMIR_INGRESS_URL_HTTPS.rstrip("/") in rw_url_after

    # AND grafana-source URL is updated to the https ingress URL
    gs_url_after = state.get_relation(grafana_source.id).local_app_data["grafana_source_app_host"]
    assert MIMIR_INGRESS_URL_HTTPS.rstrip("/") in gs_url_after, (
        f"Expected https ingress URL in grafana-source but got: {gs_url_after}"
    )
    assert MIMIR_INGRESS_URL.rstrip("/") not in gs_url_after or gs_url_after.startswith("https://"), (
        f"grafana-source still advertises http URL after Traefik switched to https: {gs_url_after}"
    )
