# Deterministic Simulation Core

## Purpose

Provide a small, replayable engine for Arkheopantheochive timelines and future world simulation without coupling simulation state to birds, rendering, HTTP, or editor UI.

## Source

- `aviary/simulation/contracts.py`
- `aviary/simulation/effects.py`
- `aviary/simulation/kernel.py`
- `aviary/simulation/__init__.py`

## Automated tests

`tests/test_simulation.py` verifies deterministic ordering, fresh replay state, per-tick hashes, receipt hashes, duplicate event rejection, unknown-effect rejection, missing-target rejection, and timeline bounds.

## Verification command

```bash
python verify.py
```

## Demonstration

Two input event sequences containing the same events in different orders produce equal snapshots, final state, and SHA-256 replay receipts because events are canonically ordered by `(tick, event_id)`.

## Failure case

An event using an unregistered effect or targeting an absent entity is rejected with `SimulationValidationError` before a replay receipt is produced.

## Known limitations

- Only `set_property` and `increment_property` are built in.
- Replay is intentionally in memory; SQLite persistence is a later integration phase.
- Effects are trusted Python callables and are not subprocess-isolated.
- No scene renderer, bridge endpoint, timeline editor, or GUI is included.
- The automation runtime could not clone GitHub for an independent local run because DNS resolution was unavailable; the exact-head GitHub Actions matrix is authoritative for this phase.
