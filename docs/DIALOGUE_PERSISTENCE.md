# Dialogue Receipt Persistence

The deterministic dialogue core can now be written to and reconstructed from the Aviary SQLite ledger without exposing a network or GUI surface.

## Contract

`DialogueReceiptStore.record(result)` stores one canonical dialogue document keyed by its SHA-256 receipt. Recording the same valid receipt again returns the original `dialogue_id`.

`DialogueReceiptStore.load(dialogue_id)` reconstructs a new immutable `DialogueResult` and compares its independently calculated receipt with the stored receipt.

```python
from pathlib import Path

from aviary.ledger import SQLiteLedger
from aviary.simulation import (
    DeterministicDialogue,
    DialogueReceiptStore,
    GovernorVerdict,
    SimulationEvent,
)

ledger = SQLiteLedger(Path("ledger/aviary.db"))
try:
    result = DeterministicDialogue().deliberate(
        (
            SimulationEvent(
                "move",
                1,
                "set_property",
                "ape-1",
                {"key": "x", "value": 2},
            ),
        ),
        lambda event: GovernorVerdict(True, "allowed"),
    )
    store = DialogueReceiptStore(ledger)
    dialogue_id = store.record(result)
    stored = store.load(dialogue_id)
    assert stored.valid
    assert stored.result == result
finally:
    ledger.close()
```

## Stored evidence

The `dialogue_runs` row contains:

- canonical dialogue JSON containing every accepted and rejected proposal
- stored receipt SHA-256
- total decision-record count
- accepted-event count
- creation timestamp

A `dialogue.recorded` history event records the dialogue ID, receipt hash, and counts.

## Failure behavior

- missing dialogue ID raises `LookupError`
- malformed JSON raises `ValueError`
- malformed document structure raises `ValueError`
- stored count mismatch raises `ValueError`
- reconstructable content tampering returns `StoredDialogue.valid == False`
- duplicate recording of an already-corrupt receipt raises `ValueError`

## Verification

```bash
python verify.py
python -m unittest tests.test_dialogue_persistence -v
```

## Boundaries

This phase does not add dialogue listing, deletion, Local Bridge routes, CLI commands, governor policy language, LLM calls, authentication, signatures, browser assets, or GUI work. SHA-256 demonstrates internal consistency, not authorship.
