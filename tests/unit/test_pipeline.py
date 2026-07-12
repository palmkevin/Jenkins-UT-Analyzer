"""Slice-0 ingest pipeline against an in-memory SQLite DB (offline, no Postgres)."""

from __future__ import annotations

import smtplib
import threading
import time
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import exc as sa_exc
from sqlalchemy import func, select

from tests.builders import make_run
from tests.fakes import FakeJenkinsClient, FakeTrackingFeed
from tests.fakes.email import RecordingEmailSender
from uta.analyze.baseline import select_baseline
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


class _AbortedShardFakeJenkins(FakeJenkinsClient):
    """A build interrupted mid-way through the py39 UT shard: ``wfapi/describe`` still lists both
    UT stages, but the interrupted one carries status ABORTED (issue #83)."""

    def wfapi(self, build: int) -> dict:
        payload = super().wfapi(build)
        for stage in payload["stages"]:
            if stage["name"] == "devUTs: Execute - permanent_py39":
                stage["status"] = "ABORTED"
        return payload


def test_ingest_aborted_shard_run_is_incomplete_and_never_a_baseline(session_factory):
    """Both shards present but one ABORTED ⇒ not complete, no analysis, never the baseline."""
    ingest_build(_AbortedShardFakeJenkins(), session_factory, 1702, expected_shards=2)
    with session_scope(session_factory) as s:
        run = s.scalar(select(Run).where(Run.build_number == 1702))
        assert run.complete is False
        assert {sh.track: sh.status for sh in run.shards}["permanent_py39"] == "ABORTED"
        # The partial run is persisted but gated out of the analysis…
        assert s.scalar(select(func.count()).select_from(TestResult)) == 14
        assert s.scalar(select(func.count()).select_from(FailureEpisode)) == 0
        # …and a later run never diffs against it.
        later = make_run(s, 1703, {}, started_at=run.started_at + timedelta(hours=24))
        assert select_baseline(s, later) is None


def test_ingest_stores_zephyr_test_cases_on_identity(session_factory):
    """The ZEPHYR test case(s) a failing test references are resolved onto its identity."""
    ingest_build(FakeJenkinsClient(), session_factory, 1702, expected_shards=2)
    with session_scope(session_factory) as s:
        ident = s.scalar(
            select(TestIdentity).where(
                TestIdentity.canonical_name
                == "ut_accounting.ac_csvc.TestClass.test_inpmode_alternativ_debitor_at_cust"
            )
        )
        assert ident is not None
        assert ident.zephyr_test_cases == "LX-T4447"
        # A passing test carries no ZEPHYR block, so its identity stays null.
        passing = s.scalars(
            select(TestIdentity).where(TestIdentity.zephyr_test_cases.is_(None))
        ).all()
        assert passing  # at least one test has no referenced case


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


def test_ingest_sends_nothing_without_recipients(session_factory):
    """A sender with no recipients means email isn't configured — no report is even composed."""
    sender = RecordingEmailSender()
    ingest_build(FakeJenkinsClient(), session_factory, 1702, email_sender=sender)
    assert sender.sent == []


class _RaisingEmailSender:
    """An :class:`~uta.delivery.email.EmailSender` whose relay is down — every send raises."""

    def __init__(self) -> None:
        self.attempts = 0

    def send(self, message) -> None:
        self.attempts += 1
        raise smtplib.SMTPException("relay down")


def test_email_failure_does_not_fail_or_roll_back_ingest(session_factory):
    """An SMTP outage must never destroy an ingest (issue #81).

    The alert is sent only after the run's transaction commits, and a send failure is swallowed —
    so the run and its results are persisted regardless, and ``ingest_build`` returns normally
    (no quarantine attempt is ever recorded for a mail outage).
    """
    sender = _RaisingEmailSender()
    ingest_build(
        FakeJenkinsClient(),
        session_factory,
        1702,
        email_sender=sender,
        email_recipients=("team@example.com",),
    )
    assert sender.attempts == 1  # the send was attempted (post-commit) and its failure swallowed
    with session_scope(session_factory) as s:
        run = s.scalar(select(Run).where(Run.build_number == 1702))
        assert run is not None and run.complete is True
        assert s.scalar(select(func.count()).select_from(TestResult)) == 14


