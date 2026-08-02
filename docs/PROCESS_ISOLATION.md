# Process Isolation — Perch Gate

Status: Engine-integrated

## Purpose

Run each bird in a separate Python subprocess. The council sends one JSON request and accepts one validated JSON response. Birds do not receive the ledger, registry, council, or another bird instance.

## Current slice

- `aviary.runtime.worker` imports exactly one registered bird module and executes one analysis request.
- `BirdSandbox` applies a wall-clock timeout, captures crashes, parses JSON, measures runtime, and reconstructs a validated `BirdOpinion`.
- Bird identity, summary, string-list fields, confidence, and JSON-object data are validated at the process boundary.
- `AviaryEngine` routes every bird analysis through `BirdSandbox`.
- A failed bird marks the session `failed`, records a SHA-256 `bird_failure` receipt, and remains visible in history without becoming replayable.

## Verification

```text
python -m unittest tests.test_runtime tests.test_engine_isolation -v
python verify.py
```

## Demonstration

A normal council run now launches each built-in bird in its own Python subprocess. Six validated opinions return to the parent process, are recorded, and produce the normal council receipt.

## Failure cases

- Worker timeout raises `BirdExecutionError(kind="timed out")`.
- Empty output is classified as a crash.
- Invalid JSON is rejected.
- A mismatched `bird_id` or malformed opinion is rejected as an invalid schema.
- Any boundary failure stops council aggregation, marks the session failed, and records a failure receipt containing the bird ID, failure kind, message, and elapsed time.

## Known limitations

- This is process isolation, not a complete hostile-code sandbox. Filesystem and network restrictions are not yet enforced.
- OS-level memory limits are not yet portable across Windows and Termux.
- Birds currently execute sequentially, so six subprocess startups increase council latency.
- A future phase will add plugin enable/disable quarantine before third-party bird loading.
