from __future__ import annotations

from dataclasses import dataclass

from aviary.simulation.chronicle import Chronicle
from aviary.simulation.contracts import (
    EntityBlueprint,
    ReplayResult,
    SimulationValidationError,
    _validated_json_object,
)
from aviary.simulation.fossil import Fossil
from aviary.simulation.kernel import DeterministicSimulation


@dataclass(frozen=True, slots=True)
class Archive:
    """Replay, inspect, and fork one deterministic simulation history."""

    blueprints: tuple[EntityBlueprint, ...]
    chronicle: Chronicle

    @classmethod
    def create(
        cls,
        blueprints: tuple[EntityBlueprint, ...],
        chronicle: Chronicle,
    ) -> "Archive":
        frozen_blueprints: list[EntityBlueprint] = []
        for blueprint in blueprints:
            if not isinstance(blueprint, EntityBlueprint):
                raise SimulationValidationError(
                    "archive blueprints must be EntityBlueprint instances"
                )
            blueprint.validate()
            frozen_blueprints.append(
                EntityBlueprint(
                    entity_id=blueprint.entity_id,
                    kind=blueprint.kind,
                    state=_validated_json_object(blueprint.state, "entity state"),
                )
            )
        if not isinstance(chronicle, Chronicle):
            raise SimulationValidationError("archive requires a Chronicle")
        return cls(tuple(frozen_blueprints), chronicle)

    def replay(
        self,
        until_tick: int | None = None,
        simulation: DeterministicSimulation | None = None,
    ) -> ReplayResult:
        engine = simulation or DeterministicSimulation()
        events = self.chronicle.entries
        if until_tick is not None:
            events = self.chronicle.through(until_tick).entries
        return engine.replay(self.blueprints, events, until_tick=until_tick)

    def rewind(self, tick: int) -> ReplayResult:
        return self.replay(until_tick=tick)

    def fossil(self, tick: int, name: str) -> Fossil:
        snapshot = self.rewind(tick).snapshots[-1]
        return Fossil.create(name=name, tick=snapshot.tick, state=snapshot.state)

    def fork(self, tick: int) -> "Archive":
        return Archive.create(self.blueprints, self.chronicle.through(tick))
