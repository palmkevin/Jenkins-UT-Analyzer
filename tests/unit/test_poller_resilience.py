"""Poller hardening (issue #51): in-tick retries, build quarantine, ops alerts, /health, recovery.

All offline: fakes for Jenkins and email, in-memory SQLite for the store, an injected ``sleep``
recorder instead of real backoff waits.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from tests.fakes import FakeJenkinsClient
from tests.fakes.email import RecordingEmailSender
from uta.config import Settings
from uta.control.health import check_health
from uta.control.heartbeat import read_heartbeat, record_heartbeat
from uta.control.jobs import create_ingest_job, recover_orphaned_jobs, run_ingest_job
from uta.control.quarantine import quarantined_build_numbers
from uta.db import Base, make_engine, make_session_factory, session_scope
from uta.models import BuildQuarantine, IngestJob, Run
from uta.models.enums import IngestJobStatus
from uta.poller import BuildIngestError, builds_to_ingest, poll_once, poll_tick
from uta.web.app import create_app

_RECIPIENTS = ("ops@example.test",)


class _MultiBuildFake(FakeJenkinsClient):
    """Serves the #1702 golden fixtures for *any* build number; configurable high-water mark."""

    def __init__(self, last_completed: int) -> None:
        super().__init__()
        self._last_completed = last_completed

    def _load(self, name: str, build: int) -> dict:
        return super()._load(name, self._build)

    def stage_describe(self, build: int, node_id: str) -> dict:
        return super().stage_describe(self._build, node_id)

    def stage_log(self, build: int, node_id: str) -> dict:
        return super().stage_log(self._build, node_id)

    def last_completed_build(self) -> int | None:
        return self._last_completed


class _FlakyNetworkFake(_MultiBuildFake):
    """``build_meta`` of one build raises a transient network error the first ``failures`` times."""

    def __init__(self, last_completed: int, *, failing: int, failures: int) -> None:
        super().__init__(last_completed=last_completed)
        self._failing = failing
        self._remaining = failures

    def build_meta(self, build: int) -> dict:
        if build == self._failing and self._remaining > 0:
            self._remaining -= 1
            raise httpx.ConnectError("connection reset by peer")
        return super().build_meta(build)


class _MalformedBuildFake(_MultiBuildFake):
    """One build always fails deterministically (a parse error, not a network fault)."""

    def __init__(self, last_completed: int, *, failing: int) -> None:
        super().__init__(last_completed=last_completed)
        self._failing = failing

    def build_meta(self, build: int) -> dict:
        if build == self._failing:
            raise ValueError("unexpected enclosingBlockNames for suite")
        return super().build_meta(build)


class _Rotated404Fake(_MultiBuildFake):
    """One build's detail endpoint 404s (rotated out of Jenkins retention)."""

    def __init__(self, last_completed: int, *, missing: int) -> None:
        super().__init__(last_completed=last_completed)
        self._missing = missing

    def build_meta(self, build: int) -> dict:
        if build == self._missing:
            request = httpx.Request("GET", f"http://jenkins/{build}/api/json")
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError("Not Found", request=request, response=response)
        return super().build_meta(build)


class _SleepRecorder:
    def __init__(self) -> None:
        self.delays: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


def _run_count(session_factory) -> int:
    with session_scope(session_factory) as s:
        return s.scalar(select(func.count()).select_from(Run))


def _quarantine_row(session_factory, build: int) -> BuildQuarantine | None:
    with session_scope(session_factory) as s:
        row = s.get(BuildQuarantine, build)
        if row is not None:
            s.expunge(row)
        return row


def _ops_mails(sender: RecordingEmailSender) -> list:
    """Only the operational alerts — the sender also receives ordinary regression reports."""
    return [m for m in sender.sent if m.subject.startswith("UT Analyzer ops")]


# ── In-tick retry with exponential backoff ───────────────────────────────────


