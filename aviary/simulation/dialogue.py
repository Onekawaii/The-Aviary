from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable, Literal

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
    kind: str
    target_id: str
    payload: Mapping[str, Any]
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
        normalized_records: list[DialogueRecord] = []
        for record in records:
            if not isinstance(record, DialogueRecord):
                raise SimulationValidationError(
                    "dialogue records must be DialogueRecord instances"
                )
            if record.decision not in ("accepted", "rejected"):
                raise SimulationValidationError(
                    "dialogue record decision must be accepted or rejected"
                )
            if not isinstance(record.reason, str) or not record.reason.strip():
                raise SimulationValidationError(
                    "dialogue record reason cannot be empty"
                )
            proposal = _normalized_event(
                SimulationEvent(
                    event_id=record.event_id,
                    tick=record.tick,
                    kind=record.kind,
                    target_id=record.target_id,
                    payload=record.payload,
                ),
                "dialogue record",
            )
            normalized_records.append(
                DialogueRecord(
                    event_id=proposal.event_id,
                    tick=proposal.tick,
                    kind=proposal.kind,
                    target_id=proposal.target_id,
                    payload=proposal.payload,
                    decision=record.decision,
                    reason=record.reason.strip(),
                )
            )

        normalized_accepted_events = tuple(
            _normalized_event(event, "accepted event") for event in accepted_events
        )
        payload = {
            "records": [
                {
                    "event_id": record.event_id,
                    "tick": record.tick,
                    "kind": record.kind,
                    "target_id": record.target_id,
                    "payload": record.payload,
                    "decision": record.decision,
                    "reason": record.reason,
                }
                for record in normalized_records
            ],
            "accepted_events": [
                {
                    "event_id": event.event_id,
                    "tick": event.tick,
                    "kind": event.kind,
                    "target_id": event.target_id,
                    "payload": event.payload,
                }
                for event in normalized_accepted_events
            ],
        }
        digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        return cls(
            records=tuple(normalized_records),
            accepted_events=normalized_accepted_events,
            receipt_hash=digest,
        )


Governor = Callable[[SimulationEvent], GovernorVerdict]


def _normalized_event(event: SimulationEvent, field_name: str) -> SimulationEvent:
    if not isinstance(event, SimulationEvent):
        raise SimulationValidationError(
            f"{field_name} must be a SimulationEvent"
        )
    event.validate()
    return SimulationEvent(
        event_id=event.event_id,
        tick=event.tick,
        kind=event.kind,
        target_id=event.target_id,
        payload=_validated_json_object(event.payload, "event payload"),
    )


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
            proposal = _normalized_event(proposal, "proposal")
            if proposal.event_id in proposal_ids:
                raise SimulationValidationError(
                    f"duplicate proposal event_id: {proposal.event_id}"
                )
            proposal_ids.add(proposal.event_id)
            normalized.append(proposal)

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
                    kind=proposal.kind,
                    target_id=proposal.target_id,
                    payload=proposal.payload,
                    decision=decision,
                    reason=verdict.reason.strip(),
                )
            )
            if verdict.accepted:
                accepted_events.append(proposal)

        return DialogueResult.create(tuple(records), tuple(accepted_events))
