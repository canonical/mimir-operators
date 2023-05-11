from unittest.mock import patch, Mock

import pytest
from scenario import ExecOutput, Context

from charm import MimirWorkerK8SOperatorCharm


@pytest.fixture(autouse=True)
def patch_all():
    # with patch("charm.MimirWorkerK8SOperatorCharm._current_mimir_config", PropertyMock(return_value={})):
    # with patch("charm.MimirWorkerK8SOperatorCharm._set_alerts", Mock(return_value=True)):
    with patch("charms.observability_libs.v1.kubernetes_service_patch.KubernetesServicePatch.__init__",
               Mock(return_value=None)):
        yield


@pytest.fixture
def ctx():
    return Context(MimirWorkerK8SOperatorCharm)


MIMIR_VERSION_EXEC_OUTPUT = ExecOutput(stdout="1.31")
