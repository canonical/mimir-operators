#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import unittest
from unittest.mock import patch
from uuid import uuid4

import ops
from charm import MimirWorkerK8SOperatorCharm
from ops.testing import Harness

ops.testing.SIMULATE_CAN_CONNECT = True


@patch("charm.MimirWorkerK8SOperatorCharm._mimir_version", property(lambda *_: "1.2.3"))
@patch("charm.MimirWorkerK8SOperatorCharm.restart", lambda *_: True)
class TestCharm(unittest.TestCase):
    def setUp(self, *unused):
        self.harness = Harness(MimirWorkerK8SOperatorCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.handle_exec("mimir", ["update-ca-certificates", "--fresh"], result=0)
        self.harness.set_leader(True)

    @patch("charm.KubernetesServicePatch", lambda *_, **__: None)
    def test_initial_hooks(self, *_):
        self.harness.set_model_info("foo", str(uuid4()))
        self.harness.begin_with_initial_hooks()
