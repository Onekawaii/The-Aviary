from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from aviary.simulation.contracts import SimulationEvent, SimulationValidationError


def _target(state: dict[str, dict[str, Any]], event: SimulationEvent) -> dict[str, Any]:
    try:
        return state[event.target_id]
    except KeyError as exc:
        raise SimulationValidationError(
            f"event {event.event_id!r} targets unknown entity {event.target_id!r}"
        ) from exc


def set_property(
    state: Mapping[str, Mapping[str, Any]], event: SimulationEvent
) -> dict[str, dict[str, Any]]:
    key = event.payload.get("key")
    if not isinstance(key, str) or not key.strip():
        raise SimulationValidationError("set_property requires a non-empty string key")
    if "value" not in event.payload:
        raise SimulationValidationError("set_property requires a value")
    updated = deepcopy({entity_id: dict(values) for entity_id, values in state.items()})
    _target(updated, event)[key] = deepcopy(event.payload["value"])
    return updated


def increment_property(
    state: Mapping[str, Mapping[str, Any]], event: SimulationEvent
) -> dict[str, dict[str, Any]]:
    key = event.payload.get("key")
    amount = event.payload.get("amount", 1)
    if not isinstance(key, str) or not key.strip():
        raise SimulationValidationError("increment_property requires a non-empty string key")
    if not isinstance(amount, (int, float)) or isinstance(amount, bool):
        raise SimulationValidationError("increment_property amount must be numeric")
    updated = deepcopy({entity_id: dict(values) for entity_id, values in state.items()})
    target = _target(updated, event)
    current = target.get(key, 0)
    if not isinstance(current, (int, float)) or isinstance(current, bool):
        raise SimulationValidationError(
            f"property {key!r} on {event.target_id!r} is not numeric"
        )
    target[key] = current + amount
    return updated


BUILTIN_EFFECTS = {
    "set_property": set_property,
    "increment_property": increment_property,
}
