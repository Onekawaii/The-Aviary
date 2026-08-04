# Deterministic Dialogue Core

The dialogue core is a pre-replay decision boundary. It does not simulate consciousness and it does not mutate world state.

Candidate `SimulationEvent` objects represent proposals. A governor callable returns one explicit `GovernorVerdict` for every proposal. The dialogue sorts proposals by `(tick, event_id)`, records accepted and rejected decisions, emits only accepted events, and hashes the complete decision receipt.

```python
from aviary.simulation import (
    DeterministicDialogue,
    GovernorVerdict,
    SimulationEvent,
)

proposals = (
    SimulationEvent("inspect", 0, "set", "ape", {"curious": True}),
    SimulationEvent("cross-wall", 0, "set", "ape", {"x": 99}),
)


def governor(event: SimulationEvent) -> GovernorVerdict:
    if event.event_id == "cross-wall":
        return GovernorVerdict(False, "boundary blocks the proposal")
    return GovernorVerdict(True, "proposal satisfies policy")


result = DeterministicDialogue().deliberate(proposals, governor)
```

`result.records` preserves the complete negotiation. `result.accepted_events` can be passed to `DeterministicSimulation.replay`. `result.receipt_hash` is stable for equivalent proposal sets and verdicts.

## Failure cases

The core rejects malformed events, duplicate proposal IDs, a non-callable governor, non-`GovernorVerdict` returns, non-boolean verdicts, and empty reasons.

## Boundaries

The governor is injected and replaceable. The dialogue core does not call birds, the council, the ledger, the Local Bridge, an LLM, or any UI. SHA-256 proves internal consistency only; it does not prove authorship.
