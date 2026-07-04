"""Slice-0 ingest pipeline against an in-memory SQLite DB (offline, no Postgres)."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select

from tests.fakes import FakeJenkinsClient, FakeTrackingFeed
from tests.fakes.email import RecordingEmailSender
from uta.db import session_scope
from uta.ingest.pipeline import _dedupe_cases, data_change_window, ingest_build
from uta.ingest.ut_report import FAILED_STATUSES, TestCaseResult
from uta.models import (
    Classification,
    CodeChangeCandidate,
    DataChangeCandidate,
    FailureEpisode,
    FailureSignature,
    Run,
    TestIdentity,
    TestLifecycle,
    TestResult,
)
from uta.models.enums import LifecycleState, PredictedCause


def test_ingest_persists_run_and_results(session_factory):
    ingest_build(FakeJenkinsClient(), session_factory, 1702, expected_shards=2)
    with session_scope(session_factory) as s:
        run = s.scalar(select(Run).where(Run.build_number == 1702))
        assert run is not None
        assert run.complete is True
        # Fixture has 14 cases across both tracks.
        n = s.scalar(select(func.count()).select_from(TestResult))
        assert n == 14
        tracks = set(s.scalars(select(TestResult.track)).all())
        assert tracks == {"permanent", "permanent_py39"}


def test_unittest_logs_off_by_default(session_factory):
    """Without opt-in, ingest is the devUTs-only path — no console-log results leak in."""
    ingest_build(FakeJenkinsClient(), session_factory, 1702)
    with session_scope(session_factory) as s:
        assert s.scalar(select(func.count()).select_from(TestResult)) == 14  # JUnit only
        smb = s.scalars(
            select(func.count())
            .select_from(TestIdentity)
            .where(TestIdentity.canonical_name.like("smb.transform.%"))
        ).one()
        assert smb == 0


def test_ingest_unittest_logs_adds_console_log_results(session_factory):
    """Opting in pulls the SMB Transform console-log stages into the same per-(test, track) path."""
    ingest_build(
        FakeJenkinsClient(),
        session_factory,
        1702,
        ingest_unittest_logs=True,
        unittest_suites={"SMB Transform"},
    )
    with session_scope(session_factory) as s:
        # 14 devUTs + 4 (perm) + 4 (py39) console-log cases.
        assert s.scalar(select(func.count()).select_from(TestResult)) == 22
        smb = s.scalars(
            select(TestResult)
            .join(TestResult.identity)
            .where(TestIdentity.canonical_name.like("smb.transform.%"))
        ).all()
        assert len(smb) == 8
        assert {r.track for r in smb} == {"permanent", "permanent_py39"}

        # The two console-log failures (py39) open episodes and get classified like JUnit failures.
        failing = s.scalars(
            select(TestLifecycle)
            .join(TestLifecycle.identity)
            .where(TestIdentity.canonical_name.like("smb.transform.%"))
        ).all()
        assert {lc.identity.canonical_name for lc in failing} == {
            "smb.transform.test_pricing.PricingTransformTest.test_round_half_even",
            "smb.transform.test_rates.RatesTransformTest.test_currency_conversion",
        }
        assert all(lc.state == LifecycleState.FAILING for lc in failing)
        # 7 devUTs episodes + 2 console-log episodes, all classified.
        assert s.scalar(select(func.count()).select_from(FailureEpisode)) == 9
        assert s.scalar(select(func.count()).select_from(Classification)) == 9


class _DescendingFakeJenkins(FakeJenkinsClient):
    """SMB Transform py39 stage (292) whose console text lives on a Shell Script step node (295).

    Mirrors the real job: the stage node's own log is empty, so ingest must descend via
    ``stage_describe`` to the step node, whose log is HTML-wrapped (Timestamper).
    """

    def stage_describe(self, build: int, node_id: str) -> dict:
        if node_id == "292":
            return {
                "id": "292",
                "stageFlowNodes": [{"id": "295", "name": "Shell Script", "status": "FAILED"}],
            }
        return super().stage_describe(build, node_id)


def test_ingest_descends_to_step_node_and_parses_html_log(session_factory):
    """The real flow: stage → Shell Script step node → HTML-wrapped log → the failure surfaces."""
    ingest_build(
        _DescendingFakeJenkins(),
        session_factory,
        1702,
        ingest_unittest_logs=True,
        unittest_suites={"SMB Transform"},
    )
    with session_scope(session_factory) as s:
        # py39 descended to step node 295 (1 failure); permanent fell back to stage node 274 (4).
        failing = s.scalars(
            select(TestLifecycle)
            .join(TestLifecycle.identity)
            .where(TestIdentity.canonical_name.like("ls.smb.tests.transform.%"))
        ).all()
        assert {lc.identity.canonical_name for lc in failing} == {
            "ls.smb.tests.transform.lx.cases.LXTransformTestCases.test_39_specbillgrpid_for_micb_elements"
        }
        assert all(lc.state == LifecycleState.FAILING for lc in failing)


def test_unittest_log_reingest_is_idempotent(session_factory):
    """Re-ingesting with the console-log stages on doesn't duplicate results or episodes."""
    for _ in range(2):
        ingest_build(
            FakeJenkinsClient(),
            session_factory,
            1702,
            ingest_unittest_logs=True,
            unittest_suites={"SMB Transform"},
        )
    with session_scope(session_factory) as s:
        assert s.scalar(select(func.count()).select_from(TestResult)) == 22
        assert s.scalar(select(func.count()).select_from(FailureEpisode)) == 9


