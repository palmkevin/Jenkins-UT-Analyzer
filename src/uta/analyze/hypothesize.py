"""LLM hypothesis step (Milestone 5) — the side-effecting wiring around the pure analysis.

Deterministic classification (``analyze/classify.py``) stays pure and offline; this step runs
**after** it, only for runs being analysed, and only when a real provider is supplied. It fills
``Classification.llm_hypothesis`` for each newly-opened episode from the top-k similar past cases
the knowledge base already retrieved (the "RAG"). With the default
:class:`~uta.llm.NoopHypothesisProvider` it is a no-op — no retrieval, no model call, no DB write —
so the offline gate and existing runs are untouched. Back-fill passes Noop; the poller passes the
real provider, mirroring the email side (history is never re-hypothesised, just as it is never
re-mailed).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from uta.analyze.relevance import rank_candidates
from uta.ingest.ut_report import FAILED_STATUSES
from uta.kb.retrieval import similar_cases
from uta.llm import HypothesisProvider, NoopHypothesisProvider
from uta.llm.prompt import build_prompt
from uta.models import Classification, FailureSignature, Run, TestIdentity, TestResult


def _failing_result_with_signature(
    session: Session, run: Run, identity_id: int
) -> TestResult | None:
    """The run's failing result for this test that carries a signature (the recurrence key)."""
    return session.scalar(
        select(TestResult)
        .where(
            TestResult.run_id == run.id,
            TestResult.test_identity_id == identity_id,
            TestResult.status.in_(FAILED_STATUSES),
            TestResult.signature_id.isnot(None),
        )
        .order_by(TestResult.id)
    )


def hypothesize_episode(
    session: Session,
    run: Run,
    identity_id: int,
    episode_id: int,
    provider: HypothesisProvider,
    *,
    top_k: int,
    cutoff: float,
) -> bool:
    """Generate + persist the hypothesis for one new episode. Returns whether a value was set."""
    classification = session.scalar(
        select(Classification).where(Classification.episode_id == episode_id)
    )
    if classification is None:
        return False

    result = _failing_result_with_signature(session, run, identity_id)
    if result is None:
        return False
    sig = session.get(FailureSignature, result.signature_id)
    if sig is None:
        return False

    cases = similar_cases(
        session,
        sig.normalized_text,
        k=top_k,
        cutoff=cutoff,
        exclude_signature_id=sig.id,
    )
    identity = session.get(TestIdentity, identity_id)
    # Rank the run's change candidates against *this* failure so the prompt can lead with the
    # likely culprit (author/path/entity + match reason) instead of bare counts (issue #50).
    ranked = rank_candidates(
        run.code_changes,
        run.data_changes,
        file_path=result.file_path,
        error_details=result.error_details,
        error_stack_trace=result.error_stack_trace,
        class_name=identity.class_name if identity else None,
    )
    system, user = build_prompt(
        test_id=identity.canonical_name if identity else str(identity_id),
        predicted_cause=classification.predicted_cause,
        error_details=result.error_details,
        error_stack_trace=result.error_stack_trace,
        code_candidates=ranked.code,
        data_candidates=ranked.data,
        similar_cases=cases,
    )
    hypothesis = provider.hypothesize(system=system, user=user)
    if hypothesis is None:
        return False
    classification.llm_hypothesis = hypothesis.text
    return True


def hypothesize_run(
    session: Session,
    run: Run,
    opened_episodes: list[tuple[int, int]],
    provider: HypothesisProvider,
    *,
    top_k: int = 5,
    cutoff: float = 0.3,
) -> int:
    """Hypothesise every episode this run newly opened. No-op under Noop. Returns count written."""
    if isinstance(provider, NoopHypothesisProvider):
        return 0
    written = 0
    for identity_id, episode_id in opened_episodes:
        if hypothesize_episode(
            session, run, identity_id, episode_id, provider, top_k=top_k, cutoff=cutoff
        ):
            written += 1
    return written
