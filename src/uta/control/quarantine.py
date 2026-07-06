"""Build quarantine — the poller's per-build failure ledger (issue #51).

One :class:`~uta.models.BuildQuarantine` row per build the poller could not ingest. Each failing
tick counts one attempt (in-tick transient retries don't count); until the configured limit the
build blocks the tick and is retried next tick, after it the row is stamped ``quarantined_at`` and
:func:`quarantined_build_numbers` excludes the build from selection, so the high-water mark can
advance past it. A 404-rotated build is quarantined immediately (:func:`quarantine_immediately`) —
the explicit, control-panel-visible mirror of the previously-silent skip. A successful ingest
(poller retry before quarantine, or an on-demand re-ingest) deletes the row.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from uta.db import session_scope
from uta.models import BuildQuarantine

_MAX_ERROR = 2000


def record_failure(
    session_factory: sessionmaker[Session],
    build: int,
    error: str,
    *,
    quarantine_after: int,
) -> BuildQuarantine:
    """Count one failed tick for ``build``; quarantine it once attempts reach the limit.

    Returns a detached copy of the row so the caller can see ``attempts`` and whether this call
    crossed the threshold (``quarantined_at`` newly set).
    """
    now = datetime.now(UTC)
    with session_scope(session_factory) as session:
        row = session.get(BuildQuarantine, build)
        if row is None:
            row = BuildQuarantine(build_number=build, attempts=0, first_failed_at=now)
            session.add(row)
        row.attempts += 1
        row.last_error = error[:_MAX_ERROR]
        if row.quarantined_at is None and row.attempts >= quarantine_after:
            row.quarantined_at = now
        session.flush()
        session.expunge(row)
    return row


def quarantine_immediately(
    session_factory: sessionmaker[Session], build: int, error: str
) -> BuildQuarantine:
    """Quarantine ``build`` in one step — for permanent conditions like a 404-rotated detail."""
    return record_failure(session_factory, build, error, quarantine_after=1)


def clear_failure(session_factory: sessionmaker[Session], build: int) -> None:
    """Drop the failure/quarantine record after ``build`` ingested successfully. No-op if none."""
    with session_scope(session_factory) as session:
        session.execute(delete(BuildQuarantine).where(BuildQuarantine.build_number == build))


def quarantined_build_numbers(session: Session) -> set[int]:
    """The build numbers the poller must skip (quarantined; attempt-only rows are still retried)."""
    rows = session.scalars(
        select(BuildQuarantine.build_number).where(BuildQuarantine.quarantined_at.is_not(None))
    ).all()
    return set(rows)


def list_quarantine(session: Session, *, limit: int = 20) -> list[BuildQuarantine]:
    """The most-recently-touched quarantine rows, newest first (control-panel display).

    Includes both quarantined builds and still-retrying attempt rows — the panel badges them apart.
    """
    return list(
        session.scalars(
            select(BuildQuarantine).order_by(BuildQuarantine.updated_at.desc()).limit(limit)
        ).all()
    )
