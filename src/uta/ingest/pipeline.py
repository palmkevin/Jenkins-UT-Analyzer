"""Slice-0 ingest pipeline: fetch one build -> parse -> persist a run + its results.

Wires the Jenkins client (real or fake) and the parsers. Idempotent on ``build_number``: a
re-ingest replaces the run's results rather than duplicating them.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from uta.db import session_scope
from uta.ingest.jenkins import JenkinsClient
from uta.ingest.ut_report import TestCaseResult, parse_test_report
from uta.ingest.wfapi import parse_wfapi
from uta.models import Run, RunShard, TestIdentity, TestResult

_PASSED = frozenset({"PASSED", "FIXED"})
_FAILED = frozenset({"FAILED", "REGRESSION"})


def _get_or_create_identity(
    session: Session, case: TestCaseResult, cache: dict[str, TestIdentity]
) -> TestIdentity:
    """Resolve the test-level identity for a case, creating it on first sight (idempotent)."""
    name = case.test_id  # className.name — the canonical v1 key
    ident = cache.get(name)
    if ident is None:
        ident = session.scalar(select(TestIdentity).where(TestIdentity.canonical_name == name))
        if ident is None:
            ident = TestIdentity(canonical_name=name)
            session.add(ident)
        cache[name] = ident
    # Keep the descriptive attributes fresh from the latest report.
    ident.suite = case.suite_name
    ident.class_name = case.class_name
    ident.method = case.name
    if case.owner_initials:
        ident.owner_initials = case.owner_initials
    return ident


def ingest_build(
    client: JenkinsClient,
    session_factory: sessionmaker[Session],
    build: int,
    *,
    expected_shards: int = 2,
) -> int:
    """Fetch, parse and persist one build. Returns the run's build_number.

    Milestone 1 populates the full result/identity/shard schema. Lifecycle, episodes, baseline diff
    and classification are wired in Milestone 2; this still only persists facts from the report.
    """
    meta = client.build_meta(build)
    timing = parse_wfapi(client.wfapi(build))
    report = parse_test_report(client.test_report(build))
    win_start, win_end = timing.window

    with session_scope(session_factory) as session:
        run = session.scalar(select(Run).where(Run.build_number == build))
        if run is None:
            run = Run(build_number=build)
            session.add(run)
        else:
            run.results.clear()  # idempotent re-ingest
            run.shards.clear()
            session.flush()  # delete old rows before re-inserting (unique constraint)

        run.status = meta.get("result") or timing.status
        run.url = meta.get("url", "")
        run.started_at = win_start
        run.finished_at = win_end
        run.complete = timing.is_complete(expected_shards)
        run.total_passed = sum(1 for c in report.cases if c.status in _PASSED)
        run.total_failed = sum(1 for c in report.cases if c.status in _FAILED)
        run.total_skipped = sum(1 for c in report.cases if c.status == "SKIPPED")

        for shard in timing.shards.values():
            run.shards.append(
                RunShard(
                    track=shard.track,
                    status=shard.status,
                    started_at=shard.start,
                    finished_at=shard.end,
                )
            )

        identities: dict[str, TestIdentity] = {}
        for case in report.cases:
            ident = _get_or_create_identity(session, case, identities)
            run.results.append(
                TestResult(
                    identity=ident,
                    track=case.track,
                    status=case.status,
                    duration=case.duration,
                    file_path=case.file_path,
                    line=case.line,
                    owner_initials=case.owner_initials,
                    error_details=case.error_details,
                    error_stack_trace=case.error_stack_trace,
                )
            )
    return build


def data_change_window(timing_window: tuple, lookback: timedelta = timedelta(hours=12)) -> tuple:
    """The UTC window for candidate data changes: a lookback before the run through its end.

    Data changes precede the nightly run (confirmed empirically on #1702 — the run's own window had
    no tracked changes), so we look back from the run start. ``lookback`` is a provisional default,
    tuned on real data later.
    """
    start, end = timing_window
    return start - lookback, end