class _CommitFailsOnce:
    """A session factory whose first ``commit()`` raises a transient ``OperationalError``.

    Simulates the poller-retry scenario of issue #81: ingest completes, the commit blips, the
    poller retries ``ingest_build``. The alert must go out for the committed attempt only.
    """

    def __init__(self, session_factory) -> None:
        self._factory = session_factory
        self.failed = False

    def __call__(self):
        session = self._factory()
        if not self.failed:

            def _fail_once():
                self.failed = True
                # ``session_scope`` rolls back on the raise, discarding the attempt's writes.
                raise sa_exc.OperationalError("COMMIT", None, RuntimeError("connection blip"))

            session.commit = _fail_once
        return session


def test_alert_sent_once_when_retry_follows_commit_failure(session_factory):
    """A commit failure after the analysis must not duplicate the alert on retry (issue #81).

    The send happens only after a successful commit, so the failed first attempt mails nothing;
    the retry recomputes the identical diff and sends the alert exactly once.
    """
    sender = RecordingEmailSender()
    factory = _CommitFailsOnce(session_factory)
    with pytest.raises(sa_exc.OperationalError):
        ingest_build(
            FakeJenkinsClient(),
            factory,
            1702,
            email_sender=sender,
            email_recipients=("team@example.com",),
        )
    assert sender.sent == []  # nothing committed ⇒ nothing mailed

    # The poller retries the transient failure with the same arguments (its live path).
    ingest_build(
        FakeJenkinsClient(),
        factory,
        1702,
        email_sender=sender,
        email_recipients=("team@example.com",),
    )
    assert len(sender.sent) == 1  # exactly one alert across the failed attempt + retry
    with session_scope(session_factory) as s:
        assert s.scalar(select(func.count()).select_from(TestResult)) == 14


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


class _ConcurrencyTrackingFake(FakeJenkinsClient):
    """Records the peak number of Jenkins calls in flight, to verify the fetch phase parallelizes
    (issue #65) rather than serializing the base endpoints (and, when enabled, the per-stage
    describe/log pairs)."""

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self._in_flight = 0
        self.peak_concurrency = 0

    def _track(self, fn, *args):
        with self._lock:
            self._in_flight += 1
            self.peak_concurrency = max(self.peak_concurrency, self._in_flight)
        try:
            time.sleep(0.01)  # widen the window so overlapping calls are reliably observed
            return fn(*args)
        finally:
            with self._lock:
                self._in_flight -= 1

    def build_meta(self, build):
        return self._track(super().build_meta, build)

    def wfapi(self, build):
        return self._track(super().wfapi, build)

    def test_report(self, build):
        return self._track(super().test_report, build)

    def change_sets(self, build):
        return self._track(super().change_sets, build)

    def stage_describe(self, build, node_id):
        return self._track(super().stage_describe, build, node_id)

    def stage_log(self, build, node_id):
        return self._track(super().stage_log, build, node_id)


def test_ingest_fetches_base_endpoints_concurrently(session_factory):
    """The 4 base Jenkins calls overlap in flight instead of running one after another."""
    fake = _ConcurrencyTrackingFake()
    ingest_build(fake, session_factory, 1702, expected_shards=2)
    assert fake.peak_concurrency >= 2


def test_ingest_fetches_unittest_stages_concurrently(session_factory):
    """Multiple unittest console-log stages' describe/log pairs also fetch in parallel."""
    fake = _ConcurrencyTrackingFake()
    ingest_build(
        fake,
        session_factory,
        1702,
        ingest_unittest_logs=True,
        unittest_suites={"SMB Transform"},
    )
    assert fake.peak_concurrency >= 2


