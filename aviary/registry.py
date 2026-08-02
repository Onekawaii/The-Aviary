from __future__ import annotations

import importlib
import inspect
import pkgutil
from dataclasses import dataclass
from typing import Iterable

from aviary.contracts import Bird


@dataclass(frozen=True, slots=True)
class LoadedBird:
    bird_id: str
    module: str
    instance: Bird


class BirdRegistry:
    def __init__(self):
        self._birds: dict[str, LoadedBird] = {}

    def discover(self, package_name: str = "aviary.birds") -> None:
        package = importlib.import_module(package_name)
        for info in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
            if info.name.rsplit(".", 1)[-1].startswith("_"):
                continue
            module = importlib.import_module(info.name)
            candidates = [
                obj
                for _, obj in inspect.getmembers(module, inspect.isclass)
                if issubclass(obj, Bird)
                and obj is not Bird
                and obj.__module__ == module.__name__
            ]
            for cls in candidates:
                self.register(cls(), module.__name__)

    def register(self, bird: Bird, module: str) -> None:
        meta = bird.metadata()
        if not meta.bird_id or meta.bird_id in self._birds:
            raise ValueError(f"invalid or duplicate bird id: {meta.bird_id}")
        if not bird.voice().strip():
            raise ValueError(f"bird {meta.bird_id} has empty voice")
        schema = bird.schema()
        if not isinstance(schema, dict) or schema.get("type") != "object":
            raise ValueError(f"bird {meta.bird_id} has invalid schema")
        self._birds[meta.bird_id] = LoadedBird(meta.bird_id, module, bird)

    def retain(self, bird_ids: Iterable[str]) -> None:
        allowed = set(bird_ids)
        self._birds = {
            bird_id: loaded
            for bird_id, loaded in self._birds.items()
            if bird_id in allowed
        }

    def all(self) -> tuple[LoadedBird, ...]:
        return tuple(
            sorted(self._birds.values(), key=lambda b: b.instance.metadata().priority)
        )

    def ids(self) -> tuple[str, ...]:
        return tuple(b.bird_id for b in self.all())
