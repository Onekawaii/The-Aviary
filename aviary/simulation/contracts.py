from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any


class SimulationValidationError(ValueError):
    pass


class FrozenJSONMapping(Mapping[str, Any]):
    """Tuple-backed immutable JSON object.

    This deliberately does not inherit from ``dict`` so mutable base-class
    descriptors such as ``dict.__setitem__`` cannot bypass immutability.
    """

    __slots__ = ("_items",)

    def __init__(self, items: tuple[tuple[str, Any], ...]):
        self._items = items

    def __getitem__(self, key: str) -> Any:
        for item_key, value in self._items:
            if item_key == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (key for key, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return f"FrozenJSONMapping({dict(self._items)!r})"

    def __deepcopy__(self, memo: dict[int, Any]) -> "FrozenJSONMapping":
        return self


def _freeze_json(value: Any, field_name: str) -> Any:
    if isinstance(value, Mapping):
        frozen_items: list[tuple[str, Any]] = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise SimulationValidationError(
                    f"{field_name} object keys must be strings"
                )
            frozen_items.append((key, _freeze_json(item, field_name)))
        frozen_items.sort(key=lambda pair: pair[0])
        return FrozenJSONMapping(tuple(frozen_items))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item, field_name) for item in value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SimulationValidationError(
                f"{field_name} must contain finite JSON numbers"
            )
        return value
    raise SimulationValidationError(f"{field_name} must be JSON serializable")


def _plain_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json(item) for item in value]
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _plain_json(value),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _validated_json_object(
    value: Mapping[str, Any], field_name: str
) -> FrozenJSONMapping:
    if not isinstance(value, Mapping):
        raise SimulationValidationError(f"{field_name} must be a JSON object")
    frozen = _freeze_json(value, field_name)
    assert isinstance(frozen, FrozenJSONMapping)
    return frozen


def _validate_json_object(value: Mapping[str, Any], field_name: str) -> None:
    _validated_json_object(value, field_name)


@dataclass(frozen=True, slots=True)
class EntityBlueprint:
    entity_id: str
    kind: str
    state: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not isinstance(self.entity_id, str) or not self.entity_id.strip():
            raise SimulationValidationError("entity_id cannot be empty")
        if not isinstance(self.kind, str) or not self.kind.strip():
            raise SimulationValidationError("entity kind cannot be empty")
        _validate_json_object(self.state, "entity state")


@dataclass(frozen=True, slots=True)
class SimulationEvent:
    event_id: str
    tick: int
    kind: str
    target_id: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not isinstance(self.event_id, str) or not self.event_id.strip():
            raise SimulationValidationError("event_id cannot be empty")
        if not isinstance(self.tick, int) or isinstance(self.tick, bool) or self.tick < 0:
            raise SimulationValidationError("event tick must be a non-negative integer")
        if not isinstance(self.kind, str) or not self.kind.strip():
            raise SimulationValidationError("event kind cannot be empty")
        if not isinstance(self.target_id, str) or not self.target_id.strip():
            raise SimulationValidationError("event target_id cannot be empty")
        _validate_json_object(self.payload, "event payload")


@dataclass(frozen=True, slots=True)
class SimulationSnapshot:
    tick: int
    state: Mapping[str, Any]
    state_hash: str

    @classmethod
    def create(cls, tick: int, state: Mapping[str, Any]) -> "SimulationSnapshot":
        frozen_state = _validated_json_object(state, "snapshot state")
        digest = hashlib.sha256(_canonical_json(frozen_state).encode("utf-8")).hexdigest()
        return cls(tick=tick, state=frozen_state, state_hash=digest)


@dataclass(frozen=True, slots=True)
class ReplayResult:
    snapshots: tuple[SimulationSnapshot, ...]
    final_state: Mapping[str, Any]
    receipt_hash: str

    @classmethod
    def create(
        cls,
        snapshots: tuple[SimulationSnapshot, ...],
        final_state: Mapping[str, Any],
    ) -> "ReplayResult":
        frozen_final_state = _validated_json_object(final_state, "final state")
        payload = {
            "snapshots": [
                {
                    "tick": snapshot.tick,
                    "state": snapshot.state,
                    "state_hash": snapshot.state_hash,
                }
                for snapshot in snapshots
            ],
            "final_state": frozen_final_state,
        }
        digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        return cls(
            snapshots=snapshots,
            final_state=frozen_final_state,
            receipt_hash=digest,
        )