def test_ingest_parallel_fetch_matches_serial_output(session_factory):
    """Parallelizing the fetch phase must not change the persisted result (issue #65)."""
    ingest_build(
        _ConcurrencyTrackingFake(),
        session_factory,
        1702,
        ingest_unittest_logs=True,
        unittest_suites={"SMB Transform"},
    )
    with session_scope(session_factory) as s:
        # Same counts as the serial-fetch test test_ingest_unittest_logs_adds_console_log_results.
        assert s.scalar(select(func.count()).select_from(TestResult)) == 22
        assert s.scalar(select(func.count()).select_from(FailureEpisode)) == 9
        assert s.scalar(select(func.count()).select_from(Classification)) == 9


class _ScriptedJenkins:
    """A fixtures-free multi-build fake: each build maps test name -> JUnit status (PASSED/FAILED).

    Duck-types the pipeline's ``JenkinsClient`` protocol (the golden-fixtures fake serves a single
    build, so cross-build scenarios script their own history here). Every run is **complete** (both
    track shards report), and build #N starts N hours after a fixed epoch, so build-number order ==
    start-time order, as on the real job. The ``builds`` dict is held by reference — a test may
    mutate a build's statuses to simulate a re-run with different content.
    """

    _EPOCH_MS = 1_780_000_000_000  # fixed, arbitrary epoch millis (UTC)

    def __init__(self, builds: dict[int, dict[str, str]]) -> None:
        self.builds = builds

    def _statuses(self, build: int) -> dict[str, str]:
        if build not in self.builds:
            raise KeyError(f"no scripted build {build}")
        return self.builds[build]

    def _start_millis(self, build: int) -> int:
        return self._EPOCH_MS + build * 3_600_000

    def build_meta(self, build: int) -> dict:
        self._statuses(build)
        return {
            "number": build,
            "result": "UNSTABLE",
            "url": f"http://jenkins/{build}/",
            "timestamp": self._start_millis(build),
            "duration": 3_600_000,
        }

    def test_report(self, build: int) -> dict:
        suites = [
            {
                "name": "nose2-junit",
                "enclosingBlockNames": [track],
                "cases": [
                    {
                        "className": "pkg.Cls",
                        "name": name,
                        "status": status,
                        "duration": 0.1,
                        "errorDetails": "boom" if status == "FAILED" else None,
                        "errorStackTrace": "ValueError: boom" if status == "FAILED" else None,
                    }
                    for name, status in self._statuses(build).items()
                ],
            }
            for track in ("permanent", "permanent_py39")
        ]
        return {"suites": suites}

    def change_sets(self, build: int) -> dict:
        self._statuses(build)
        return {"changeSets": []}

    def wfapi(self, build: int) -> dict:
        start = self._start_millis(build)
        self._statuses(build)
        return {
            "id": str(build),
            "name": f"#{build}",
            "status": "UNSTABLE",
            "startTimeMillis": start,
            "durationMillis": 3_600_000,
            "stages": [
                {
                    "id": str(300 + i),
                    "name": f"devUTs: Execute - {track}",
                    "status": "SUCCESS",
                    "startTimeMillis": start,
                    "durationMillis": 3_000_000,
                }
                for i, track in enumerate(("permanent", "permanent_py39"))
            ],
        }

    def stage_describe(self, build: int, node_id: str) -> dict:
        return {"id": str(node_id), "stageFlowNodes": []}

    def stage_log(self, build: int, node_id: str) -> dict:
        return {"nodeId": str(node_id), "text": ""}

    def last_completed_build(self) -> int | None:
        return max(self.builds)


def _lifecycle_snapshot(session) -> tuple[dict, dict]:
    """Every lifecycle + episode fact a historical re-ingest must leave untouched (issue #82)."""
    lifecycles = {
        lc.identity.canonical_name: (
            lc.state,
            lc.reopen_count,
            lc.acknowledged,
            lc.acknowledged_by,
            lc.current_episode_id,
            lc.last_failing_run_id,
        )
        for lc in session.scalars(select(TestLifecycle)).all()
    }
    episodes = {
        (ep.identity.canonical_name, ep.episode_number): (
            ep.is_open,
            ep.first_failure_run_id,
            ep.last_failing_run_id,
            ep.fixed_in_run_id,
            ep.age_runs,
        )
        for ep in session.scalars(select(FailureEpisode)).all()
    }
    return lifecycles, episodes


