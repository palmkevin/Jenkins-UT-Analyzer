"""The scheduled poller's heartbeat (issue #16) — read + write of the singleton status row.

The poller stamps :func:`record_heartbeat` after every tick (success or failure); the dashboard
reads :func:`read_heartbeat` to show last-poll time, last tick's build count, and the last error.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from uta.db import session_scope
from uta.models import PollerHeartbeat

_HEARTBEAT_ID = 1
_MAX_ERROR = 2000


def _get_or_create(session: Session) -> PollerHeartbeat:
    hb = session.get(PollerHeartbeat, _HEARTBEAT_ID)
    if hb is None:
        hb = PollerHeartbeat(id=_HEARTBEAT_ID)
        session.add(hb)
    return hb


def record_heartbeat(
    session_factory: sessionmaker[Session],
    *,
    processed: Sequence[int],
    error: str | None = None,
) -> None:
    """Stamp the poll tick: time, builds processed, and — only when a tick fails — the error.

    A successful tick leaves the previous ``last_error`` in place (it is the *last* error, not a
    per-tick flag), so a transient failure stays visible until the operator has seen it; a fresh
    error overwrites it. ``last_success_at`` moves on an error-free tick (and, via
    :func:`record_liveness`, after each ingested build) — it is the freshness reference ``/health``
    evaluates ("no successful poll in N intervals", issue #51).
    """
    now = datetime.now(UTC)
    with session_scope(session_factory) as session:
        hb = _get_or_create(session)
        hb.last_poll_at = now
        hb.last_processed_count = len(processed)
        hb.last_processed = ",".join(str(b) for b in list(processed)[-20:]) or None
        if error is not None:
            hb.last_error = error[:_MAX_ERROR]
            hb.last_error_at = now
        else:
            hb.last_success_at = now


def record_liveness(session_factory: sessionmaker[Session]) -> None:
    """Stamp ``last_success_at`` mid-tick, after each successfully ingested build.

    The heartbeat is otherwise only written at tick end, so a long catch-up tick (many builds,
    each minutes long) looked stale to ``/health`` while it was making progress. A build that
    ingested is proof the poller works, so it refreshes the freshness reference without touching
    the per-tick fields (count / processed list / last error), which the tick-end stamp still owns.
    """
    with session_scope(session_factory) as session:
        _get_or_create(session).last_success_at = datetime.now(UTC)


def read_heartbeat(session: Session) -> PollerHeartbeat | None:
    """The singleton heartbeat row, or ``None`` if the poller has never run."""
    return session.get(PollerHeartbeat, _HEARTBEAT_ID)
