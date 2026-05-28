import pytest
import sh
from helpers import charm_resources, deploy_swfs
from jubilant import Juju, all_active, all_blocked


@pytest.mark.setup
def test_deploy_workers(juju: Juju, cos_channel):
    # GIVEN an empty model

    # WHEN deploying the workers with recommended scale
    for role in ("read", "write", "backend"):
        juju.deploy(
            "mimir-worker-k8s",
            role,
            channel=cos_channel,
            config={
                "role-all": False,
                f"role-{role}": True,
            },
            trust=True,
            num_units=3,
        )

    # THEN workers will be blocked because of missing coordinator integration
    juju.wait(
        lambda status: all_blocked(status, "read", "write", "backend"),
        timeout=1000,
    )


def test_all_active_when_coordinator_and_swfs_added(juju: Juju, mimir_charm):
    # GIVEN a model with workers

    # WHEN deploying and integrating the minimal mimir cluster
    deploy_swfs(juju)

    juju.deploy(
        mimir_charm,
        "mimir",
        resources=charm_resources(),
        trust=True,
    )
    juju.integrate("mimir:s3", "swfs")
    juju.integrate("mimir:mimir-cluster", "read")
    juju.integrate("mimir:mimir-cluster", "write")
    juju.integrate("mimir:mimir-cluster", "backend")

    # THEN both the coordinator and the workers become active
    juju.wait(
        lambda status: all_active(status, "mimir", "read", "write", "backend"),
        timeout=5000,
    )


def test_juju_doctor_probes(juju: Juju):
    # GIVEN the full model
    # THEN juju-doctor passes
    try:
        sh.uvx(
            "juju-doctor",
            "check",
            probe="file://../probes/cluster-consistency.yaml",
            model=juju.model,
        )
    except sh.ErrorReturnCode as e:
        pytest.fail(f"juju-doctor failed:\n{e.stderr.decode()}")
