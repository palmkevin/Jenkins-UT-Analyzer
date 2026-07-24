"""Prompt assembly for the LLM hypothesis — pure, fully offline-testable.

This is the "augmented" half of retrieval-augmented generation: it renders the current failure plus
the deterministic prior (predicted cause + the change candidates **ranked by relevance to this
test**, issue #50) and the top-k **similar past cases** the knowledge base already retrieved into a
compact ``(system, user)`` pair. The model is asked for a single sentence; the deterministic
``predicted_cause`` already carries the label, so the hypothesis is the *human-readable* "why" —
and with the top candidates' author/path/entity in hand it can name a concrete suspect.

Medical-data invariant: only already-redacted/normalized fields reach the prompt — the failure's
error text/stack (committed fixtures are redacted), the similar cases' *attribution* fields
(human-entered reasons / author initials), and the candidates' key/author fields (commit id,
author, message, changed paths; entity table code, change type, component, user code). Raw
``MODDATA`` is never selected or persisted upstream, so it cannot leak here. Error text, stack and
commit messages are length-capped so a pathological input can't blow the token budget.
"""

from __future__ import annotations

from collections.abc import Sequence

from uta.analyze.relevance import RankedCodeChange, RankedDataChange
from uta.kb.retrieval import SimilarCase

_MAX_ERROR_CHARS = 2000
_MAX_STACK_CHARS = 2000
_MAX_MESSAGE_CHARS = 200
# Top-N candidates of each kind rendered in detail; the rest stay a count.
_MAX_CANDIDATES = 3

SYSTEM_PROMPT = (
    "You triage failing unit tests for a laboratory information management system (LIMS). "
    "You are given one failing test, a deterministic predicted cause, the candidate code commits "
    "and reference-data changes in the build window ranked by relevance to this test (with the "
    "match reason), and similar past failures with any validated human conclusions. "
    "Reply with ONE concise sentence naming the most likely root cause and, if the evidence "
    "supports it, the specific commit, change or person to look at. Prefer a validated past "
    "conclusion when the current error closely matches it; prefer candidates whose match reason "
    "ties them to this test. Do not restate the error verbatim, do not speculate beyond the "
    "evidence, and do not add preamble — return only the sentence."
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


def _match_note(reasons: tuple[str, ...]) -> str:
    return f" [{'; '.join(reasons)}]" if reasons else " [no direct match to this test]"


def _render_code(candidates: Sequence[RankedCodeChange]) -> str:
    if not candidates:
        return "(none)"
    lines = [
        f"{i}. revision {c.revision or '?'} by {c.author or 'unknown'}: "
        f'"{_truncate(c.message, _MAX_MESSAGE_CHARS)}"{_match_note(c.reasons)}'
        for i, c in enumerate(candidates[:_MAX_CANDIDATES], start=1)
    ]
    if len(candidates) > _MAX_CANDIDATES:
        lines.append(f"(+{len(candidates) - _MAX_CANDIDATES} less relevant, omitted)")
    return "\n".join(lines)


def _render_data(candidates: Sequence[RankedDataChange]) -> str:
    if not candidates:
        return "(none)"
    lines = []
    for i, d in enumerate(candidates[:_MAX_CANDIDATES], start=1):
        pk = f" pk {d.pk}" if d.pk else ""
        comp = f" via {d.component}" if d.component else ""
        lines.append(
            f"{i}. {d.entity}{pk} ({d.change_type}) by {d.author or 'unknown'}"
            f"{comp}{_match_note(d.reasons)}"
        )
    if len(candidates) > _MAX_CANDIDATES:
        lines.append(f"(+{len(candidates) - _MAX_CANDIDATES} less relevant, omitted)")
    return "\n".join(lines)


def build_prompt(
    *,
    test_id: str,
    predicted_cause: str | None,
    error_details: str | None,
    error_stack_trace: str | None,
    code_candidates: Sequence[RankedCodeChange] = (),
    data_candidates: Sequence[RankedDataChange] = (),
    similar_cases: Sequence[SimilarCase] = (),
) -> tuple[str, str]:
    """Build the ``(system, user)`` prompt for one failing test. Deterministic — no I/O.

    ``code_candidates`` / ``data_candidates`` are the build's change candidates already ranked
    against this test (:func:`uta.analyze.relevance.rank_candidates`); the top
    :data:`_MAX_CANDIDATES` of each kind are rendered in detail with their match reason.
    """
    user = (
        f"Failing test: {test_id}\n"
        f"Deterministic predicted cause: {predicted_cause or 'UNKNOWN'}\n"
        f"Change signals in window: {len(code_candidates)} code change(s), "
        f"{len(data_candidates)} reference-data change(s)\n\n"
        f"Candidate code changes (most relevant to this test first):\n"
        f"{_render_code(code_candidates)}\n\n"
        f"Candidate reference-data changes (most relevant to this test first):\n"
        f"{_render_data(data_candidates)}\n\n"
        f"Error:\n{_truncate(error_details, _MAX_ERROR_CHARS)}\n\n"
        f"Stack trace:\n{_truncate(error_stack_trace, _MAX_STACK_CHARS)}\n\n"
        f"Similar past cases (most similar first):\n{_render_cases(similar_cases)}\n\n"
        "Give the single-sentence hypothesis."
    )
    return SYSTEM_PROMPT, user
