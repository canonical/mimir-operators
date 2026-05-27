import json
import logging
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote

import jubilant
import requests
import yaml
from lightkube import Client
from lightkube.generic_resource import create_namespaced_resource
from minio import Minio
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import format_trace_id
from tenacity import retry, stop_after_attempt, wait_fixed, wait_exponential

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]


def charm_resources(metadata_file: str | None = None) -> dict[str, str]:
    if metadata_file is None:
        metadata_file = str(REPO_ROOT / "coordinator" / "charmcraft.yaml")
    with open(metadata_file, "r") as file:
        metadata = yaml.safe_load(file)
    resources = {}
    for res, data in metadata["resources"].items():
        resources[res] = data["upstream-source"]
    return resources


def get_leader_address(juju: jubilant.Juju, app_name: str) -> str:
    """Get the address of the leader unit of an application."""
    status = juju.status()
    for name, unit in status.apps[app_name].units.items():
        if unit.leader:
            return unit.address
    raise ValueError(f"no leader found for app {app_name}")


def get_unit_address(juju: jubilant.Juju, app_name: str, unit_no: int) -> str:
    """Get the address of a specific unit."""
    status = juju.status()
    unit = status.apps[app_name].units.get(f"{app_name}/{unit_no}")
    if unit is None:
        raise ValueError(f"no unit exists in app {app_name} with index {unit_no}")
    return unit.address


@retry(wait=wait_fixed(5), stop=stop_after_attempt(12))
def _wait_for_minio_ready(minio_addr: str):
    """Poll MinIO's readiness endpoint until the S3 API is actually serving."""
    response = requests.get(f"http://{minio_addr}:9000/minio/health/ready", timeout=5)
    assert response.status_code == 200, (
        f"MinIO readiness check returned HTTP {response.status_code}"
    )


def configure_minio(juju: jubilant.Juju):
    bucket_name = "mimir"
    minio_addr = get_leader_address(juju, "minio")
    _wait_for_minio_ready(minio_addr)
    mc_client = Minio(
        f"{minio_addr}:9000",
        access_key="access",
        secret_key="secretsecret",
        secure=False,
    )
    if not mc_client.bucket_exists(bucket_name):
        mc_client.make_bucket(bucket_name)


def configure_s3_integrator(juju: jubilant.Juju):
    model_name = juju.status().model.name
    juju.config("s3", {
        "endpoint": f"minio-0.minio-endpoints.{model_name}.svc.cluster.local:9000",
        "bucket": "mimir",
    })
    juju.run("s3/leader", "sync-s3-credentials", {
        "access-key": "access",
        "secret-key": "secretsecret",
    })


def get_grafana_datasources_from_client_localhost(
    juju: jubilant.Juju,
    grafana_app: str = "grafana",
) -> list[Any]:
    """Get Grafana datasources from the test host machine (outside the cluster)."""
    task = juju.run(f"{grafana_app}/leader", "get-admin-password")
    admin_password = task.results["admin-password"]
    grafana_url = get_leader_address(juju, grafana_app)
    url = f"http://admin:{admin_password}@{grafana_url}:3000/api/datasources"
    response = requests.get(url)
    assert response.status_code == 200
    return response.json()


def get_mimir_rules_from_grafana(
    juju: jubilant.Juju,
    grafana_app: str = "grafana",
) -> dict[str, Any]:
    """Query Mimir alert rules through Grafana's Prometheus-compatible API.

    This exercises the nginx routing in the Mimir coordinator for the
    /prometheus/api/v1/rules endpoint, which Grafana uses to fetch alert rules.
    """
    task = juju.run(f"{grafana_app}/leader", "get-admin-password")
    admin_password = task.results["admin-password"]
    grafana_url = get_leader_address(juju, grafana_app)
    base_url = f"http://admin:{admin_password}@{grafana_url}:3000"

    # Find the Mimir datasource UID (type "prometheus", name contains "mimir")
    response = requests.get(f"{base_url}/api/datasources")
    assert response.status_code == 200
    datasources = response.json()

    mimir_uid = None
    for ds in datasources:
        if "mimir" in ds.get("name", "").lower() and ds.get("type") == "prometheus":
            mimir_uid = ds.get("uid")
            break
    assert mimir_uid is not None, "Mimir datasource not found in Grafana"

    # Query alert rules through Grafana's Prometheus-compatible proxy endpoint
    response = requests.get(f"{base_url}/api/prometheus/{mimir_uid}/api/v1/rules")
    assert response.status_code == 200
    response_json = response.json()

    # Grafana returns 200 with empty groups when there are no rules, so check groups are non-empty
    assert response_json.get("data", {}).get("groups", []), "No alert rule groups found in Mimir"
    return response_json


