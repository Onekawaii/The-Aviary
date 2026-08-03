from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from aviary.api import AviaryBridge, create_server
from aviary.api.__main__ import build_parser
from aviary.ledger import SQLiteLedger
from aviary.simulation import DeterministicSimulation, EntityBlueprint, SimulationEvent
from aviary.simulation.persistence import SimulationReceiptStore


class BridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "aviary.db"
        self.server = create_server(port=0, ledger_path=self.db_path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        self.base = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tempdir.cleanup()

    def get_json(self, path: str) -> tuple[int, dict[str, object], dict[str, str]]:
        with urlopen(self.base + path, timeout=2) as response:
            body = json.loads(response.read().decode("utf-8"))
            return response.status, body, dict(response.headers.items())

    def read_error(self, path: str) -> tuple[int, dict[str, object]]:
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.base + path, timeout=2)
        return caught.exception.code, json.loads(caught.exception.read().decode("utf-8"))

    def record_simulation(self) -> int:
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

    def tamper_snapshot(self, run_id: int) -> None:
        ledger = SQLiteLedger(self.db_path)
        try:
            with ledger.connection:
                ledger.connection.execute(
                    "UPDATE simulation_snapshots SET state_json=? WHERE run_id=? AND tick=0",
                    ('{"owl-1":{"energy":99}}', run_id),
                )
        finally:
            ledger.close()

    def test_health_reports_ready_service(self) -> None:
        status, body, headers = self.get_json("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["service"], "the-aviary")
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["bird_count"], 6)
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_birds_exposes_registry_contracts(self) -> None:
        status, body, _ = self.get_json("/api/birds")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 6)
        birds = body["birds"]
        ids = [bird["bird_id"] for bird in birds]
        self.assertIn("duck", ids)
        self.assertIn("brother_ape", ids)
        self.assertTrue(all(bird["schema"]["type"] == "object" for bird in birds))

    def test_server_initializes_ledger_before_accepting_requests(self) -> None:
        self.assertTrue(self.db_path.exists())
        status, body, _ = self.get_json("/api/simulations")
        self.assertEqual(status, 200)
        self.assertEqual(body["runs"], [])

    def test_simulations_lists_empty_ledger_with_pagination(self) -> None:
        status, body, _ = self.get_json("/api/simulations?limit=5&offset=0")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"runs": [], "count": 0, "limit": 5, "offset": 0})

    def test_simulation_detail_returns_verified_receipt(self) -> None:
        run_id = self.record_simulation()
        status, body, _ = self.get_json(f"/api/simulations/{run_id}")
        self.assertEqual(status, 200)
        self.assertEqual(body["run_id"], run_id)
        self.assertTrue(body["receipt_valid"])
        self.assertTrue(body["valid"])
        self.assertTrue(all(body["snapshot_integrity"]))
        self.assertEqual(body["final_state"]["owl-1"]["energy"], 5)
        self.assertEqual(len(body["snapshots"]), 2)

    def test_simulation_verification_returns_only_integrity_evidence(self) -> None:
        run_id = self.record_simulation()
        status, body, _ = self.get_json(f"/api/simulations/{run_id}/verify")
        self.assertEqual(status, 200)
        self.assertEqual(body["run_id"], run_id)
        self.assertEqual(body["snapshot_count"], 2)
        self.assertTrue(body["receipt_valid"])
        self.assertTrue(body["valid"])
        self.assertTrue(all(body["snapshot_integrity"]))
        self.assertNotIn("final_state", body)
        self.assertNotIn("snapshots", body)

    def test_simulation_detail_reports_tampered_snapshot(self) -> None:
        run_id = self.record_simulation()
        self.tamper_snapshot(run_id)
        status, body, _ = self.get_json(f"/api/simulations/{run_id}")
        self.assertEqual(status, 200)
        self.assertFalse(body["valid"])
        self.assertFalse(body["snapshots"][0]["valid"])

    def test_simulation_verification_reports_tampering_without_state(self) -> None:
        run_id = self.record_simulation()
        self.tamper_snapshot(run_id)
        status, body, _ = self.get_json(f"/api/simulations/{run_id}/verify")
        self.assertEqual(status, 200)
        self.assertFalse(body["valid"])
        self.assertFalse(body["snapshot_integrity"][0])
        self.assertNotIn("final_state", body)

    def test_simulation_paths_reject_bad_or_missing_ids(self) -> None:
        paths = (
            "/api/simulations/0",
            "/api/simulations/nope",
            "/api/simulations/1?extra=1",
            "/api/simulations/0/verify",
            "/api/simulations/nope/verify",
            "/api/simulations/1/verify?extra=1",
            "/api/simulations/1/extra",
        )
        for path in paths:
            with self.subTest(path=path):
                status, body = self.read_error(path)
                self.assertEqual(status, 400)
                self.assertEqual(body["error"], "invalid_request")
        for path in ("/api/simulations/999", "/api/simulations/999/verify"):
            with self.subTest(path=path):
                status, body = self.read_error(path)
                self.assertEqual(status, 404)
                self.assertEqual(body["error"], "simulation_not_found")

    def test_simulations_rejects_invalid_query(self) -> None:
        queries = (
            "limit=0",
            "offset=-1",
            "limit=9223372036854775808",
            "offset=9223372036854775808",
            "wat=1",
        )
        for query in queries:
            with self.subTest(query=query):
                status, body = self.read_error(f"/api/simulations?{query}")
                self.assertEqual(status, 400)
                self.assertEqual(body["error"], "invalid_request")

    def test_unknown_path_is_structured_404(self) -> None:
        status, body = self.read_error("/api/missing")
        self.assertEqual(status, 404)
        self.assertEqual(body, {"error": "not_found", "path": "/api/missing"})

    def test_post_is_rejected_without_execution(self) -> None:
        request = Request(self.base + "/api/birds", data=b"{}", method="POST")
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=2)
        self.assertEqual(caught.exception.code, 405)

    def test_invalid_bind_arguments_fail_before_server_creation(self) -> None:
        with self.assertRaisesRegex(ValueError, "host"):
            create_server(host="", port=0)
        with self.assertRaisesRegex(ValueError, "port"):
            create_server(port=70000)

    def test_bridge_cli_honors_shared_ledger_environment_default(self) -> None:
        configured = str(Path(self.tempdir.name) / "configured.db")
        with patch.dict(os.environ, {"AVIARY_DB": configured}):
            args = build_parser().parse_args([])
        self.assertEqual(Path(args.db), Path(configured))

    def test_bridge_can_be_constructed_independently(self) -> None:
        bridge = AviaryBridge(ledger_path=self.db_path)
        self.assertEqual(bridge.health()["bird_count"], 6)
        self.assertEqual(
            bridge.simulations(),
            {"runs": [], "count": 0, "limit": 20, "offset": 0},
        )


if __name__ == "__main__":
    unittest.main()
