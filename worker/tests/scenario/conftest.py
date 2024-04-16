import pytest
from charm import MimirWorkerK8SOperatorCharm
from scenario import Context, ExecOutput


@pytest.fixture(autouse=True)
def patch_all():
    # with patch("charm.MimirWorkerK8SOperatorCharm._current_mimir_config", PropertyMock(return_value={})):
    # with patch("charm.MimirWorkerK8SOperatorCharm._set_alerts", Mock(return_value=True)):
    yield


@pytest.fixture
def ctx():
    return Context(MimirWorkerK8SOperatorCharm)


MIMIR_VERSION_EXEC_OUTPUT = ExecOutput(stdout="1.31")