def test_transient_failure_is_retried_and_succeeds_within_the_tick(session_factory):
    client = _FlakyNetworkFake(last_completed=1, failing=1, failures=2)
    sleep = _SleepRecorder()
    processed = poll_once(
        client, session_factory, retry_attempts=3, retry_base_seconds=2.0, sleep=sleep
    )
    assert processed == [1]
    assert sleep.delays == [2.0, 4.0]  # exponential backoff between the in-tick attempts
    assert _quarantine_row(session_factory, 1) is None  # success leaves no failure record


def test_exhausted_transient_retries_record_an_attempt_and_end_the_tick(session_factory):
    client = _FlakyNetworkFake(last_completed=2, failing=1, failures=99)
    sleep = _SleepRecorder()
    with pytest.raises(BuildIngestError) as excinfo:
        poll_once(client, session_factory, retry_attempts=3, sleep=sleep)
    assert excinfo.value.build == 1
    assert excinfo.value.processed == []
    assert len(sleep.delays) == 2  # 3 attempts ⇒ 2 backoff waits
    row = _quarantine_row(session_factory, 1)
    assert row.attempts == 1 and row.quarantined_at is None
    # The tick ended at the failing build: build #2 was not ingested out of order.
    assert _run_count(session_factory) == 0


def test_deterministic_failure_is_not_retried_in_tick(session_factory):
    client = _MalformedBuildFake(last_completed=1, failing=1)
    sleep = _SleepRecorder()
    with pytest.raises(BuildIngestError):
        poll_once(client, session_factory, retry_attempts=3, sleep=sleep)
    assert sleep.delays == []  # a parse error cannot succeed seconds later — fail fast


def test_success_after_earlier_failing_tick_clears_the_failure_record(session_factory):
    # Tick 1: transient outage outlasts the in-tick retries — one attempt recorded.
    client = _FlakyNetworkFake(last_completed=1, failing=1, failures=99)
    with pytest.raises(BuildIngestError):
        poll_once(client, session_factory, retry_attempts=2, sleep=_SleepRecorder())
    assert _quarantine_row(session_factory, 1).attempts == 1
    # Tick 2: the blip is over — the build ingests and its failure record is dropped.
    client._remaining = 0
    assert poll_once(client, session_factory, retry_attempts=2, sleep=_SleepRecorder()) == [1]
    assert _quarantine_row(session_factory, 1) is None


# ── Quarantine after persistent failure ──────────────────────────────────────


def test_persistent_failure_quarantines_advances_and_alerts(session_factory):
    client = _MalformedBuildFake(last_completed=2, failing=1)
    sender = RecordingEmailSender()

    # Ticks 1 and 2: the malformed build blocks the tick and accrues attempts.
    for expected_attempts in (1, 2):
        with pytest.raises(BuildIngestError):
            poll_once(
                client,
                session_factory,
                quarantine_attempts=3,
                email_sender=sender,
                email_recipients=_RECIPIENTS,
                sleep=_SleepRecorder(),
            )
        assert _quarantine_row(session_factory, 1).attempts == expected_attempts
        assert _ops_mails(sender) == []

    # Tick 3: attempts reach the limit — quarantined, alerted, and the tick continues past it.
    processed = poll_once(
        client,
        session_factory,
        quarantine_attempts=3,
        email_sender=sender,
        email_recipients=_RECIPIENTS,
        sleep=_SleepRecorder(),
    )
    assert processed == [2]
    row = _quarantine_row(session_factory, 1)
    assert row.quarantined_at is not None and row.attempts == 3
    ops = _ops_mails(sender)
    assert len(ops) == 1
    assert "quarantined" in ops[0].subject
    assert "#1" in ops[0].subject
    # The high-water mark advanced past the quarantined build …
    with session_scope(session_factory) as s:
        assert s.scalar(select(func.max(Run.build_number))) == 2
        assert quarantined_build_numbers(s) == {1}
    # … and the next tick does not re-select it.
    assert poll_once(client, session_factory, sleep=_SleepRecorder()) == []


