from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


class SimulationValidationError(ValueError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _validate_json_object(value: Mapping[str, Any], field_name: str) -> None:
    try:
        encoded = _canonical_json(dict(value))
    except (TypeError, ValueError) as exc:
        raise SimulationValidationError(f"{field_name} must be JSON serializable") from exc
    if not encoded.startswith("{"):
        raise SimulationValidationError(f"{field_name} must be a JSON object")


@dataclass(frozen=True, slots=True)
class EntityBlueprint:
    entity_id: str
    kind: str
    state: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.entity_id.strip():
            raise SimulationValidationError("entity_id cannot be empty")
        if not self.kind.strip():
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
        if not self.event_id.strip():
            raise SimulationValidationError("event_id cannot be empty")
        if not isinstance(self.tick, int) or isinstance(self.tick, bool) or self.tick < 0:
            raise SimulationValidationError("event tick must be a non-negative integer")
        if not self.kind.strip():
            raise SimulationValidationError("event kind cannot be empty")
        if not self.target_id.strip():
            raise SimulationValidationError("event target_id cannot be empty")
        _validate_json_object(self.payload, "event payload")


@dataclass(frozen=True, slots=True)
class SimulationSnapshot:
    tick: int
    state: Mapping[str, Any]
    state_hash: str

    @classmethod
    def create(cls, tick: int, state: Mapping[str, Any]) -> "SimulationSnapshot":
        canonical = _canonical_json(state)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return cls(tick=tick, state=state, state_hash=digest)


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
        payload = {
            "snapshots": [asdict(snapshot) for snapshot in snapshots],
            "final_state": final_state,
        }
        digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        return cls(snapshots=snapshots, final_state=final_state, receipt_hash=digest)
