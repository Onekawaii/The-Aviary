from __future__ import annotations

import pytest

from aviary.simulation import (
    Archive,
    Chronicle,
    EntityBlueprint,
    SimulationEvent,
    SimulationValidationError,
)


def _blueprints() -> tuple[EntityBlueprint, ...]:
    return (EntityBlueprint("nest", "place", {"signal": 0, "mode": "quiet"}),)


def _events() -> tuple[SimulationEvent, ...]:
    return (
        SimulationEvent(
            "event-b",
            2,
            "set_property",
            "nest",
            {"key": "mode", "value": "awake"},
        ),
        SimulationEvent(
            "event-a",
            1,
            "increment_property",
            "nest",
            {"key": "signal", "amount": 3},
        ),
    )


def test_chronicle_canonicalizes_event_order() -> None:
    chronicle = Chronicle.create(_events())
    assert tuple(event.event_id for event in chronicle.entries) == (
        "event-a",
        "event-b",
    )


def test_chronicle_rejects_duplicate_event_ids() -> None:
    event = _events()[0]
    with pytest.raises(SimulationValidationError, match="duplicate event_id"):
        Chronicle.create((event, event))


def test_archive_replay_is_deterministic() -> None:
    archive = Archive.create(_blueprints(), Chronicle.create(_events()))
    first = archive.replay()
    second = archive.replay()
    assert first.receipt_hash == second.receipt_hash
    assert first.final_state == second.final_state


def test_archive_rewind_reconstructs_requested_tick() -> None:
    archive = Archive.create(_blueprints(), Chronicle.create(_events()))
    result = archive.rewind(1)
    assert len(result.snapshots) == 2
    assert result.final_state["nest"]["signal"] == 3
    assert result.final_state["nest"]["mode"] == "quiet"


def test_archive_fork_excludes_future_events() -> None:
    archive = Archive.create(_blueprints(), Chronicle.create(_events()))
    fork = archive.fork(1)
    assert tuple(event.event_id for event in fork.chronicle.entries) == ("event-a",)
    assert fork.replay().final_state["nest"]["mode"] == "quiet"


def test_fossil_is_immutable_and_verifiable() -> None:
    archive = Archive.create(_blueprints(), Chronicle.create(_events()))
    fossil = archive.fossil(2, "awakening")
    assert fossil.verify()
    assert fossil.state_hash == archive.replay().snapshots[2].state_hash
    with pytest.raises(TypeError):
        fossil.state["nest"]["signal"] = 99
