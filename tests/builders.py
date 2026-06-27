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
) -> Run:
    """Create a complete (by default) run where each ``name`` has ``status`` in every track.

    ``statuses`` maps canonical test name -> JUnit status (PASSED/FAILED/REGRESSION/FIXED/SKIPPED).
    ``error_type`` optionally maps name -> derived error type (to drive INFRA classification).
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
    for name, status in statuses.items():
        ident = get_identity(session, name)
        for track in tracks:
            run.results.append(
                TestResult(
                    identity=ident,
                    track=track,
                    status=status,
                    error_type=err.get(name),
                )
            )
    session.flush()
    return run
