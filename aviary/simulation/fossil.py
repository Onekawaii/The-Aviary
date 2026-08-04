from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any

from aviary.simulation.contracts import SimulationSnapshot


@dataclass(frozen=True, slots=True)
class Fossil:
    """Named immutable checkpoint derived from a simulation snapshot."""

    name: str
    snapshot: SimulationSnapshot

    @classmethod
    def create(cls, name: str, tick: int, state: Mapping[str, Any]) -> "Fossil":
        if not isinstance(name, str) or not name.strip():
            raise ValueError("fossil name cannot be empty")
        return cls(name=name.strip(), snapshot=SimulationSnapshot.create(tick, state))

    @property
    def tick(self) -> int:
        return self.snapshot.tick

    @property
    def state_hash(self) -> str:
        return self.snapshot.state_hash

    @property
    def state(self) -> Mapping[str, Any]:
        return self.snapshot.state

    def verify(self) -> bool:
        rebuilt = SimulationSnapshot.create(self.tick, self.state)
        return rebuilt.state_hash == self.state_hash
