from __future__ import annotations

import io
import json
import subprocess
import unittest
from unittest.mock import patch

from aviary.contracts import BirdOpinion, Topic
from aviary.registry import BirdRegistry
from aviary.runtime import worker
from aviary.runtime.sandbox import BirdExecutionError, BirdSandbox, decode_opinion


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.registry = BirdRegistry()
        self.registry.discover()

    def test_builtin_bird_runs_in_subprocess(self):
        duck = next(b for b in self.registry.all() if b.bird_id == "duck")
        result = BirdSandbox(timeout_seconds=3.0).analyze(duck, Topic("Build roots"))
        self.assertEqual(result.opinion.bird_id, "duck")
        self.assertTrue(result.opinion.summary)

    def test_mismatched_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "expected 'duck'"):
            decode_opinion(
                {
                    "bird_id": "goose",
                    "summary": "wrong bird",
                    "observations": [],
                    "recommendations": [],
                    "risks": [],
                    "confidence": 0.5,
                    "data": {},
                },
                "duck",
            )

    def test_invalid_schema_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "summary"):
            decode_opinion(
                {
                    "bird_id": "duck",
                    "summary": "",
                    "observations": [],
                    "recommendations": [],
                },
                "duck",
            )

    def test_timeout_becomes_typed_failure(self):
        duck = next(b for b in self.registry.all() if b.bird_id == "duck")
        with patch(
            "aviary.runtime.sandbox.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["python"], 0.01),
        ):
            with self.assertRaisesRegex(BirdExecutionError, "timed out"):
                BirdSandbox(timeout_seconds=0.01).analyze(duck, Topic("slow"))

    def test_launch_oserror_becomes_typed_failure(self):
        duck = next(b for b in self.registry.all() if b.bird_id == "duck")
        with patch(
            "aviary.runtime.sandbox.subprocess.run",
            side_effect=OSError("process table full"),
        ):
            with self.assertRaisesRegex(BirdExecutionError, "could not launch worker"):
                BirdSandbox().analyze(duck, Topic("launch"))

    def test_worker_keeps_plugin_prints_out_of_protocol_stdout(self):
        class NoisyBird:
            def analyze(self, topic):
                print("diagnostic from plugin")
                return BirdOpinion(
                    bird_id="duck",
                    summary="valid",
                    observations=(),
                    recommendations=(),
                )

        request = json.dumps(
            {"module": "fake", "bird_id": "duck", "topic": {"text": "x"}}
        )
        protocol = io.StringIO()
        diagnostics = io.StringIO()
        with (
            patch.object(worker, "_load_bird", return_value=NoisyBird()),
            patch.object(worker.sys, "stdin", io.StringIO(request)),
            patch.object(worker.sys, "stdout", protocol),
            patch.object(worker.sys, "stderr", diagnostics),
        ):
            self.assertEqual(worker.main(), 0)
        response = json.loads(protocol.getvalue())
        self.assertTrue(response["ok"])
        self.assertNotIn("diagnostic", protocol.getvalue())
        self.assertIn("diagnostic from plugin", diagnostics.getvalue())


if __name__ == "__main__":
    unittest.main()
