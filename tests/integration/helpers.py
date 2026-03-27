import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import jubilant
import requests
import yaml
from lightkube import Client
from lightkube.generic_resource import create_namespaced_resource
from minio import Minio
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import format_trace_id
from tenacity import retry, stop_after_attempt, wait_fixed

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


def configure_minio(juju: jubilant.Juju):
    bucket_name = "mimir"
    minio_addr = get_leader_address(juju, "minio")
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
    OpenTelemetry SDK to a metric.
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
    metrics.set_meter_provider(meter_provider)
    meter = metrics.get_meter("meter", "1.0.0")
    counter = meter.create_counter(metric_name, description="A placeholder counter metric")
    tracer_provider = TracerProvider()

    with tracer_provider.get_tracer("service").start_as_current_span("generate_metrics_span") as span:
        span_ctx = span.get_span_context()
        trace_id = span_ctx.trace_id
        trace_id_hex = format_trace_id(trace_id)
        counter.add(100, {"trace_id": trace_id_hex})

    return trace_id_hex


@retry(wait=wait_fixed(20), stop=stop_after_attempt(6))
def query_exemplars(
    juju: jubilant.Juju, query_name: str, coordinator_app: str
) -> str | None:
    mimir_url = get_leader_address(juju, coordinator_app)
    response = requests.get(
        f"http://{mimir_url}:8080/prometheus/api/v1/query_exemplars",
        params={"query": f"{query_name}_total"},
    )
    assert response.status_code == 200

    response_data = response.json()
    assert response_data.get("data", []), "No exemplar data found in Mimir's API."

    exemplars = response_data["data"][0].get("exemplars", [])
    assert exemplars, "No exemplars found in data returned from Mimir"
    assert exemplars[0].get("labels", {})
    assert exemplars[0]["labels"].get("trace_id"), "No trace_id found in data returned from Mimir"
    return exemplars[0]["labels"]["trace_id"]


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
