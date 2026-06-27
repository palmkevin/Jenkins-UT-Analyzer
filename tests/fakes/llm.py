"""A fake hypothesis provider — returns a canned answer, no network (offline gate)."""

from __future__ import annotations

from uta.llm import Hypothesis


class StubHypothesisProvider:
    """Implements :class:`~uta.llm.HypothesisProvider`; records prompts and returns a fixed text.

    Pass ``text=None`` to simulate a provider that declines / fails (the hypothesis is then skipped
    and ``llm_hypothesis`` is left NULL).
    """

    def __init__(
        self, text: str | None = "Likely caused by the trunk commit in the window."
    ) -> None:
        self._text = text
        self.calls: list[tuple[str, str]] = []

    def hypothesize(self, *, system: str, user: str) -> Hypothesis | None:
        self.calls.append((system, user))
        if self._text is None:
            return None
        return Hypothesis(text=self._text, provider="stub")