def test_reingest_is_idempotent(session_factory):
    ingest_build(FakeJenkinsClient(), session_factory, 1702)
    ingest_build(FakeJenkinsClient(), session_factory, 1702)
    with session_scope(session_factory) as s:
        assert s.scalar(select(func.count()).select_from(Run)) == 1
        assert s.scalar(select(func.count()).select_from(TestResult)) == 14  # not doubled
        # Lifecycle/episodes/classifications are not doubled either.
        assert s.scalar(select(func.count()).select_from(FailureEpisode)) == 7
        assert s.scalar(select(func.count()).select_from(Classification)) == 7


def test_ingest_drives_analysis_and_code_candidates(session_factory):
    ingest_build(FakeJenkinsClient(), session_factory, 1702)
    with session_scope(session_factory) as s:
        run = s.scalar(select(Run).where(Run.build_number == 1702))
        assert run.baseline_run_id is None  # first run — nothing to diff against
        # 7 distinct failing identities -> 7 open episodes, all FAILING, all classified.
        assert s.scalar(select(func.count()).select_from(TestLifecycle)) == 7
        states = set(s.scalars(select(TestLifecycle.state)).all())
        assert states == {LifecycleState.FAILING}
        assert s.scalar(select(func.count()).select_from(FailureEpisode)) == 7
        # The fixture carries one SVN commit and no data feed -> CODE_CHANGE.
        assert s.scalar(select(func.count()).select_from(CodeChangeCandidate)) == 1
        causes = set(s.scalars(select(Classification.predicted_cause)).all())
        assert causes == {PredictedCause.CODE_CHANGE}


def test_ingest_with_data_feed_persists_data_candidates(session_factory):
    ingest_build(FakeJenkinsClient(), session_factory, 1702, feed=FakeTrackingFeed())
    with session_scope(session_factory) as s:
        assert s.scalar(select(func.count()).select_from(DataChangeCandidate)) > 0
        # Both code and data candidates present -> ambiguous -> UNKNOWN (both attached as evidence).
        causes = set(s.scalars(select(Classification.predicted_cause)).all())
        assert causes == {PredictedCause.UNKNOWN}


def test_data_change_window_looks_back_with_tolerance():
    from datetime import UTC, datetime

    start = datetime(2026, 6, 26, 17, 0, tzinfo=UTC)
    end = datetime(2026, 6, 26, 19, 0, tzinfo=UTC)
    lo, hi = data_change_window(
        (start, end), lookback=timedelta(hours=12), tolerance=timedelta(minutes=5)
    )
    assert lo == start - timedelta(hours=12) - timedelta(minutes=5)
    assert hi == end + timedelta(minutes=5)


def test_ingest_records_failure_signatures(session_factory):
    """Every failing result gets a KB signature linked; re-ingest doesn't double-count."""
    ingest_build(FakeJenkinsClient(), session_factory, 1702)
    with session_scope(session_factory) as s:
        sigs = s.scalars(select(FailureSignature)).all()
        assert sigs  # signatures recorded
        # Every failing result is linked to a signature.
        failing = s.scalars(select(TestResult).where(TestResult.status.in_(FAILED_STATUSES))).all()
        assert failing and all(r.signature_id is not None for r in failing)
        before = {sig.id: sig.occurrence_count for sig in sigs}

    ingest_build(FakeJenkinsClient(), session_factory, 1702)  # re-ingest
    with session_scope(session_factory) as s:
        after = {sig.id: sig.occurrence_count for sig in s.scalars(select(FailureSignature)).all()}
        assert after == before  # recomputed from live links, not inflated


