"""Prompt assembly for the LLM hypothesis (Milestone 5) — pure, fully offline-testable.

This is the "augmented" half of retrieval-augmented generation: it renders the current failure plus
the deterministic prior (predicted cause + change-signal counts) and the top-k **similar past
cases** the knowledge base already retrieved into a compact ``(system, user)`` pair. The model is
asked for a single sentence; the deterministic ``predicted_cause`` already carries the label, so the
hypothesis is the *human-readable* "why".

Medical-data invariant: only already-redacted/normalized fields reach the prompt — the failure's
error text/stack (committed fixtures are redacted) and the similar cases' *attribution* fields
(human-entered reasons / author initials). Raw ``MODDATA`` is never selected, so it cannot leak
here. Error text and stack are length-capped so a pathological trace can't blow the token budget.
"""

from __future__ import annotations

from collections.abc import Sequence

from uta.kb.retrieval import SimilarCase

_MAX_ERROR_CHARS = 2000
_MAX_STACK_CHARS = 2000

SYSTEM_PROMPT = (
    "You triage failing nightly unit tests for a laboratory information management system (LIMS). "
    "You are given one failing test, a deterministic predicted cause derived from the change "
    "signals in the run window, and similar past failures with any validated human conclusions. "
    "Reply with ONE concise sentence naming the most likely root cause and, if the evidence "
    "supports it, who or what to look at. Prefer a validated past conclusion when the current "
    "error closely matches it. Do not restate the error verbatim, do not speculate beyond it, "
    "and do not add preamble — return only the sentence."
)


def _truncate(text: str | None, limit: int) -> str:
    if not text:
        return "(none)"
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + " …[truncated]"


def _render_cases(cases: Sequence[SimilarCase]) -> str:
    if not cases:
        return "(no similar past cases on record)"
    lines: list[str] = []
    for i, c in enumerate(cases, start=1):
        conclusion = c.reason_text or "(no recorded conclusion)"
        who = f", attributed to {c.causing_person}" if c.causing_person else ""
        prov = f" [{c.provenance}]" if c.provenance else ""
        lines.append(
            f"{i}. {c.test_id} (similarity {c.similarity:.2f}, seen {c.occurrence_count}x"
            f"{', ' + c.exception_type if c.exception_type else ''}): "
            f"{conclusion}{who}{prov}"
        )
    return "\n".join(lines)


def build_prompt(
    *,
    test_id: str,
    predicted_cause: str | None,
    error_details: str | None,
    error_stack_trace: str | None,
    code_candidates: int,
    data_candidates: int,
    similar_cases: Sequence[SimilarCase],
) -> tuple[str, str]:
    """Build the ``(system, user)`` prompt for one failing test. Deterministic — no I/O."""
    user = (
        f"Failing test: {test_id}\n"
        f"Deterministic predicted cause: {predicted_cause or 'UNKNOWN'}\n"
        f"Change signals in window: {code_candidates} code change(s), "
        f"{data_candidates} reference-data change(s)\n\n"
        f"Error:\n{_truncate(error_details, _MAX_ERROR_CHARS)}\n\n"
        f"Stack trace:\n{_truncate(error_stack_trace, _MAX_STACK_CHARS)}\n\n"
        f"Similar past cases (most similar first):\n{_render_cases(similar_cases)}\n\n"
        "Give the single-sentence hypothesis."
    )
    return SYSTEM_PROMPT, user
