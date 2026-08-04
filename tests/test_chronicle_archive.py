from __future__ import annotations

import unittest

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


class ChronicleArchiveTests(unittest.TestCase):
    def test_chronicle_canonicalizes_event_order(self) -> None:
        chronicle = Chronicle.create(_events())
        self.assertEqual(
            tuple(event.event_id for event in chronicle.entries),
            ("event-a", "event-b"),
        )

    def test_chronicle_rejects_duplicate_event_ids(self) -> None:
        event = _events()[0]
        with self.assertRaisesRegex(SimulationValidationError, "duplicate event_id"):
            Chronicle.create((event, event))

    def test_archive_replay_is_deterministic(self) -> None:
        archive = Archive.create(_blueprints(), Chronicle.create(_events()))
        first = archive.replay()
        second = archive.replay()
        self.assertEqual(first.receipt_hash, second.receipt_hash)
        self.assertEqual(first.final_state, second.final_state)

    def test_archive_rewind_reconstructs_requested_tick(self) -> None:
        archive = Archive.create(_blueprints(), Chronicle.create(_events()))
        result = archive.rewind(1)
        self.assertEqual(len(result.snapshots), 2)
        self.assertEqual(result.final_state["nest"]["signal"], 3)
        self.assertEqual(result.final_state["nest"]["mode"], "quiet")

    def test_archive_fork_excludes_future_events(self) -> None:
        archive = Archive.create(_blueprints(), Chronicle.create(_events()))
        fork = archive.fork(1)
        self.assertEqual(
            tuple(event.event_id for event in fork.chronicle.entries),
            ("event-a",),
        )
        self.assertEqual(fork.replay().final_state["nest"]["mode"], "quiet")

    def test_fossil_is_immutable_and_verifiable(self) -> None:
        archive = Archive.create(_blueprints(), Chronicle.create(_events()))
        fossil = archive.fossil(2, "awakening")
        self.assertTrue(fossil.verify())
        self.assertEqual(
            fossil.state_hash,
            archive.replay().snapshots[2].state_hash,
        )
        with self.assertRaises(TypeError):
            fossil.state["nest"]["signal"] = 99


    def test_chronicle_freezes_source_event_payloads(self) -> None:
        payload = {"nested": {"values": [1, 2]}}
        event = SimulationEvent(
            "event-a",
            0,
            "set_property",
            "nest",
            payload,
        )
        chronicle = Chronicle.create((event,))

        payload["nested"]["values"].append(3)

        frozen_payload = chronicle.entries[0].payload
        self.assertEqual(tuple(frozen_payload["nested"]["values"]), (1, 2))
        with self.assertRaises(TypeError):
            frozen_payload["new"] = True

    def test_archive_snapshots_source_blueprint_state(self) -> None:
        state = {"signal": 0, "nested": {"values": [1, 2]}}
        blueprint = EntityBlueprint("nest", "place", state)
        archive = Archive.create((blueprint,), Chronicle.create(()))
        first = archive.replay()

        state["signal"] = 99
        state["nested"]["values"].append(3)
        second = archive.replay()

        self.assertEqual(first.receipt_hash, second.receipt_hash)
        self.assertEqual(archive.blueprints[0].state["signal"], 0)
        self.assertEqual(
            tuple(archive.blueprints[0].state["nested"]["values"]),
            (1, 2),
        )
        with self.assertRaises(TypeError):
            archive.blueprints[0].state["new"] = True

    def test_archive_fossil_validates_and_normalizes_name(self) -> None:
        archive = Archive.create(_blueprints(), Chronicle.create(_events()))
        fossil = archive.fossil(2, "  awakening  ")

        self.assertEqual(fossil.name, "awakening")
        with self.assertRaisesRegex(ValueError, "fossil name cannot be empty"):
            archive.fossil(2, "   ")

if __name__ == "__main__":
    unittest.main()
