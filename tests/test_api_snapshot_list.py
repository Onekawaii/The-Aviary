from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from aviary.api import create_server
from aviary.ledger import SQLiteLedger
from aviary.simulation import DeterministicSimulation, EntityBlueprint, SimulationEvent
from aviary.simulation.persistence import SimulationReceiptStore


class SnapshotListRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "aviary.db"
        self.server = create_server(port=0, ledger_path=self.db_path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        self.base = f"http://{host}:{port}"
        self.run_id = self._record_simulation()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tempdir.cleanup()

    def _record_simulation(self) -> int:
        result = DeterministicSimulation().replay(
            (EntityBlueprint("owl-1", "bird", {"energy": 3}),),
            (
                SimulationEvent(
                    "rise",
                    1,
                    "increment_property",
                    "owl-1",
                    {"key": "energy", "amount": 2},
                ),
            ),
        )
        ledger = SQLiteLedger(self.db_path)
        try:
            return SimulationReceiptStore(ledger).record(result)
        finally:
            ledger.close()

    def _get_json(self, path: str) -> tuple[int, dict[str, object]]:
        with urlopen(self.base + path, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def _read_error(self, path: str) -> tuple[int, dict[str, object]]:
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.base + path, timeout=2)
        return caught.exception.code, json.loads(caught.exception.read().decode("utf-8"))

    def test_lists_snapshot_metadata_without_state_payloads(self) -> None:
        status, body = self._get_json(f"/api/simulations/{self.run_id}/snapshots")
        self.assertEqual(status, 200)
        self.assertEqual(body["run_id"], self.run_id)
        self.assertEqual(body["count"], 2)
        self.assertTrue(body["receipt_valid"])
        self.assertEqual([item["tick"] for item in body["snapshots"]], [0, 1])
        for item in body["snapshots"]:
            self.assertEqual(len(item["state_sha256"]), 64)
            self.assertTrue(item["valid"])
            self.assertNotIn("state", item)
        self.assertNotIn("final_state", body)

    def test_reports_tampered_snapshot_integrity(self) -> None:
        ledger = SQLiteLedger(self.db_path)
        try:
            with ledger.connection:
                ledger.connection.execute(
                    "UPDATE simulation_snapshots SET state_json=? "
                    "WHERE run_id=? AND tick=0",
                    ('{"owl-1":{"energy":99}}', self.run_id),
                )
        finally:
            ledger.close()
        status, body = self._get_json(f"/api/simulations/{self.run_id}/snapshots")
        self.assertEqual(status, 200)
        self.assertFalse(body["snapshots"][0]["valid"])
        self.assertTrue(body["snapshots"][1]["valid"])

    def test_rejects_query_parameters_and_missing_runs(self) -> None:
        status, body = self._read_error(
            f"/api/simulations/{self.run_id}/snapshots?extra=1"
        )
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "invalid_request")

        status, body = self._read_error("/api/simulations/999/snapshots")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "simulation_not_found")

    def test_capabilities_advertise_snapshot_listing(self) -> None:
        status, body = self._get_json("/api/capabilities")
        self.assertEqual(status, 200)
        paths = {item["path"] for item in body["capabilities"]}
        self.assertIn("/api/simulations/{run_id}/snapshots", paths)


if __name__ == "__main__":
    unittest.main()
