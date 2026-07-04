"""LLM hypothesis provider.

A failing test's *predicted cause* is derived deterministically (``analyze/classify.py``); the LLM
adds a **human-readable hypothesis** — one sentence naming the most likely root cause — grounded in
the top-k similar past cases the knowledge base already retrieves (``kb/retrieval.py``). That is the
whole "RAG": fetch the similar cases, render them into a prompt, ask the model. **No vector store**
— retrieval is the existing ``pg_trgm`` / difflib similarity.

The model call sits behind :class:`HypothesisProvider` so the offline gate drives a fake and never
touches the network. :class:`NoopHypothesisProvider` is the **default**: with no API key configured,
ingest behaves exactly as before (``Classification.llm_hypothesis`` stays ``NULL``). The real
provider lives in :mod:`uta.llm.claude`; prompt assembly lives in :mod:`uta.llm.prompt`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Hypothesis:
    text: str
    provider: str


class HypothesisProvider(Protocol):
    def hypothesize(self, *, system: str, user: str) -> Hypothesis | None: ...


class NoopHypothesisProvider:
    """Default provider: returns nothing. Active whenever no LLM API key is configured."""

    def hypothesize(self, *, system: str, user: str) -> Hypothesis | None:
        return None
