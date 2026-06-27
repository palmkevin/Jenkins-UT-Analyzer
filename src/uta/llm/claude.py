"""Real LLM provider — Anthropic Claude (Milestone 5).

Implements :class:`~uta.llm.HypothesisProvider` with the official ``anthropic`` SDK. One short,
non-streaming message per failing test (the output is a single sentence). The ``anthropic`` import
is **local to this module** so the default offline path never imports the SDK, and any API failure
returns ``None`` — a missing hypothesis must never break ingest. Named ``claude`` rather than
``anthropic`` so it does not shadow the SDK package.

Configured from ``ANTHROPIC_API_KEY`` (Developer Console / pay-as-you-go billing — separate from
any Claude Code or Claude.ai subscription). Default model ``claude-opus-4-8``; override via
``LLM_MODEL``. This provider is exercised only by ``live``-marked tests, never in CI.
"""

from __future__ import annotations

import logging

from uta.llm import Hypothesis

_log = logging.getLogger(__name__)

_MAX_TOKENS = 512


class AnthropicHypothesisProvider:
    """Single-shot root-cause hypothesis via the Claude Messages API."""

    def __init__(self, api_key: str, model: str = "claude-opus-4-8") -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def hypothesize(self, *, system: str, user: str) -> Hypothesis | None:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=_MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception:  # noqa: BLE001 — enrichment is best-effort; never break ingest
            _log.warning("LLM hypothesis request failed; skipping", exc_info=True)
            return None

        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip()
        if not text:
            return None
        return Hypothesis(text=text, provider=self._model)
