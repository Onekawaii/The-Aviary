from __future__ import annotations

import unittest

from aviary.simulation import (
    DeterministicSimulation,
    EntityBlueprint,
    SimulationEvent,
    SimulationValidationError,
)


class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.blueprints = (
            EntityBlueprint("raven-1", "bird", {"energy": 10, "mood": "watching"}),
        )

    def test_replay_is_deterministic_across_input_order(self):
        events = (
            SimulationEvent("b", 1, "increment_property", "raven-1", {"key": "energy", "amount": 2}),
            SimulationEvent("a", 0, "set_property", "raven-1", {"key": "mood", "value": "flying"}),
        )
        first = DeterministicSimulation().replay(self.blueprints, events)
        second = DeterministicSimulation().replay(self.blueprints, tuple(reversed(events)))
        self.assertEqual(first, second)
        self.assertEqual(first.final_state["raven-1"]["energy"], 12)

    def test_replay_uses_fresh_state(self):
        sim = DeterministicSimulation()
        event = SimulationEvent("a", 0, "increment_property", "raven-1", {"key": "energy"})
        first = sim.replay(self.blueprints, (event,))
        second = sim.replay(self.blueprints, (event,))
        self.assertEqual(first.final_state["raven-1"]["energy"], 11)
        self.assertEqual(first, second)

    def test_snapshot_hash_changes_with_state(self):
        event = SimulationEvent("a", 1, "increment_property", "raven-1", {"key": "energy"})
        result = DeterministicSimulation().replay(self.blueprints, (event,))
        self.assertEqual(len(result.snapshots), 2)
        self.assertNotEqual(result.snapshots[0].state_hash, result.snapshots[1].state_hash)
        self.assertEqual(len(result.receipt_hash), 64)

    def test_duplicate_event_ids_fail(self):
        event = SimulationEvent("same", 0, "set_property", "raven-1", {"key": "mood", "value": "x"})
        with self.assertRaisesRegex(SimulationValidationError, "duplicate event_id"):
            DeterministicSimulation().replay(self.blueprints, (event, event))

    def test_unknown_effect_fails(self):
        event = SimulationEvent("a", 0, "summon_void", "raven-1")
        with self.assertRaisesRegex(SimulationValidationError, "unknown effect"):
            DeterministicSimulation().replay(self.blueprints, (event,))

    def test_missing_target_fails(self):
        event = SimulationEvent("a", 0, "set_property", "missing", {"key": "mood", "value": "x"})
        with self.assertRaisesRegex(SimulationValidationError, "unknown entity"):
            DeterministicSimulation().replay(self.blueprints, (event,))

    def test_event_beyond_until_tick_fails(self):
        event = SimulationEvent("a", 2, "set_property", "raven-1", {"key": "mood", "value": "x"})
        with self.assertRaisesRegex(SimulationValidationError, "exceeds"):
            DeterministicSimulation().replay(self.blueprints, (event,), until_tick=1)

    def test_nested_non_string_object_keys_fail_before_hashing(self):
        blueprints = (
            EntityBlueprint("raven-1", "bird", {"nested": {1: "value"}}),
        )
        with self.assertRaisesRegex(SimulationValidationError, "keys must be strings"):
            DeterministicSimulation().replay(blueprints, ())

    def test_hashed_state_is_deeply_immutable(self):
        blueprints = (
            EntityBlueprint("raven-1", "bird", {"nested": {"value": 1}, "trail": [1, 2]}),
        )
        result = DeterministicSimulation().replay(blueprints, ())
        with self.assertRaises(TypeError):
            result.final_state["raven-1"]["nested"]["value"] = 2
        with self.assertRaises(TypeError):
            result.snapshots[0].state["raven-1"]["nested"]["value"] = 2
        nested = result.final_state["raven-1"]["nested"]
        with self.assertRaises(TypeError):
            nested |= {"value": 2}
        self.assertIsInstance(result.final_state["raven-1"]["trail"], tuple)

    def test_malformed_events_are_validated_before_sorting(self):
        malformed = (
            SimulationEvent("valid", 0, "set_property", "raven-1", {"key": "mood", "value": "x"}),
            SimulationEvent("bad-tick", "bad", "set_property", "raven-1", {"key": "mood", "value": "x"}),  # type: ignore[arg-type]
        )
        with self.assertRaisesRegex(SimulationValidationError, "event tick"):
            DeterministicSimulation().replay(self.blueprints, malformed)

        malformed_ids = (
            SimulationEvent("valid", 0, "set_property", "raven-1", {"key": "mood", "value": "x"}),
            SimulationEvent(1, 0, "set_property", "raven-1", {"key": "mood", "value": "x"}),  # type: ignore[arg-type]
        )
        with self.assertRaisesRegex(SimulationValidationError, "event_id"):
            DeterministicSimulation().replay(self.blueprints, malformed_ids)


if __name__ == "__main__":
    unittest.main()
