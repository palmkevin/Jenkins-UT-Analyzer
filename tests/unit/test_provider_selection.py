"""Provider selection for the LLM hypothesis (Milestone 5) — offline, constructs no network call.

Building a provider only instantiates the SDK client (no request), so these run on the offline gate.
"""

from __future__ import annotations

from uta.cli import _build_hypothesis_provider
from uta.config import Settings


def _name(**kw) -> str:
    # Explicit kwargs override any env/.env, so the selection is hermetic.
    base = dict(anthropic_api_key="", openai_api_key="", llm_provider="")
    base.update(kw)
    return type(_build_hypothesis_provider(Settings(**base))).__name__


def test_no_keys_is_noop():
    assert _name() == "NoopHypothesisProvider"


def test_anthropic_key_autoselects_anthropic():
    assert _name(anthropic_api_key="sk-a") == "AnthropicHypothesisProvider"


def test_openai_key_autoselects_openai():
    assert _name(openai_api_key="sk-o") == "OpenAIHypothesisProvider"


def test_both_keys_prefer_anthropic():
    assert _name(anthropic_api_key="sk-a", openai_api_key="sk-o") == "AnthropicHypothesisProvider"


def test_explicit_provider_overrides_autoselect():
    assert (
        _name(llm_provider="openai", anthropic_api_key="sk-a", openai_api_key="sk-o")
        == "OpenAIHypothesisProvider"
    )


def test_explicit_provider_without_key_is_noop():
    assert _name(llm_provider="openai") == "NoopHypothesisProvider"
