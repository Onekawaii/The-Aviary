from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from aviary.simulation.contracts import (
    SimulationEvent,
    SimulationValidationError,
    _validated_json_object,
)


@dataclass(frozen=True, slots=True)
class Chronicle:
    """Canonical immutable history of validated simulation events."""

    entries: tuple[SimulationEvent, ...]

    @classmethod
    def create(cls, events: Iterable[SimulationEvent]) -> "Chronicle":
        validated: list[SimulationEvent] = []
        event_ids: set[str] = set()
        for event in events:
            if not isinstance(event, SimulationEvent):
                raise SimulationValidationError(
                    "chronicle entries must be SimulationEvent instances"
                )
            event.validate()
            if event.event_id in event_ids:
                raise SimulationValidationError(
                    f"duplicate event_id: {event.event_id}"
                )
            event_ids.add(event.event_id)
            validated.append(
                SimulationEvent(
                    event_id=event.event_id,
                    tick=event.tick,
                    kind=event.kind,
                    target_id=event.target_id,
                    payload=_validated_json_object(event.payload, "event payload"),
                )
            )
        validated.sort(key=lambda event: (event.tick, event.event_id))
        return cls(entries=tuple(validated))

    def through(self, tick: int) -> "Chronicle":
        if not isinstance(tick, int) or isinstance(tick, bool) or tick < 0:
            raise SimulationValidationError("tick must be a non-negative integer")
        return Chronicle(tuple(event for event in self.entries if event.tick <= tick))

    def after(self, tick: int) -> "Chronicle":
        if not isinstance(tick, int) or isinstance(tick, bool) or tick < 0:
            raise SimulationValidationError("tick must be a non-negative integer")
        return Chronicle(tuple(event for event in self.entries if event.tick > tick))