def test_ingest_emails_on_regression_only_via_sender(session_factory):
    """A sender + recipients ⇒ regression email; back-fill (no sender) stays silent."""
    sender = RecordingEmailSender()
    ingest_build(
        FakeJenkinsClient(),
        session_factory,
        1702,
        email_sender=sender,
        email_recipients=("team@example.com",),
    )
    # First run with failures vs an empty baseline ⇒ new failures ⇒ one email.
    assert len(sender.sent) == 1
    assert "new failing" in sender.sent[0].subject

    # Re-ingest with no sender (the back-fill path) sends nothing more.
    ingest_build(FakeJenkinsClient(), session_factory, 1702)
    assert len(sender.sent) == 1


def test_ingest_fills_llm_hypothesis_with_provider(session_factory):
    """A real provider fills the hypothesis for every newly-classified episode."""
    from tests.fakes.llm import StubHypothesisProvider

    ingest_build(
        FakeJenkinsClient(),
        session_factory,
        1702,
        hypothesis_provider=StubHypothesisProvider(text="trunk commit r123 broke this"),
    )
    with session_scope(session_factory) as s:
        hyps = s.scalars(select(Classification.llm_hypothesis)).all()
        assert len(hyps) == 7
        assert all(h == "trunk commit r123 broke this" for h in hyps)


def test_ingest_default_leaves_hypothesis_null(session_factory):
    """Default (no provider) ⇒ Noop ⇒ the column stays NULL, as before M5."""
    ingest_build(FakeJenkinsClient(), session_factory, 1702)
    with session_scope(session_factory) as s:
        hyps = s.scalars(select(Classification.llm_hypothesis)).all()
        assert hyps and all(h is None for h in hyps)


def _case(class_name: str, name: str, track: str, *, status: str = "PASSED", duration: float = 0.0):
    return TestCaseResult(
        track=track,
        suite_name="s",
        class_name=class_name,
        name=name,
        status=status,
        duration=duration,
        age=0,
        failed_since=0,
        error_details=None,
        error_stack_trace=None,
        file_path=None,
        line=None,
    )


def test_dedupe_cases_first_wins_within_track():
    """Two cases sharing (test_id, track) collapse to one — the first (authoritative JUnit) wins."""
    junit = _case("pkg.Cls", "test_a", "permanent_py39", status="REGRESSION", duration=1.5)
    console = _case("pkg.Cls", "test_a", "permanent_py39", status="FAILED", duration=0.0)
    other = _case("pkg.Cls", "test_b", "permanent_py39")
    deduped = _dedupe_cases([junit, console, other])
    assert len(deduped) == 2
    kept = next(c for c in deduped if c.name == "test_a")
    assert kept.status == "REGRESSION" and kept.duration == 1.5  # JUnit (first) kept, not console


def test_dedupe_cases_keeps_same_test_in_both_tracks():
    """The same test in different tracks is two distinct identities — never collapsed."""
    perm = _case("pkg.Cls", "test_a", "permanent")
    py39 = _case("pkg.Cls", "test_a", "permanent_py39")
    assert len(_dedupe_cases([perm, py39])) == 2


class _OverlappingFakeJenkins(FakeJenkinsClient):
    """A JUnit report that re-reports a test the SMB Transform console-log stage also emits (py39).

    Mirrors the real #1707 overlap: nose2 collects some of the same modules the console-log stages
    run, so both sources report the test in one build. The injected case carries a distinctive
    duration so the test can assert the JUnit copy (not the duration-0.0 console copy) survives.
    """

    def test_report(self, build: int) -> dict:
        report = super().test_report(build)
        report = {**report, "suites": [*report.get("suites", [])]}
        report["suites"].append(
            {
                "name": "overlap",
                "enclosingBlockNames": ["permanent_py39"],
                "cases": [
                    {
                        "className": "smb.transform.test_pricing.PricingTransformTest",
                        "name": "test_round_half_even",
                        "status": "REGRESSION",
                        "duration": 2.5,
                    }
                ],
            }
        )
        return report


def test_ingest_dedupes_junit_console_log_overlap(session_factory):
    """An overlapping (test_id, track) across the two sources must not break the constraint."""
    ingest_build(
        _OverlappingFakeJenkins(),
        session_factory,
        1702,
        ingest_unittest_logs=True,
        unittest_suites={"SMB Transform"},
    )
    with session_scope(session_factory) as s:
        # 15 JUnit (14 + injected) + 8 console-log − 1 overlap collapsed = 22.
        assert s.scalar(select(func.count()).select_from(TestResult)) == 22
        # Exactly one row for the overlap, and it's the JUnit copy (duration 2.5, not console 0.0).
        overlap = s.scalars(
            select(TestResult)
            .join(TestResult.identity)
            .where(
                TestIdentity.canonical_name
                == "smb.transform.test_pricing.PricingTransformTest.test_round_half_even",
                TestResult.track == "permanent_py39",
            )
        ).all()
        assert len(overlap) == 1
        assert overlap[0].duration == 2.5
