from __future__ import annotations

import importlib
import inspect
import json
import sys
from contextlib import redirect_stdout
from dataclasses import asdict

from aviary.contracts import Bird, Topic


def _load_bird(module_name: str, bird_id: str) -> Bird:
    module = importlib.import_module(module_name)
    candidates = [
        obj
        for _, obj in inspect.getmembers(module, inspect.isclass)
        if issubclass(obj, Bird) and obj is not Bird and obj.__module__ == module.__name__
    ]
    for cls in candidates:
        instance = cls()
        if instance.metadata().bird_id == bird_id:
            return instance
    raise LookupError(f"bird {bird_id!r} not found in {module_name!r}")


def main() -> int:
    protocol_stdout = sys.stdout
    try:
        # Plugin imports and analysis may print diagnostics. Keep stdout reserved
        # for exactly one JSON protocol response; diagnostics are sent to stderr.
        with redirect_stdout(sys.stderr):
            request = json.loads(sys.stdin.read())
            bird = _load_bird(str(request["module"]), str(request["bird_id"]))
            topic_data = request["topic"]
            topic = Topic(str(topic_data["text"]), topic_data.get("context") or {})
            opinion = bird.analyze(topic)
            response = {"ok": True, "opinion": asdict(opinion)}
    except Exception as exc:
        response = {
            "ok": False,
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
        }
    protocol_stdout.write(json.dumps(response, sort_keys=True, separators=(",", ":")))
    protocol_stdout.flush()
    return 0 if response["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
