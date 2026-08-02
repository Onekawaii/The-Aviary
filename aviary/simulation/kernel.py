from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping

from aviary.simulation.contracts import (
    EntityBlueprint,
    ReplayResult,
    SimulationEvent,
    SimulationSnapshot,
    SimulationValidationError,
)
from aviary.simulation.effects import BUILTIN_EFFECTS

Effect = Callable[
    [Mapping[str, Mapping[str, Any]], SimulationEvent],
    dict[str, dict[str, Any]],
]


class DeterministicSimulation:
    def __init__(self, effects: Mapping[str, Effect] | None = None):
        self._effects: dict[str, Effect] = dict(BUILTIN_EFFECTS)
        if effects:
            for kind, effect in effects.items():
                self.register_effect(kind, effect)

    def register_effect(self, kind: str, effect: Effect) -> None:
        if not kind.strip():
            raise SimulationValidationError("effect kind cannot be empty")
        if not callable(effect):
            raise SimulationValidationError("effect must be callable")
        self._effects[kind] = effect

    def replay(
        self,
        blueprints: tuple[EntityBlueprint, ...],
        events: tuple[SimulationEvent, ...],
        until_tick: int | None = None,
    ) -> ReplayResult:
        if until_tick is not None and (
            not isinstance(until_tick, int)
            or isinstance(until_tick, bool)
            or until_tick < 0
        ):
            raise SimulationValidationError("until_tick must be a non-negative integer")

        state: dict[str, dict[str, Any]] = {}
        for blueprint in blueprints:
            blueprint.validate()
            if blueprint.entity_id in state:
                raise SimulationValidationError(
                    f"duplicate entity_id: {blueprint.entity_id}"
                )
            state[blueprint.entity_id] = deepcopy(dict(blueprint.state))

        event_ids: set[str] = set()
        ordered_events = sorted(events, key=lambda event: (event.tick, event.event_id))
        for event in ordered_events:
            event.validate()
            if event.event_id in event_ids:
                raise SimulationValidationError(f"duplicate event_id: {event.event_id}")
            event_ids.add(event.event_id)
            if event.kind not in self._effects:
                raise SimulationValidationError(
                    f"event {event.event_id!r} uses unknown effect {event.kind!r}"
                )

        max_event_tick = ordered_events[-1].tick if ordered_events else 0
        final_tick = max_event_tick if until_tick is None else until_tick
        if until_tick is not None and max_event_tick > until_tick:
            raise SimulationValidationError("event tick exceeds until_tick")

        events_by_tick: dict[int, list[SimulationEvent]] = {}
        for event in ordered_events:
            events_by_tick.setdefault(event.tick, []).append(event)

        snapshots: list[SimulationSnapshot] = []
        for tick in range(final_tick + 1):
            for event in events_by_tick.get(tick, []):
                state = self._effects[event.kind](state, event)
            snapshot_state = deepcopy(state)
            snapshots.append(SimulationSnapshot.create(tick, snapshot_state))

        final_state = deepcopy(state)
        return ReplayResult.create(tuple(snapshots), final_state)
