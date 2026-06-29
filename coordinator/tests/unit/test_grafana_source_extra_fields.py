# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.
import json

from ops.testing import Relation, State


def test_grafana_source_relation_extra_fields(
    context,
    s3,
    all_worker,
    nginx_container,
    nginx_prometheus_exporter_container,
):
    # GIVEN a grafana-source relation, s3 and all_worker relations, nginx containers, and the unit is leader
    grafana_source = Relation("grafana-source", remote_app_name="grafana")
    state_in = State(
        relations=[s3, all_worker, grafana_source],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        leader=True,
    )
    # WHEN update_status is triggered
    state_out = context.run(context.on.update_status(), state_in)
    gs_data = json.loads(
        state_out.get_relation(grafana_source.id).local_app_data["grafana_source_data"]
    )
    # THEN the grafana-source relation data includes timeInterval=60s and httpHeaderName1
    # NOTE: OTel collector scrapes every 60s by default. Grafana defaults to 15s if not informed,
    # causing dashboard errors. This assertion ensures Mimir communicates the correct interval.
    assert gs_data["extra_fields"]["timeInterval"] == "60s"
    assert gs_data["extra_fields"]["httpHeaderName1"] == "X-Scope-OrgID"
