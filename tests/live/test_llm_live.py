"""Live LLM check — LOCAL ONLY (needs an Anthropic API key + network). Never run in CI.

Run with: ``pytest -m live tests/live/test_llm_live.py`` (requires ``ANTHROPIC_API_KEY`` set).
Confirms the real provider returns a non-empty single-line hypothesis from a tiny prompt.
"""

from __future__ import annotations

import pytest

from uta.config import get_settings
from uta.llm.claude import AnthropicHypothesisProvider
from uta.llm.prompt import build_prompt

pytestmark = pytest.mark.live


def test_live_real_provider_returns_hypothesis():
    settings = get_settings()
    if not settings.anthropic_api_key:
        pytest.skip("ANTHROPIC_API_KEY not configured")
    provider = AnthropicHypothesisProvider(settings.anthropic_api_key, model=settings.llm_model)
    system, user = build_prompt(
        test_id="ut_ar.arinv_csvc.test_reminder_fee",
        predicted_cause="CODE_CHANGE",
        error_details="AssertionError: expected fee 12.50, got 12.55",
        error_stack_trace="  File arinv_csvc.py, line 92, in test_reminder_fee",
        code_candidates=1,
        data_candidates=0,
        similar_cases=[],
    )
    hypothesis = provider.hypothesize(system=system, user=user)
    assert hypothesis is not None
    assert hypothesis.text.strip()
    assert hypothesis.provider == settings.llm_model