def test_historical_reingest_skips_lifecycle(session_factory):
    """Re-ingesting an older build (the quarantine-recovery path, issue #82) keeps the run's data
    but must not drive the lifecycle: the old diff would open phantom episodes and close live ones.

    Timeline: #103 was quarantined and skipped; #102 and #104-#106 ingested. ``t_fix`` failed in
    #104 and was fixed by #105 (episode closed, then acknowledged); ``t_live`` has been failing
    since #102 (live open episode); ``t_calm`` always passes. The recovered #103 disagrees on all
    three: ``t_fix`` FAILED (would reopen a phantom episode and clear the ack), ``t_live`` PASSED
    (would close the live episode "in the past"), ``t_calm`` FAILED (would invent lifecycle state
    for a healthy test).
    """
    fake = _ScriptedJenkins(
        {
            102: {"t_fix": "PASSED", "t_live": "FAILED", "t_calm": "PASSED"},
            103: {"t_fix": "FAILED", "t_live": "PASSED", "t_calm": "FAILED"},
            104: {"t_fix": "FAILED", "t_live": "FAILED", "t_calm": "PASSED"},
            105: {"t_fix": "PASSED", "t_live": "FAILED", "t_calm": "PASSED"},
            106: {"t_fix": "PASSED", "t_live": "FAILED", "t_calm": "PASSED"},
        }
    )
    for n in (102, 104, 105, 106):
        ingest_build(fake, session_factory, n)

    with session_scope(session_factory) as s:
        # A human acknowledged the fixed test — the phantom reopen would have cleared this.
        lc = s.scalar(
            select(TestLifecycle)
            .join(TestLifecycle.identity)
            .where(TestIdentity.canonical_name == "pkg.Cls.t_fix")
        )
        assert lc.state == LifecycleState.FIXED
        lc.acknowledged = True
        lc.acknowledged_by = "alice"

    with session_scope(session_factory) as s:
        before = _lifecycle_snapshot(s)
        classifications_before = s.scalar(select(func.count()).select_from(Classification))

    # The recovery re-ingest — with a sender wired, to prove the notify step is skipped too.
    sender = RecordingEmailSender()
    ingest_build(
        fake, session_factory, 103, email_sender=sender, email_recipients=("team@example.com",)
    )
    assert sender.sent == []  # a historical diff is never mailed

    with session_scope(session_factory) as s:
        # Lifecycle states, episodes, episode numbers and acknowledgements: all untouched —
        # in particular no phantom episode for t_fix, no closure of t_live's live episode, and
        # still no lifecycle row at all for the healthy t_calm.
        assert _lifecycle_snapshot(s) == before
        assert s.scalar(select(func.count()).select_from(Classification)) == classifications_before

        # The run itself is fully persisted: results (3 tests x 2 tracks), KB signatures on the
        # failures, and the display baseline stamped so the run page shows its diff.
        run = s.scalar(select(Run).where(Run.build_number == 103))
        assert run is not None and run.complete is True
        results = s.scalars(select(TestResult).where(TestResult.run_id == run.id)).all()
        assert len(results) == 6
        failing = [r for r in results if r.status in FAILED_STATUSES]
        assert failing and all(r.signature_id is not None for r in failing)
        baseline = s.scalar(select(Run).where(Run.build_number == 102))
        assert run.baseline_run_id == baseline.id


