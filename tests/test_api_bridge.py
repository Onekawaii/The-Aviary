from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from aviary.api import AviaryBridge, create_server


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
        return (
            caught.exception.code,
            json.loads(caught.exception.read().decode("utf-8")),
        )

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

    def test_simulations_lists_empty_ledger_with_pagination(self) -> None:
        status, body, _ = self.get_json("/api/simulations?limit=5&offset=0")
        self.assertEqual(status, 200)
        self.assertEqual(
            body,
            {"runs": [], "count": 0, "limit": 5, "offset": 0},
        )
        self.assertTrue(self.db_path.exists())

    def test_simulations_rejects_invalid_query(self) -> None:
        status, body = self.read_error("/api/simulations?limit=0")
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "invalid_request")
        status, body = self.read_error("/api/simulations?wat=1")
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

    def test_bridge_can_be_constructed_independently(self) -> None:
        bridge = AviaryBridge(ledger_path=self.db_path)
        self.assertEqual(bridge.health()["bird_count"], 6)
        self.assertEqual(bridge.simulations(), {"runs": [], "count": 0, "limit": 20, "offset": 0})


if __name__ == "__main__":
    unittest.main()
