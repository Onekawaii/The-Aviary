# Process Isolation — Perch Gate

Status: In development

## Purpose

Run each bird in a separate Python subprocess. The council sends one JSON request and accepts one validated JSON response. Birds do not receive the ledger, registry, council, or another bird instance.

## Current slice

- `aviary.runtime.worker` imports exactly one registered bird module and executes one analysis request.
- `BirdSandbox` applies a wall-clock timeout, captures crashes, parses JSON, and reconstructs a validated `BirdOpinion`.
- Bird identity, summary, string-list fields, confidence, and JSON-object data are validated at the process boundary.

## Verification

```text
python -m unittest tests.test_runtime -v
python verify.py
```

## Demonstration

A built-in Duck analysis is serialized to a subprocess, executed, returned as JSON, and reconstructed in the parent process.

## Failure cases

- Worker timeout raises `BirdExecutionError(kind="timed out")`.
- Empty output is classified as a crash.
- Invalid JSON is rejected.
- A mismatched `bird_id` or malformed opinion is rejected as an invalid schema.

## Known limitations

- The engine does not use the sandbox yet; this first commit proves the execution boundary independently.
- This is process isolation, not a complete hostile-code sandbox. Filesystem and network restrictions are not yet enforced.
- OS-level memory limits are not yet portable across Windows and Termux.
- Per-bird failure receipts are added in the next integration commit.
