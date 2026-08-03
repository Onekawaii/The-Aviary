from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aviary.api import AviaryBridge


class CapabilityManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "aviary.db"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_capabilities_are_machine_readable_and_read_only(self) -> None:
        body = AviaryBridge(ledger_path=self.db_path).capabilities()
        self.assertEqual(body["service"], "the-aviary")
        self.assertEqual(body["api_version"], "v1")
        self.assertTrue(body["read_only"])
        self.assertEqual(body["count"], len(body["capabilities"]))
        routes = {(item["method"], item["path"]) for item in body["capabilities"]}
        self.assertIn(("GET", "/api/health"), routes)
        self.assertIn(("GET", "/api/capabilities"), routes)
        self.assertIn(("GET", "/api/simulations/{run_id}/verify"), routes)
        self.assertFalse(any(method != "GET" for method, _ in routes))

    def test_capability_results_are_independent_copies(self) -> None:
        bridge = AviaryBridge(ledger_path=self.db_path)
        first = bridge.capabilities()
        first["capabilities"][0]["path"] = "/changed"
        second = bridge.capabilities()
        self.assertEqual(second["capabilities"][0]["path"], "/api/health")


if __name__ == "__main__":
    unittest.main()
