from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aviary.cli import build_engine
from aviary.contracts import BirdOpinion
from aviary.engine import AviaryEngine
from aviary.runtime.sandbox import BirdExecutionError, BirdExecutionResult


class RecordingSandbox:
    def __init__(self):
        self.calls: list[str] = []

    def analyze(self, loaded, topic):
        self.calls.append(loaded.bird_id)
        opinion = loaded.instance.analyze(topic)
        return BirdExecutionResult(opinion=opinion, runtime_ms=1.0)


class FailingSandbox:
    def analyze(self, loaded, topic):
        raise BirdExecutionError(loaded.bird_id, "timed out", "exceeded 0.010s")


class EngineIsolationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base_engine, self.ledger = build_engine(Path(self.tmp.name) / "aviary.db")

    def tearDown(self):
        self.ledger.close()
        self.tmp.cleanup()

    def test_engine_routes_every_bird_through_sandbox(self):
        sandbox = RecordingSandbox()
        engine = AviaryEngine(self.base_engine.registry, self.ledger, sandbox=sandbox)
        report = engine.run("route through boundary")
        self.assertEqual(sandbox.calls, list(self.base_engine.registry.ids()))
        self.assertEqual(len(report.opinions), 6)

    def test_failure_marks_session_failed_and_records_receipt(self):
        engine = AviaryEngine(self.base_engine.registry, self.ledger, sandbox=FailingSandbox())
        with self.assertRaises(BirdExecutionError):
            engine.run("force timeout")
        session = self.ledger.connection.execute(
            "SELECT id,status,final_json FROM sessions ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(session["status"], "failed")
        self.assertIsNone(session["final_json"])
        receipt = self.ledger.connection.execute(
            "SELECT kind,content_json,sha256 FROM receipts WHERE session_id=?",
            (session["id"],),
        ).fetchone()
        self.assertEqual(receipt["kind"], "bird_failure")
        payload = json.loads(receipt["content_json"])
        self.assertEqual(payload["kind"], "timed out")
        self.assertEqual(payload["bird_id"], "duck")
        self.assertEqual(len(receipt["sha256"]), 64)

    def test_failed_session_is_visible_but_not_replayable(self):
        engine = AviaryEngine(self.base_engine.registry, self.ledger, sandbox=FailingSandbox())
        with self.assertRaises(BirdExecutionError):
            engine.run("failed history")
        row = self.ledger.recent_sessions(1)[0]
        self.assertEqual(row["status"], "failed")
        self.assertEqual(len(row["sha256"]), 64)
        with self.assertRaises(ValueError):
            self.ledger.replay_session(row["id"])


if __name__ == "__main__":
    unittest.main()
