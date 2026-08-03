from __future__ import annotations

import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from aviary.api import create_server


class CapabilityHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = Path(self.tempdir.name) / "aviary.db"
        self.server = create_server(port=0, ledger_path=db_path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address[:2]

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tempdir.cleanup()

    def request(self, path: str) -> tuple[int, dict[str, object]]:
        connection = http.client.HTTPConnection(self.host, self.port, timeout=2)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            return response.status, json.loads(response.read().decode("utf-8"))
        finally:
            connection.close()

    def test_capabilities_route_returns_manifest(self) -> None:
        status, body = self.request("/api/capabilities")
        self.assertEqual(status, 200)
        self.assertTrue(body["read_only"])
        self.assertEqual(body["count"], len(body["capabilities"]))

    def test_capabilities_route_rejects_query_parameters(self) -> None:
        status, body = self.request("/api/capabilities?extra=1")
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "invalid_request")


if __name__ == "__main__":
    unittest.main()
