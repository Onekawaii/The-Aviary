from __future__ import annotations

import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from aviary.api import AviaryBridge, create_server


class BridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = create_server(port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        self.base = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def get_json(self, path: str) -> tuple[int, dict[str, object], dict[str, str]]:
        with urlopen(self.base + path, timeout=2) as response:
            body = json.loads(response.read().decode("utf-8"))
            return response.status, body, dict(response.headers.items())

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

    def test_unknown_path_is_structured_404(self) -> None:
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.base + "/api/missing", timeout=2)
        self.assertEqual(caught.exception.code, 404)
        body = json.loads(caught.exception.read().decode("utf-8"))
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
        bridge = AviaryBridge()
        self.assertEqual(bridge.health()["bird_count"], 6)


if __name__ == "__main__":
    unittest.main()
