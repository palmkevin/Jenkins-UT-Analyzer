"""LLM hypothesis provider — stubbed (no-op) in v1 behind a swappable interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Hypothesis:
    text: str
    provider: str


class HypothesisProvider(Protocol):
    def hypothesize(self, *, error_details: str | None, context: str) -> Hypothesis | None: ...


class NoopHypothesisProvider:
    """v1 default: returns nothing. Milestone 5 swaps in a real provider + RAG."""

    def hypothesize(self, *, error_details: str | None, context: str) -> Hypothesis | None:
        return None
