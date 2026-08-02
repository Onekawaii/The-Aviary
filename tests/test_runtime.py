from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from aviary.contracts import Topic
from aviary.registry import BirdRegistry
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


if __name__ == "__main__":
    unittest.main()
