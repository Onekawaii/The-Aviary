from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

@dataclass(frozen=True, slots=True)
class Topic:
    text: str
    context: Mapping[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class BirdMetadata:
    bird_id: str
    name: str
    version: str
    role: str
    priority: int = 100
    deterministic: bool = True

@dataclass(frozen=True, slots=True)
class BirdOpinion:
    bird_id: str
    summary: str
    observations: tuple[str, ...]
    recommendations: tuple[str, ...]
    risks: tuple[str, ...] = ()
    confidence: float = 0.5
    data: Mapping[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")

@dataclass(frozen=True, slots=True)
class CouncilDecision:
    title: str
    synthesis: str
    actions: tuple[str, ...]
    risks: tuple[str, ...]
    confidence: float

class Bird(ABC):
    @abstractmethod
    def analyze(self, topic: Topic) -> BirdOpinion: ...
    @abstractmethod
    def metadata(self) -> BirdMetadata: ...
    @abstractmethod
    def voice(self) -> str: ...
    @abstractmethod
    def schema(self) -> Mapping[str, Any]: ...

class CouncilStrategy(ABC):
    @abstractmethod
    def aggregate(self, topic: Topic, opinions: Sequence[BirdOpinion]) -> CouncilDecision: ...
