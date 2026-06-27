"""Real LLM provider — OpenAI (Milestone 5, alternate to Anthropic).

Implements :class:`~uta.llm.HypothesisProvider` with the official ``openai`` SDK (chat completions).
Symmetric to :mod:`uta.llm.claude`: one short, non-streaming call per failing test, the ``openai``
import is **local to this module** so the default offline path never loads the SDK, and any API
failure returns ``None`` (a missing hypothesis must never break ingest). Named ``openai_provider``
so it does not shadow the ``openai`` package.

Configured from ``OPENAI_API_KEY`` — an OpenAI **Platform** key (platform.openai.com, pay-as-you-go
billing), which is **separate from a ChatGPT subscription**. Default model ``gpt-4o``; override via
``OPENAI_MODEL``. This provider is exercised only by ``live``-marked tests, never in CI.
"""

from __future__ import annotations

import logging

from uta.llm import Hypothesis

_log = logging.getLogger(__name__)

_MAX_TOKENS = 512


class OpenAIHypothesisProvider:
    """Single-shot root-cause hypothesis via the OpenAI Chat Completions API."""

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def hypothesize(self, *, system: str, user: str) -> Hypothesis | None:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                max_tokens=_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except Exception:  # noqa: BLE001 — enrichment is best-effort; never break ingest
            _log.warning("OpenAI hypothesis request failed; skipping", exc_info=True)
            return None

        choices = response.choices or []
        text = (choices[0].message.content or "").strip() if choices else ""
        if not text:
            return None
        return Hypothesis(text=text, provider=self._model)