def get_grafana_datasources_from_client_pod(
    juju: jubilant.Juju,
    source_pod: str,
    grafana_app: str = "grafana",
) -> list[Any]:
    """Get Grafana datasources from inside a pod (within the cluster)."""
    task = juju.run(f"{grafana_app}/leader", "get-admin-password")
    admin_password = task.results["admin-password"]
    grafana_url = get_leader_address(juju, grafana_app)
    url = f"http://admin:{admin_password}@{grafana_url}:3000/api/datasources"
    task = juju.exec(f"curl -s {url}", unit=source_pod)
    return json.loads(task.stdout)


def get_prometheus_targets_from_client_localhost(
    juju: jubilant.Juju,
    prometheus_app: str = "prometheus",
) -> dict[str, Any]:
    """Get Prometheus scrape targets from the test host machine (outside the cluster)."""
    prometheus_url = get_leader_address(juju, prometheus_app)
    url = f"http://{prometheus_url}:9090/api/v1/targets"
    response = requests.get(url)
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["status"] == "success"
    return response_json["data"]


def get_prometheus_targets_from_client_pod(
    juju: jubilant.Juju,
    source_pod: str,
    prometheus_app: str = "prometheus",
) -> dict[str, Any]:
    """Get Prometheus scrape targets from inside a pod (within the cluster)."""
    prometheus_url = get_leader_address(juju, prometheus_app)
    url = f"http://{prometheus_url}:9090/api/v1/targets"
    task = juju.exec(f"curl -s {url}", unit=source_pod)
    response_json = json.loads(task.stdout)
    assert response_json["status"] == "success"
    return response_json["data"]


def query_mimir_from_client_localhost(
    juju: jubilant.Juju,
    query: str,
    coordinator_app: str = "mimir",
) -> dict[str, Any]:
    """Query Mimir API from the test host machine (outside the cluster)."""
    mimir_url = get_leader_address(juju, coordinator_app)
    response = requests.get(
        f"http://{mimir_url}:8080/prometheus/api/v1/query",
        params={"query": query},
    )
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["status"] == "success"
    return response_json["data"]["result"]


def query_mimir_from_client_pod(
    juju: jubilant.Juju,
    source_pod: str,
    query: str,
    coordinator_app: str = "mimir",
) -> dict[str, Any]:
    """Query Mimir API from inside a pod (within the cluster)."""
    model_name = juju.status().model.name
    mimir_url = f"{coordinator_app}.{model_name}.svc.cluster.local"
    url = f"http://{mimir_url}:8080/prometheus/api/v1/query"
    encoded_query = quote(query, safe="")
    task = juju.exec(f"curl -s '{url}?query={encoded_query}'", unit=source_pod)
    response_json = json.loads(task.stdout)
    assert response_json["status"] == "success"
    return response_json["data"]["result"]


def get_traefik_proxied_endpoints(
    juju: jubilant.Juju, traefik_app: str = "traefik"
) -> dict[str, Any]:
    task = juju.run(f"{traefik_app}/leader", "show-proxied-endpoints")
    return json.loads(task.results["proxied-endpoints"])


