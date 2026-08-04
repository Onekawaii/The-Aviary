from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Callable, Literal

from aviary.simulation.contracts import (
    SimulationEvent,
    SimulationValidationError,
    _canonical_json,
    _validated_json_object,
)

Decision = Literal["accepted", "rejected"]


@dataclass(frozen=True, slots=True)
class GovernorVerdict:
    accepted: bool
    reason: str

    def validate(self) -> None:
        if not isinstance(self.accepted, bool):
            raise SimulationValidationError("governor verdict accepted must be a boolean")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise SimulationValidationError("governor verdict reason cannot be empty")


@dataclass(frozen=True, slots=True)
class DialogueRecord:
    event_id: str
    tick: int
    decision: Decision
    reason: str


@dataclass(frozen=True, slots=True)
class DialogueResult:
    records: tuple[DialogueRecord, ...]
    accepted_events: tuple[SimulationEvent, ...]
    receipt_hash: str

    @classmethod
    def create(
        cls,
        records: tuple[DialogueRecord, ...],
        accepted_events: tuple[SimulationEvent, ...],
    ) -> "DialogueResult":
        payload = {
            "records": [
                {
                    "event_id": record.event_id,
                    "tick": record.tick,
                    "decision": record.decision,
                    "reason": record.reason,
                }
                for record in records
            ],
            "accepted_events": [
                {
                    "event_id": event.event_id,
                    "tick": event.tick,
                    "kind": event.kind,
                    "target_id": event.target_id,
                    "payload": event.payload,
                }
                for event in accepted_events
            ],
        }
        digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        return cls(records=records, accepted_events=accepted_events, receipt_hash=digest)


Governor = Callable[[SimulationEvent], GovernorVerdict]


class DeterministicDialogue:
    """Deterministically gate candidate events before simulation replay.

    The proposal side supplies candidate ``SimulationEvent`` objects. The
    governor side returns an explicit verdict for each candidate. This class
    records both accepted and rejected outcomes while emitting only accepted
    events for the simulation kernel.
    """

    def deliberate(
        self,
        proposals: tuple[SimulationEvent, ...],
        governor: Governor,
    ) -> DialogueResult:
        if not callable(governor):
            raise SimulationValidationError("governor must be callable")

        proposal_ids: set[str] = set()
        normalized: list[SimulationEvent] = []
        for proposal in proposals:
            if not isinstance(proposal, SimulationEvent):
                raise SimulationValidationError("proposal must be a SimulationEvent")
            proposal.validate()
            if proposal.event_id in proposal_ids:
                raise SimulationValidationError(
                    f"duplicate proposal event_id: {proposal.event_id}"
                )
            proposal_ids.add(proposal.event_id)
            normalized.append(
                SimulationEvent(
                    event_id=proposal.event_id,
                    tick=proposal.tick,
                    kind=proposal.kind,
                    target_id=proposal.target_id,
                    payload=_validated_json_object(proposal.payload, "event payload"),
                )
            )

        ordered = sorted(normalized, key=lambda event: (event.tick, event.event_id))
        records: list[DialogueRecord] = []
        accepted_events: list[SimulationEvent] = []

        for proposal in ordered:
            verdict = governor(proposal)
            if not isinstance(verdict, GovernorVerdict):
                raise SimulationValidationError(
                    "governor must return a GovernorVerdict"
                )
            verdict.validate()
            decision: Decision = "accepted" if verdict.accepted else "rejected"
            records.append(
                DialogueRecord(
                    event_id=proposal.event_id,
                    tick=proposal.tick,
                    decision=decision,
                    reason=verdict.reason.strip(),
                )
            )
            if verdict.accepted:
                accepted_events.append(proposal)

        return DialogueResult.create(tuple(records), tuple(accepted_events))
