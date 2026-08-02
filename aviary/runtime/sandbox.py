from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Mapping

from aviary.contracts import BirdOpinion, Topic
from aviary.registry import LoadedBird


class BirdExecutionError(RuntimeError):
    def __init__(self, bird_id: str, kind: str, message: str):
        super().__init__(f"bird {bird_id} {kind}: {message}")
        self.bird_id = bird_id
        self.kind = kind
        self.message = message


@dataclass(frozen=True, slots=True)
class BirdExecutionResult:
    opinion: BirdOpinion
    runtime_ms: float


def _as_tuple(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a JSON array")
    if not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field} must contain only strings")
    return tuple(value)


def decode_opinion(payload: Mapping[str, Any], expected_bird_id: str) -> BirdOpinion:
    bird_id = payload.get("bird_id")
    if bird_id != expected_bird_id:
        raise ValueError(
            f"returned bird_id {bird_id!r}; expected {expected_bird_id!r}"
        )
    summary = payload.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("summary must be a non-empty string")
    data = payload.get("data", {})
    if not isinstance(data, dict):
        raise ValueError("data must be a JSON object")
    confidence = payload.get("confidence", 0.5)
    if not isinstance(confidence, (int, float)):
        raise ValueError("confidence must be numeric")
    return BirdOpinion(
        bird_id=bird_id,
        summary=summary,
        observations=_as_tuple(payload.get("observations", []), "observations"),
        recommendations=_as_tuple(
            payload.get("recommendations", []), "recommendations"
        ),
        risks=_as_tuple(payload.get("risks", []), "risks"),
        confidence=float(confidence),
        data=data,
    )


class BirdSandbox:
    def __init__(self, timeout_seconds: float = 2.0):
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds

    def analyze(self, loaded: LoadedBird, topic: Topic) -> BirdExecutionResult:
        request = {
            "module": loaded.module,
            "bird_id": loaded.bird_id,
            "topic": {"text": topic.text, "context": dict(topic.context)},
        }
        command = [sys.executable, "-m", "aviary.runtime.worker"]
        try:
            completed = subprocess.run(
                command,
                input=json.dumps(request),
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise BirdExecutionError(
                loaded.bird_id,
                "timed out",
                f"exceeded {self.timeout_seconds:.3f}s",
            ) from exc

        raw = completed.stdout.strip()
        if not raw:
            detail = completed.stderr.strip() or f"worker exited {completed.returncode}"
            raise BirdExecutionError(loaded.bird_id, "crashed", detail)
        try:
            response = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BirdExecutionError(
                loaded.bird_id, "returned invalid JSON", raw[:200]
            ) from exc
        if not isinstance(response, dict):
            raise BirdExecutionError(
                loaded.bird_id, "returned invalid response", "root must be an object"
            )
        if not response.get("ok"):
            error = response.get("error") or {}
            kind = str(error.get("type") or "failed")
            message = str(error.get("message") or "unknown worker failure")
            raise BirdExecutionError(loaded.bird_id, kind, message)
        opinion_payload = response.get("opinion")
        if not isinstance(opinion_payload, dict):
            raise BirdExecutionError(
                loaded.bird_id, "returned invalid schema", "opinion must be an object"
            )
        try:
            opinion = decode_opinion(opinion_payload, loaded.bird_id)
        except (TypeError, ValueError) as exc:
            raise BirdExecutionError(
                loaded.bird_id, "returned invalid schema", str(exc)
            ) from exc
        return BirdExecutionResult(opinion=opinion, runtime_ms=0.0)