def test_builds_to_ingest_excludes_quarantined_builds(session_factory):
    client = _MalformedBuildFake(last_completed=2, failing=2)
    # One-strike limit: #1 ingests, then #2 fails, is quarantined at once, and the tick ends clean.
    assert poll_once(client, session_factory, quarantine_attempts=1, sleep=_SleepRecorder()) == [1]
    # #2 sits above the high-water mark but is quarantined — never re-selected …
    assert builds_to_ingest(client, session_factory) == []
    # … and when a newer build appears, selection jumps straight past it.
    client._last_completed = 3
    assert builds_to_ingest(client, session_factory) == [3]


def test_404_build_is_quarantined_immediately_and_alerted(session_factory):
    client = _Rotated404Fake(last_completed=3, missing=2)
    sender = RecordingEmailSender()
    processed = poll_once(
        client,
        session_factory,
        email_sender=sender,
        email_recipients=_RECIPIENTS,
        sleep=_SleepRecorder(),
    )
    assert processed == [1, 3]  # the rotated build is skipped, later builds still ingest
    row = _quarantine_row(session_factory, 2)
    assert row.quarantined_at is not None
    assert "404" in row.last_error
    ops = _ops_mails(sender)
    assert len(ops) == 1 and "skipped" in ops[0].subject
    # Never re-selected, never re-alerted.
    assert poll_once(client, session_factory, email_sender=sender, sleep=_SleepRecorder()) == []
    assert len(_ops_mails(sender)) == 1


def test_ondemand_reingest_clears_a_quarantined_build(session_factory):
    client = _MalformedBuildFake(last_completed=1, failing=1)
    # One-strike limit ⇒ quarantined on the first failing tick (no BuildIngestError raised).
    assert poll_once(client, session_factory, quarantine_attempts=1, sleep=_SleepRecorder()) == []
    assert _quarantine_row(session_factory, 1).quarantined_at is not None

    # The cause is fixed (the build's payload parses again); re-ingest from the control panel.
    with session_scope(session_factory) as s:
        job = create_ingest_job(s, 1, 1)
        s.flush()
        job_id = job.id
    run_ingest_job(
        session_factory,
        job_id,
        settings=Settings(),
        client=_MultiBuildFake(last_completed=1),
        feed=None,
    )
    assert _quarantine_row(session_factory, 1) is None
    assert _run_count(session_factory) == 1


# ── poll_tick: heartbeat bookkeeping around failures ─────────────────────────


def test_failing_tick_records_partial_progress_and_error(session_factory):
    client = _MalformedBuildFake(last_completed=3, failing=2)
    processed = poll_tick(client, session_factory, Settings(), sleep=_SleepRecorder())
    assert processed == [1]  # build #1 landed before #2 wedged the tick
    with session_scope(session_factory) as s:
        hb = read_heartbeat(s)
        assert hb.last_processed == "1"
        assert "enclosingBlockNames" in hb.last_error
        assert hb.last_success_at is None  # a failing tick is not a successful poll


def test_clean_tick_stamps_last_success(session_factory):
    poll_tick(_MultiBuildFake(last_completed=1), session_factory, Settings())
    with session_scope(session_factory) as s:
        assert read_heartbeat(s).last_success_at is not None


# ── /health: DB connectivity + heartbeat freshness ───────────────────────────


def _client_settings(**kw) -> Settings:
    return Settings(poll_interval_seconds=300, poller_stale_after_intervals=3, **kw)


