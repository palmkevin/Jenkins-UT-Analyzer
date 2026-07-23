"""LLM hypothesis wiring (Milestone 5) — the side-effecting step around the pure analysis.

Drives a fake provider so the offline gate never touches the network. Verifies: Noop is a no-op,
a real provider fills ``llm_hypothesis`` on the right episode, a declining provider leaves it NULL,
the retrieved similar cases reach the prompt, and the column the deterministic classifier set is
preserved.
"""

from __future__ import annotations

from sqlalchemy import select

from tests.builders import get_identity, make_build
from tests.fakes.llm import StubHypothesisProvider
from uta.analyze.hypothesize import hypothesize_build
from uta.kb.store import record_signatures_for_build
from uta.llm import NoopHypothesisProvider
from uta.models import Classification, FailureEpisode

_STACK = (
    "Traceback (most recent call last):\n"
    '  File "/opt/ls/lx/release/permanent/tests/dev/ut_ar/arinv_csvc.py", line {line}, in test_x\n'
    "    self.assertEqual(a, b)\n"
    "AssertionError: {msg}\n"
)
T = "ut_ar.arinv_csvc.test_x"


def _setup_episode(session, build=1, name=T, cause="CODE_CHANGE"):
    """A failing build with a signature, plus an open episode + its deterministic classification."""
    build = make_build(
        session,
        build,
        {name: "FAILED"},
        errors={name: ("boom", _STACK.format(line=92, msg="1 != 2"))},
    )
    record_signatures_for_build(session, build)
    ident = get_identity(session, name)
    ep = FailureEpisode(
        test_identity_id=ident.id,
        episode_number=1,
        first_failure_build_id=build.id,
        first_failure_at=build.started_at,
    )
    session.add(ep)
    session.flush()
    classification = Classification(episode_id=ep.id, predicted_cause=cause)
    session.add(classification)
    session.flush()
    return build, ident, ep, classification


def test_real_provider_fills_hypothesis(session_factory):
    with session_factory() as s:
        build, ident, ep, classification = _setup_episode(s)
        provider = StubHypothesisProvider(text="Off-by-one introduced by the trunk commit.")
        written = hypothesize_build(s, build, [(ident.id, ep.id)], provider, top_k=5, cutoff=0.3)
        assert written == 1
        assert classification.llm_hypothesis == "Off-by-one introduced by the trunk commit."
        # The prompt actually carried the failing test and its deterministic cause.
        assert provider.calls, "provider should have been called"
        _system, user = provider.calls[0]
        assert T in user
        assert "CODE_CHANGE" in user


def test_noop_provider_writes_nothing(session_factory):
    with session_factory() as s:
        build, ident, ep, classification = _setup_episode(s)
        written = hypothesize_build(s, build, [(ident.id, ep.id)], NoopHypothesisProvider())
        assert written == 0
        assert classification.llm_hypothesis is None


def test_declining_provider_leaves_null(session_factory):
    with session_factory() as s:
        build, ident, ep, classification = _setup_episode(s)
        provider = StubHypothesisProvider(text=None)  # provider returns no hypothesis
        written = hypothesize_build(s, build, [(ident.id, ep.id)], provider)
        assert written == 0
        assert classification.llm_hypothesis is None


def test_ranked_candidate_details_reach_the_prompt(session_factory):
    """The build's candidates are ranked against the failure and their details (author, path,
    match reason) appear in the prompt instead of bare counts (issue #50)."""
    from datetime import UTC, datetime

    from uta.models import CodeChangeCandidate

    with session_factory() as s:
        build, ident, ep, _ = _setup_episode(s)
        build.code_changes.append(
            CodeChangeCandidate(
                commit_id="135200",
                revision="135200",
                author="R. Devlin",
                message="rework reminder fees",
                committed_at=datetime(2026, 6, 1, tzinfo=UTC),
                paths='[{"editType": "edit", "file": "/trunk/lx/ut_ar/arinv_csvc.py"}]',
            )
        )
        s.flush()
        provider = StubHypothesisProvider()
        hypothesize_build(s, build, [(ident.id, ep.id)], provider, top_k=5, cutoff=0.3)
        _system, user = provider.calls[0]
        assert "135200" in user and "R. Devlin" in user and "rework reminder fees" in user
        # The commit touches the failing test's module, so the match reason is spelled out.
        assert "matches the failing test's module" in user


def test_similar_cases_reach_the_prompt(session_factory):
    """A prior failure with a validated reason should be retrieved into the hypothesis prompt."""
    from uta.models import Attribution, FailureSignature
    from uta.models.enums import Provenance

    with session_factory() as s:
        # A past, near-identical failure on a different test, with a human-entered conclusion.
        past = make_build(
            s,
            1,
            {"ut_ar.arinv_csvc.test_y": "FAILED"},
            errors={"ut_ar.arinv_csvc.test_y": ("boom", _STACK.format(line=99, msg="1 != 2"))},
        )
        record_signatures_for_build(s, past)
        past_sig = s.scalar(
            select(FailureSignature).where(
                FailureSignature.test_identity_id == get_identity(s, "ut_ar.arinv_csvc.test_y").id
            )
        )
        s.add(
            Attribution(
                episode_id=999,
                signature_id=past_sig.id,
                reason_text="reminder-fee rounding bug",
                causing_person="ako",
                reason_provenance=Provenance.HUMAN_ENTERED,
            )
        )
        # The current failure under triage.
        build, ident, ep, _ = _setup_episode(s, build=2)
        provider = StubHypothesisProvider()
        hypothesize_build(s, build, [(ident.id, ep.id)], provider, top_k=5, cutoff=0.1)
        _system, user = provider.calls[0]
        assert "reminder-fee rounding bug" in user
        assert "attributed to ako" in user
