from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


class SceneValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Transform:
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0

    def validate(self) -> None:
        values = (self.x, self.y, self.rotation, self.scale_x, self.scale_y)
        if not all(isinstance(value, (int, float)) for value in values):
            raise SceneValidationError("transform values must be numeric")
        if self.scale_x == 0 or self.scale_y == 0:
            raise SceneValidationError("scene node scale cannot be zero")


@dataclass(frozen=True, slots=True)
class SceneNode:
    node_id: str
    kind: str
    transform: Transform = field(default_factory=Transform)
    layer: int = 0
    visible: bool = True
    props: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.node_id.strip():
            raise SceneValidationError("node_id cannot be empty")
        if not self.kind.strip():
            raise SceneValidationError("kind cannot be empty")
        self.transform.validate()
        try:
            json.dumps(dict(self.props), sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise SceneValidationError("node props must be JSON serializable") from exc


@dataclass(frozen=True, slots=True)
class Scene:
    scene_id: str
    title: str
    width: int = 1280
    height: int = 720
    background: str = "#07080d"
    nodes: tuple[SceneNode, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.scene_id.strip():
            raise SceneValidationError("scene_id cannot be empty")
        if not self.title.strip():
            raise SceneValidationError("scene title cannot be empty")
        if self.width <= 0 or self.height <= 0:
            raise SceneValidationError("scene dimensions must be positive")
        seen: set[str] = set()
        for node in self.nodes:
            node.validate()
            if node.node_id in seen:
                raise SceneValidationError(f"duplicate node_id: {node.node_id}")
            seen.add(node.node_id)
        try:
            json.dumps(dict(self.metadata), sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise SceneValidationError("scene metadata must be JSON serializable") from exc

    def canonical_dict(self) -> dict[str, Any]:
        self.validate()
        payload = asdict(self)
        payload["nodes"] = sorted(payload["nodes"], key=lambda node: (node["layer"], node["node_id"]))
        return payload

    def canonical_json(self) -> str:
        return json.dumps(self.canonical_dict(), sort_keys=True, separators=(",", ":"))

    def receipt_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


BIRD_ARCHETYPES: tuple[str, ...] = (
    "duck",
    "goose",
    "raven",
    "gobble",
    "pheasant",
    "brother_ape",
    "owl",
    "penguin",
    "eagle",
    "parrot",
    "swan",
    "rooster",
    "bat",
    "hummingbird",
    "dodo",
    "paracletheon",
)