def _shared_memory_factory():
    """An in-memory SQLite store usable across threads (the TestClient runs requests in one)."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


def test_health_ok_without_heartbeat(session_factory):
    report = check_health(session_factory, _client_settings())
    assert report.ok and report.db == "ok" and report.poller == "never"


def test_health_ok_with_fresh_heartbeat(session_factory):
    record_heartbeat(session_factory, processed=[1], error=None)
    report = check_health(session_factory, _client_settings())
    assert report.ok and report.poller == "ok"


def test_health_stale_heartbeat_is_degraded_and_alerts_once(session_factory):
    record_heartbeat(session_factory, processed=[1], error=None)
    sender = RecordingEmailSender()
    late = datetime.now(UTC) + timedelta(hours=2)  # 2h ≫ 3 × 300s

    for _ in range(2):  # a monitor probing repeatedly must not re-mail
        report = check_health(
            session_factory,
            _client_settings(),
            email_sender=sender,
            email_recipients=_RECIPIENTS,
            now=late,
        )
        assert not report.ok and report.poller == "stale"
    assert len(sender.sent) == 1
    assert "stale" in sender.sent[0].subject

    # Recovery re-arms the alert: a fresh success clears the latch, a later staleness re-mails.
    record_heartbeat(session_factory, processed=[2], error=None)
    assert check_health(session_factory, _client_settings(), now=datetime.now(UTC)).ok
    check_health(
        session_factory,
        _client_settings(),
        email_sender=sender,
        email_recipients=_RECIPIENTS,
        now=late,
    )
    assert len(sender.sent) == 2


def test_health_poller_that_ticks_but_never_succeeds_goes_stale(session_factory):
    record_heartbeat(session_factory, processed=[1], error=None)
    # From then on every tick fails: last_poll_at stays fresh, last_success_at doesn't move.
    record_heartbeat(session_factory, processed=[], error="boom")
    late = datetime.now(UTC) + timedelta(hours=2)
    report = check_health(session_factory, _client_settings(), now=late)
    assert not report.ok and report.poller == "stale"


def test_health_endpoint_returns_503_when_db_unreachable():
    # Nothing listens on port 9 — the connection is refused locally, no live system involved.
    broken = make_session_factory(make_engine("postgresql+psycopg://u:p@127.0.0.1:9/nope"))
    client = TestClient(create_app(session_factory=broken))
    resp = client.get("/health")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded" and body["db"] == "error"


def test_health_endpoint_returns_503_when_heartbeat_stale():
    sf = _shared_memory_factory()  # request runs in the TestClient thread — needs a shared pool
    record_heartbeat(sf, processed=[1], error=None)
    with session_scope(sf) as s:
        hb = read_heartbeat(s)
        hb.last_success_at = datetime.now(UTC) - timedelta(days=2)
        hb.last_poll_at = datetime.now(UTC) - timedelta(days=2)
    client = TestClient(create_app(session_factory=sf))
    resp = client.get("/health")
    assert resp.status_code == 503
    assert resp.json()["poller"] == "stale"


# ── Orphaned-job recovery on startup ─────────────────────────────────────────


def _seed_job(session_factory, status: IngestJobStatus) -> int:
    with session_scope(session_factory) as s:
        job = IngestJob(build_start=1, build_end=1, status=status, builds_total=1, builds_done=0)
        s.add(job)
        s.flush()
        return job.id


def test_recover_orphaned_jobs_flips_queued_and_running_to_error(session_factory):
    queued = _seed_job(session_factory, IngestJobStatus.QUEUED)
    running = _seed_job(session_factory, IngestJobStatus.RUNNING)
    done = _seed_job(session_factory, IngestJobStatus.DONE)

    assert recover_orphaned_jobs(session_factory) == 2

    with session_scope(session_factory) as s:
        for job_id in (queued, running):
            job = s.get(IngestJob, job_id)
            assert job.status == IngestJobStatus.ERROR
            assert "orphaned by a restart" in job.error
            assert job.finished_at is not None
        assert s.get(IngestJob, done).status == IngestJobStatus.DONE  # untouched


def test_web_startup_recovers_orphaned_jobs():
    sf = _shared_memory_factory()
    running = _seed_job(sf, IngestJobStatus.RUNNING)

    # The lifespan (startup) hook runs when the TestClient is entered — a "restart".
    with TestClient(create_app(session_factory=sf)):
        pass

    with session_scope(sf) as s:
        assert s.get(IngestJob, running).status == IngestJobStatus.ERROR
