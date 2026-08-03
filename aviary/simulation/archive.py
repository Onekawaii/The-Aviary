from __future__ import annotations

from dataclasses import dataclass

from aviary.simulation.chronicle import Chronicle
from aviary.simulation.contracts import EntityBlueprint, ReplayResult, SimulationValidationError
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
        for blueprint in blueprints:
            if not isinstance(blueprint, EntityBlueprint):
                raise SimulationValidationError(
                    "archive blueprints must be EntityBlueprint instances"
                )
            blueprint.validate()
        if not isinstance(chronicle, Chronicle):
            raise SimulationValidationError("archive requires a Chronicle")
        return cls(tuple(blueprints), chronicle)

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
        result = self.rewind(tick)
        return Fossil(name=name, snapshot=result.snapshots[-1])

    def fork(self, tick: int) -> "Archive":
        return Archive.create(self.blueprints, self.chronicle.through(tick))
