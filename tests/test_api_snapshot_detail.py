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


class SnapshotDetailRouteTests(unittest.TestCase):
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

    def test_returns_one_verified_snapshot(self) -> None:
        status, body = self._get_json(
            f"/api/simulations/{self.run_id}/snapshots/1"
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["run_id"], self.run_id)
        self.assertEqual(body["tick"], 1)
        self.assertEqual(body["state"]["owl-1"]["energy"], 5)
        self.assertTrue(body["receipt_valid"])
        self.assertTrue(body["valid"])
        self.assertEqual(len(body["state_sha256"]), 64)
        self.assertNotIn("snapshots", body)
        self.assertNotIn("final_state", body)

    def test_reports_tampered_snapshot_without_hiding_state(self) -> None:
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
        status, body = self._get_json(
            f"/api/simulations/{self.run_id}/snapshots/0"
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["state"]["owl-1"]["energy"], 99)
        self.assertFalse(body["valid"])

    def test_missing_snapshot_is_distinct_from_missing_run(self) -> None:
        status, body = self._read_error(
            f"/api/simulations/{self.run_id}/snapshots/999"
        )
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "snapshot_not_found")

        status, body = self._read_error("/api/simulations/999/snapshots/0")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "simulation_not_found")

    def test_rejects_invalid_ticks_and_query_parameters(self) -> None:
        paths = (
            f"/api/simulations/{self.run_id}/snapshots/-1",
            f"/api/simulations/{self.run_id}/snapshots/nope",
            f"/api/simulations/{self.run_id}/snapshots/9223372036854775808",
            f"/api/simulations/{self.run_id}/snapshots/0?extra=1",
            f"/api/simulations/{self.run_id}/snapshots",
            f"/api/simulations/{self.run_id}/snapshots/0/extra",
        )
        for path in paths:
            with self.subTest(path=path):
                status, body = self._read_error(path)
                self.assertEqual(status, 400)
                self.assertEqual(body["error"], "invalid_request")

    def test_capabilities_advertise_snapshot_route(self) -> None:
        status, body = self._get_json("/api/capabilities")
        self.assertEqual(status, 200)
        routes = {
            (item["method"], item["path"])
            for item in body["capabilities"]
        }
        self.assertIn(
            ("GET", "/api/simulations/{run_id}/snapshots/{tick}"), routes
        )


if __name__ == "__main__":
    unittest.main()
