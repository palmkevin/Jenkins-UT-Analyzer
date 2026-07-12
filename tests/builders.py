"""Helpers to construct synthetic runs/results directly in the DB for analysis tests.

The lifecycle/diff/classification logic is exercised against hand-built run sequences (no Jenkins
fixtures needed) so each scenario — clean regression, fix, reopen, removal, flaky-style flips,
incomplete baseline — is explicit and isolated.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from uta.models import Run, TestIdentity, TestResult

_EPOCH = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)


def get_identity(session: Session, name: str) -> TestIdentity:
    ident = session.scalar(select(TestIdentity).where(TestIdentity.canonical_name == name))
    if ident is None:
        ident = TestIdentity(canonical_name=name)
        session.add(ident)
        session.flush()
    return ident


def make_run(
    session: Session,
    build: int,
    statuses: dict[str, str],
    *,
    complete: bool = True,
    tracks: tuple[str, ...] = ("permanent", "permanent_py39"),
    started_at: datetime | None = None,
    error_type: dict[str, str] | None = None,
    errors: dict[str, tuple[str | None, str | None]] | None = None,
    fail_tracks: dict[str, tuple[str, ...]] | None = None,
) -> Run:
    """Create a complete (by default) run where each ``name`` has ``status`` in every track.

    ``statuses`` maps canonical test name -> JUnit status (PASSED/FAILED/REGRESSION/FIXED/SKIPPED).
    ``error_type`` optionally maps name -> derived error type (to drive INFRA classification).
    ``errors`` optionally maps name -> (error_details, error_stack_trace) for KB signature tests.
    ``fail_tracks`` optionally restricts which tracks a failing test fails in (the rest pass) — for
    shard-correlation tests; default is "fails in all tracks".
    """
    start = started_at or (_EPOCH + timedelta(hours=build))
    run = Run(
        build_number=build,
        status="SUCCESS",
        started_at=start,
        finished_at=start + timedelta(minutes=30),
        complete=complete,
    )
    session.add(run)
    session.flush()
    err = error_type or {}
    errs = errors or {}
    only = fail_tracks or {}
    for name, status in statuses.items():
        ident = get_identity(session, name)
        details, stack = errs.get(name, (None, None))
        for track in tracks:
            track_status = status
            if status in ("FAILED", "REGRESSION") and name in only and track not in only[name]:
                track_status = "PASSED"
            run.results.append(
                TestResult(
                    identity=ident,
                    track=track,
                    status=track_status,
                    error_type=err.get(name) if track_status == status else None,
                    error_details=details if track_status == status else None,
                    error_stack_trace=stack if track_status == status else None,
                )
            )
    # Mirror the ingest pipeline's totals (per-result-row counts) so views built on run.total_*
    # (the run-page header / failures-only heading, issue #157) see the real invariant:
    # total_passed + total_failed + total_skipped == the run's result-row count.
    run.total_passed = sum(1 for r in run.results if r.status in ("PASSED", "FIXED"))
    run.total_failed = sum(1 for r in run.results if r.status in ("FAILED", "REGRESSION"))
    run.total_skipped = sum(1 for r in run.results if r.status == "SKIPPED")
    session.flush()
    return run
