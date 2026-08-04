from __future__ import annotations

import unittest

from aviary.simulation.contracts import SimulationEvent, SimulationValidationError
from aviary.simulation.dialogue import DeterministicDialogue, GovernorVerdict


class DeterministicDialogueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dialogue = DeterministicDialogue()

    def test_orders_proposals_and_records_rejections(self) -> None:
        proposals = (
            SimulationEvent("b", 1, "set", "ape", {"value": 2}),
            SimulationEvent("a", 1, "set", "ape", {"value": 1}),
            SimulationEvent("z", 0, "set", "ape", {"value": 0}),
        )

        result = self.dialogue.deliberate(
            proposals,
            lambda event: GovernorVerdict(
                accepted=event.event_id != "b",
                reason="allowed" if event.event_id != "b" else "blocked",
            ),
        )

        self.assertEqual([record.event_id for record in result.records], ["z", "a", "b"])
        self.assertEqual(
            [record.decision for record in result.records],
            ["accepted", "accepted", "rejected"],
        )
        self.assertEqual(
            [event.event_id for event in result.accepted_events],
            ["z", "a"],
        )

    def test_receipt_is_stable_for_equivalent_input_order(self) -> None:
        first = SimulationEvent("a", 1, "set", "ape", {"value": 1})
        second = SimulationEvent("b", 0, "set", "ape", {"value": 2})
        governor = lambda event: GovernorVerdict(True, "accepted by policy")

        left = self.dialogue.deliberate((first, second), governor)
        right = self.dialogue.deliberate((second, first), governor)

        self.assertEqual(left.receipt_hash, right.receipt_hash)

    def test_result_payload_is_deeply_immutable(self) -> None:
        payload = {"nested": {"values": [1, 2]}}
        result = self.dialogue.deliberate(
            (SimulationEvent("a", 0, "set", "ape", payload),),
            lambda event: GovernorVerdict(True, "accepted"),
        )
        payload["nested"]["values"].append(3)

        frozen = result.accepted_events[0].payload
        self.assertEqual(tuple(frozen["nested"]["values"]), (1, 2))
        with self.assertRaises(TypeError):
            frozen["new"] = True  # type: ignore[index]

    def test_rejects_duplicate_proposal_ids(self) -> None:
        proposal = SimulationEvent("same", 0, "set", "ape", {})
        with self.assertRaisesRegex(
            SimulationValidationError, "duplicate proposal event_id"
        ):
            self.dialogue.deliberate(
                (proposal, proposal),
                lambda event: GovernorVerdict(True, "accepted"),
            )

    def test_rejects_invalid_governor_result(self) -> None:
        proposal = SimulationEvent("a", 0, "set", "ape", {})
        with self.assertRaisesRegex(
            SimulationValidationError, "must return a GovernorVerdict"
        ):
            self.dialogue.deliberate((proposal,), lambda event: True)  # type: ignore[arg-type,return-value]

    def test_rejects_empty_reason(self) -> None:
        proposal = SimulationEvent("a", 0, "set", "ape", {})
        with self.assertRaisesRegex(
            SimulationValidationError, "reason cannot be empty"
        ):
            self.dialogue.deliberate(
                (proposal,), lambda event: GovernorVerdict(True, "  ")
            )


if __name__ == "__main__":
    unittest.main()