def push_to_otelcol(juju: jubilant.Juju, metric_name: str) -> str:
    """Push a metric along with a trace ID to an OpenTelemetry Collector.

    This creates an exemplar by attaching a trace ID provided by the
    OpenTelemetry SDK to a metric.  The meter provider is shut down before
    returning to force a synchronous flush of all pending metric data.

    Each call creates a fresh, local MeterProvider (no global state) so the
    function can safely be called multiple times in a retry loop.
    """
    otel_url = get_leader_address(juju, "otelcol")
    collector_endpoint = f"http://{otel_url}:4318/v1/metrics"

    resource = Resource(attributes={
        SERVICE_NAME: "service",
        SERVICE_VERSION: "1.0.0",
    })

    otlp_exporter = OTLPMetricExporter(endpoint=collector_endpoint)
    metric_reader = PeriodicExportingMetricReader(otlp_exporter, export_interval_millis=5000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    meter = meter_provider.get_meter("meter", "1.0.0")
    counter = meter.create_counter(metric_name, description="A placeholder counter metric")
    tracer_provider = TracerProvider()

    with tracer_provider.get_tracer("service").start_as_current_span("generate_metrics_span") as span:
        span_ctx = span.get_span_context()
        trace_id = span_ctx.trace_id
        trace_id_hex = format_trace_id(trace_id)
        counter.add(100, {"trace_id": trace_id_hex})

    meter_provider.shutdown()
    return trace_id_hex


@retry(wait=wait_fixed(20), stop=stop_after_attempt(5))
def _query_exemplars(
    juju: jubilant.Juju, query_name: str, coordinator_app: str
) -> str:
    """Query Mimir for exemplar data and return the trace_id."""
    mimir_url = get_leader_address(juju, coordinator_app)
    response = requests.get(
        f"http://{mimir_url}:8080/prometheus/api/v1/query_exemplars",
        params={"query": query_name},
    )
    assert response.status_code == 200, (
        f"query_exemplars got HTTP {response.status_code}: {response.text[:200]}"
    )

    response_data = response.json()
    assert response_data.get("data", []), "No exemplar data found in Mimir's API."

    exemplars = response_data["data"][0].get("exemplars", [])
    assert exemplars, "No exemplars found in data returned from Mimir"
    assert exemplars[0].get("labels", {})
    assert exemplars[0]["labels"].get("trace_id"), "No trace_id found in data returned from Mimir"
    return exemplars[0]["labels"]["trace_id"]


@retry(wait=wait_fixed(30), stop=stop_after_attempt(5))
def push_and_verify_exemplars(juju: jubilant.Juju, coordinator_app: str) -> None:
    """Push exemplar data to otelcol and verify it reaches Mimir.

    Retries the full push-then-query cycle to handle transient pipeline issues
    (e.g. otelcol still reconfiguring remote-write exporters after a relation
    URL change).  Each attempt uses a unique metric name so stale data from a
    prior failed push cannot satisfy the query.
    """
    metric_name = f"sample_metric_{uuid.uuid4().hex[:8]}"
    logger.info("push_and_verify_exemplars: pushing %s to otelcol", metric_name)
    trace_id = push_to_otelcol(juju, metric_name=metric_name)
    found = _query_exemplars(juju, query_name=metric_name, coordinator_app=coordinator_app)
    assert found == trace_id, f"Trace ID mismatch: expected {trace_id}, got {found}"


def get_istio_ingress_ip(juju: jubilant.Juju, app_name: str = "istio-ingress") -> str:
    """Get the istio-ingress public IP address from Kubernetes."""
    gateway_resource = create_namespaced_resource(
        group="gateway.networking.k8s.io",
        version="v1",
        kind="Gateway",
        plural="gateways",
    )
    model_name = juju.status().model.name
    client = Client()
    gateway = client.get(gateway_resource, app_name, namespace=model_name)  # type: ignore
    if gateway.status and gateway.status.get("addresses"):  # type: ignore
        return gateway.status["addresses"][0]["value"]  # type: ignore
    raise ValueError(f"No ingress address found for {app_name}")


def service_mesh(
    enable: bool,
    juju: jubilant.Juju,
    beacon_app_name: str,
    apps_to_be_related_with_beacon: list[str],
):
    """Enable or disable the service-mesh in the model."""
    juju.config(beacon_app_name, {"model-on-mesh": str(enable).lower()})
    juju.wait(jubilant.all_active, timeout=1000)
    if enable:
        for app in apps_to_be_related_with_beacon:
            juju.integrate(f"{beacon_app_name}:service-mesh", f"{app}:service-mesh")
    else:
        for app in apps_to_be_related_with_beacon:
            juju.remove_relation(
                f"{beacon_app_name}:service-mesh", f"{app}:service-mesh"
            )
    juju.wait(jubilant.all_active, timeout=1000, successes=10, delay=3)


def get_traces(tempo_host: str, service_name="tracegen-otlp_http", tls=True):
    """Get traces directly from Tempo REST API."""
    url = f"{'https' if tls else 'http'}://{tempo_host}:3200/api/search?tags=service.name={service_name}"
    req = requests.get(
        url,
        verify=False,
    )
    assert req.status_code == 200
    traces = json.loads(req.text)["traces"]
    return traces


@retry(stop=stop_after_attempt(15), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_traces_patiently(tempo_host, service_name="tracegen-otlp_http", tls=True):
    """Get traces directly from Tempo REST API, but also try multiple times.

    Useful for cases when Tempo might not return the traces immediately (its API is known
    for returning data in random order).
    """
    traces = get_traces(tempo_host, service_name=service_name, tls=tls)
    assert len(traces) > 0
    return traces

def deploy_tempo_cluster(juju: Juju, cos_channel: str):
    """Deploy Tempo in its HA version together with Minio and s3-integrator."""
    tempo_app = "tempo"
    worker_app = "tempo-worker"
    s3_app = "s3-tempo"

    juju.deploy("tempo-worker-k8s", app=worker_app, channel=cos_channel, trust=True)
    juju.deploy("tempo-coordinator-k8s", app=tempo_app, channel=cos_channel, trust=True)
    juju.deploy("s3-integrator", app=s3_app, channel="edge")

    juju.integrate(f"{tempo_app}:s3", f"{s3_app}:s3-credentials")
    juju.integrate(f"{tempo_app}:tempo-cluster", f"{worker_app}:tempo-cluster")

    configure_minio(juju, bucket_name="tempo")
    juju.wait(lambda status: jubilant.all_blocked(status, s3_app), timeout=1000)
    configure_s3_integrator(juju, bucket_name="tempo", s3_app=s3_app)

    juju.wait(
        lambda status: jubilant.all_active(status, tempo_app, worker_app, s3_app),
        timeout=2000,
        delay=5,
        successes=3,
    )