def test_reingest_newest_build_still_analyzed(session_factory):
    """Re-ingesting the **newest** build stays the documented idempotent analysis path.

    Same content twice ⇒ identical lifecycle/episode state; corrected content (the fake's build
    now passes) ⇒ the analysis still runs and closes the episode — proving the historical-skip
    guard is strictly "older than the newest complete run", never the newest build itself.
    """
    fake = _ScriptedJenkins({104: {"t": "FAILED"}, 105: {"t": "FAILED"}})
    ingest_build(fake, session_factory, 104)
    ingest_build(fake, session_factory, 105)

    with session_scope(session_factory) as s:
        before = _lifecycle_snapshot(s)

    ingest_build(fake, session_factory, 105)  # same content — idempotent, analysis included
    with session_scope(session_factory) as s:
        assert _lifecycle_snapshot(s) == before
        assert s.scalar(select(func.count()).select_from(FailureEpisode)) == 1

    fake.builds[105] = {"t": "PASSED"}  # the re-run build now passes
    ingest_build(fake, session_factory, 105)
    with session_scope(session_factory) as s:
        run = s.scalar(select(Run).where(Run.build_number == 105))
        ep = s.scalar(select(FailureEpisode))
        assert ep.is_open is False and ep.fixed_in_run_id == run.id
        assert s.scalar(select(TestLifecycle)).state == LifecycleState.FIXED


def test_reingest_with_changed_content_resets_orphaned_signature_aggregates(session_factory):
    """A re-ingest whose failure vanished must recompute the now-orphaned signature (issue #116).

    #104 and #105 both fail ``t`` — one signature, occurrence 4 (2 runs × 2 tracks). The re-run
    #105 now passes: the signature loses #105's links but gains none, so it is only reachable via
    the pre-delete link capture — occurrence must drop to 2 and last-seen must point back at #104,
    the newest run actually containing the failure (the KB page and the LLM evidence read these).
    """
    fake = _ScriptedJenkins({104: {"t": "FAILED"}, 105: {"t": "FAILED"}})
    ingest_build(fake, session_factory, 104)
    ingest_build(fake, session_factory, 105)

    with session_scope(session_factory) as s:
        sig = s.scalar(select(FailureSignature))
        run105 = s.scalar(select(Run).where(Run.build_number == 105))
        assert sig.occurrence_count == 4
        assert sig.last_seen_run_id == run105.id

    fake.builds[105] = {"t": "PASSED"}  # the re-run build now passes
    ingest_build(fake, session_factory, 105)
    with session_scope(session_factory) as s:
        sig = s.scalar(select(FailureSignature))
        run104 = s.scalar(select(Run).where(Run.build_number == 104))
        assert sig.occurrence_count == 2  # only #104's two tracks remain
        assert sig.first_seen_run_id == run104.id
        assert sig.last_seen_run_id == run104.id
        assert sig.last_seen_at == run104.started_at


def test_reingest_orphaning_all_links_resets_signature_to_zero(session_factory):
    """A signature that loses its every link on re-ingest gets the documented zero/empty reset."""
    fake = _ScriptedJenkins({104: {"t": "FAILED"}})
    ingest_build(fake, session_factory, 104)
    with session_scope(session_factory) as s:
        assert s.scalar(select(FailureSignature)).occurrence_count == 2

    fake.builds[104] = {"t": "PASSED"}
    ingest_build(fake, session_factory, 104)
    with session_scope(session_factory) as s:
        sig = s.scalar(select(FailureSignature))
        assert sig.occurrence_count == 0
        assert sig.first_seen_at is None and sig.last_seen_at is None
        assert sig.first_seen_run_id is None and sig.last_seen_run_id is None


class _FailingReportFake(FakeJenkinsClient):
    """``test_report`` always 5xxs — the failure the poller's transient-retry path expects."""

    def test_report(self, build: int) -> dict:
        request = httpx.Request("GET", f"http://jenkins/{build}/testReport/api/json")
        response = httpx.Response(500, request=request)
        raise httpx.HTTPStatusError("Server Error", request=request, response=response)


def test_ingest_propagates_single_endpoint_failure(session_factory):
    """A single failing endpoint still surfaces its original exception type, unwrapped."""
    with pytest.raises(httpx.HTTPStatusError):
        ingest_build(_FailingReportFake(), session_factory, 1702)
