import json
import logging
from typing import Any, Dict, List

import requests
import yaml
from juju.application import Application
from juju.unit import Unit
from minio import Minio
from pytest_operator.plugin import OpsTest
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


def charm_resources(metadata_file="charmcraft.yaml") -> Dict[str, str]:
    with open(metadata_file, "r") as file:
        metadata = yaml.safe_load(file)
    resources = {}
    for res, data in metadata["resources"].items():
        resources[res] = data["upstream-source"]
    return resources


async def configure_minio(ops_test: OpsTest, bucket_name="mimir"):
    minio_leader_unit_number = await get_leader_unit_number(ops_test, "minio")
    minio_addr = await get_unit_address(ops_test, "minio", minio_leader_unit_number)
    mc_client = Minio(
        f"{minio_addr}:9000",
        access_key="access",
        secret_key="secretsecret",
        secure=False,
    )
    # create bucket
    found = mc_client.bucket_exists(bucket_name)
    if not found:
        mc_client.make_bucket(bucket_name)


async def configure_s3_integrator(ops_test: OpsTest, bucket_name="mimir", s3_app="s3"):
    assert ops_test.model is not None
    config = {
        "access-key": "access",
        "secret-key": "secretsecret",
    }
    s3_integrator_app: Application = ops_test.model.applications[s3_app]  # type: ignore
    s3_integrator_leader: Unit = s3_integrator_app.units[0]

    await s3_integrator_app.set_config(
        {
            "endpoint": f"minio-0.minio-endpoints.{ops_test.model.name}.svc.cluster.local:9000",
            "bucket": bucket_name,
        }
    )
    action = await s3_integrator_leader.run_action("sync-s3-credentials", **config)
    action_result = await action.wait()
    assert action_result.status == "completed"


async def get_leader_unit_number(ops_test: OpsTest, app_name: str) -> int:
    """Get the unit number of the leader of an application.

    Raises an exception if no leader is found.
    """
    assert ops_test.model
    status = await ops_test.model.get_status()
    app = status["applications"][app_name]
    if app is None:
        raise ValueError(f"no app exists with name {app_name}")

    for name, unit in app["units"].items():
        if unit["leader"]:
            return int(name.split("/")[1])

    raise ValueError(f"no leader found for app {app_name}")


async def get_unit_address(ops_test: OpsTest, app_name: str, unit_no: int) -> str:
    assert ops_test.model is not None
    status = await ops_test.model.get_status()
    app = status["applications"][app_name]
    if app is None:
        assert False, f"no app exists with name {app_name}"
    unit = app["units"].get(f"{app_name}/{unit_no}")
    if unit is None:
        assert False, f"no unit exists in app {app_name} with index {unit_no}"
    return unit["address"]


async def get_grafana_datasources(ops_test: OpsTest, grafana_app: str = "grafana") -> List[Any]:
    """Get the Datasources from Grafana using the HTTP API.

    HTTP API Response format: [{"id": 1, "name": <some-name>, ...}, ...]
    """
    assert ops_test.model is not None
    grafana_leader: Unit = ops_test.model.applications[grafana_app].units[0]  # type: ignore
    action = await grafana_leader.run_action("get-admin-password")
    action_result = await action.wait()
    admin_password = action_result.results["admin-password"]
    leader_unit_number = await get_leader_unit_number(ops_test, grafana_app)
    grafana_url = await get_unit_address(ops_test, grafana_app, leader_unit_number)
    response = requests.get(f"http://admin:{admin_password}@{grafana_url}:3000/api/datasources")
    assert response.status_code == 200

    return response.json()


async def get_prometheus_targets(
    ops_test: OpsTest, prometheus_app: str = "prometheus"
) -> Dict[str, Any]:
    """Get the Scrape Targets from Prometheus using the HTTP API.

    HTTP API Response format:
        {"status": "success", "data": {"activeTargets": [{"discoveredLabels": {..., "juju_charm": <charm>, ...}}]}}
    """
    assert ops_test.model is not None
    leader_unit_number = await get_leader_unit_number(ops_test, prometheus_app)
    prometheus_url = await get_unit_address(ops_test, prometheus_app, leader_unit_number)
    response = requests.get(f"http://{prometheus_url}:9090/api/v1/targets")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    return response.json()["data"]


async def query_mimir(
    ops_test: OpsTest, query: str, coordinator_app: str = "mimir"
) -> Dict[str, Any]:
    leader_unit_number = await get_leader_unit_number(ops_test, coordinator_app)
    mimir_url = await get_unit_address(ops_test, coordinator_app, leader_unit_number)
    response = requests.get(
        f"http://{mimir_url}:8080/prometheus/api/v1/query",
        params={"query": query},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"  # the query was successful
    return response.json()["data"]["result"]


async def get_traefik_proxied_endpoints(
    ops_test: OpsTest, traefik_app: str = "traefik"
) -> Dict[str, Any]:
    assert ops_test.model is not None
    traefik_leader: Unit = ops_test.model.applications[traefik_app].units[0]  # type: ignore
    action = await traefik_leader.run_action("show-proxied-endpoints")
    action_result = await action.wait()
    return json.loads(action_result.results["proxied-endpoints"])


async def deploy_tempo_cluster(ops_test: OpsTest):
    """Deploys tempo in its HA version together with minio and s3-integrator."""
    assert ops_test.model
    tempo_app = "tempo"
    worker_app = "tempo-worker"
    s3_app = "s3-tempo"
    tempo_worker_charm_url, worker_channel = "tempo-worker-k8s", "2/edge"
    tempo_coordinator_charm_url, coordinator_channel = "tempo-coordinator-k8s", "2/edge"
    await ops_test.model.deploy(
        tempo_worker_charm_url, application_name=worker_app, channel=worker_channel, trust=True
    )
    await ops_test.model.deploy(
        tempo_coordinator_charm_url,
        application_name=tempo_app,
        channel=coordinator_channel,
        trust=True,
    )

    await ops_test.model.deploy("s3-integrator", channel="edge", application_name=s3_app)

    await ops_test.model.integrate(f"{tempo_app}:s3", f"{s3_app}:s3-credentials")
    await ops_test.model.integrate(f"{tempo_app}:tempo-cluster", f"{worker_app}:tempo-cluster")

    await configure_minio(ops_test, bucket_name="tempo")
    await ops_test.model.wait_for_idle(apps=[s3_app], status="blocked")
    await configure_s3_integrator(ops_test, bucket_name="tempo", s3_app=s3_app)

    async with ops_test.fast_forward():
        await ops_test.model.wait_for_idle(
            apps=[tempo_app, worker_app, s3_app],
            status="active",
            timeout=2000,
            idle_period=30,
        )


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
async def get_traces_patiently(tempo_host, service_name="tracegen-otlp_http", tls=True):
    """Get traces directly from Tempo REST API, but also try multiple times.

    Useful for cases when Tempo might not return the traces immediately (its API is known for returning data in
    random order).
    """
    traces = get_traces(tempo_host, service_name=service_name, tls=tls)
    assert len(traces) > 0
    return traces


async def get_application_ip(ops_test: OpsTest, app_name: str) -> str:
    """Get the application IP address."""
    assert ops_test.model
    status = await ops_test.model.get_status()
    app = status["applications"][app_name]
    return app.public_address
