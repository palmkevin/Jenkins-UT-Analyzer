"""Real ``/health``: DB connectivity + poller-heartbeat freshness (issue #51).

The web process is the one long-lived component an external monitor can reach, so it evaluates the
heartbeat the poller writes: **stale** means no *successful* tick (``last_success_at``) within
``poller_stale_after_intervals × poll_interval_seconds``. A deployment with no poller at all (the
public demo, a web-only stack) has no heartbeat row and reports ``poller: "never"`` while staying
healthy — absence is a topology, staleness is a fault.

Going stale also sends **one** ops alert email through the same :class:`~uta.delivery.email
.EmailSender` seam as the regression report, latched on the heartbeat row (``stale_alerted_at``) so
a monitor probing ``/health`` every few seconds doesn't re-mail; recovery clears the latch.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from uta.config import Settings
from uta.control.heartbeat import read_heartbeat
from uta.db import session_scope
from uta.delivery.email import EmailSender, send_ops_alert


@dataclass(frozen=True)
class HealthReport:
    """What ``/health`` returns: overall verdict + the two checks behind it."""

    ok: bool
    db: str  # "ok" | "error"
    poller: str  # "ok" | "stale" | "never" | "unknown" (DB down — heartbeat unreadable)
    last_success_at: datetime | None = None
    detail: str | None = None

    def payload(self) -> dict:
        return {
            "status": "ok" if self.ok else "degraded",
            "db": self.db,
            "poller": self.poller,
            "last_success_at": (self.last_success_at.isoformat() if self.last_success_at else None),
            "detail": self.detail,
        }


def _aware(ts: datetime) -> datetime:
    """Normalize a possibly-naive stored timestamp to UTC (SQLite reads back naive)."""
    return ts if ts.tzinfo is not None else ts.replace(tzinfo=UTC)


def check_health(
    session_factory: sessionmaker[Session],
    settings: Settings,
    *,
    email_sender: EmailSender | None = None,
    email_recipients: tuple[str, ...] = (),
    now: datetime | None = None,
) -> HealthReport:
    """Evaluate DB reachability and heartbeat freshness; alert (once) on a stale poller.

    Freshness reference is ``last_success_at`` — a poller that ticks but keeps failing goes stale
    too, matching "no successful poll in N intervals". For a heartbeat with no success yet —
    a row predating the ``last_success_at`` column (upgrade window) or a deployment that has
    failed from birth — the row's ``created_at`` stands in, granting one grace window before
    going stale (``last_poll_at`` must not stand in: it stays fresh on failing ticks).
    """
    now = now or datetime.now(UTC)
    try:
        with session_scope(session_factory) as session:
            session.execute(text("SELECT 1"))
            hb = read_heartbeat(session)
            last_success = (hb.last_success_at or hb.created_at) if hb else None
            stale_alerted = hb.stale_alerted_at if hb else None
    except Exception as exc:  # noqa: BLE001 — any DB fault means unhealthy, whatever its type
        return HealthReport(
            ok=False, db="error", poller="unknown", detail=f"database unreachable: {exc!r}"
        )

    if last_success is None:
        return HealthReport(ok=True, db="ok", poller="never")

    last_success = _aware(last_success)
    max_age_seconds = settings.poll_interval_seconds * settings.poller_stale_after_intervals
    age = (now - last_success).total_seconds()
    if age <= max_age_seconds:
        if stale_alerted is not None:  # recovered — re-arm the alert
            _set_stale_alerted(session_factory, None)
        return HealthReport(ok=True, db="ok", poller="ok", last_success_at=last_success)

    detail = (
        f"no successful poll for {int(age)}s "
        f"(limit {max_age_seconds}s = {settings.poller_stale_after_intervals} × "
        f"{settings.poll_interval_seconds}s intervals)"
    )
    if stale_alerted is None:
        sent = send_ops_alert(
            email_sender,
            email_recipients,
            subject="poller is stale",
            body=(
                f"The scheduled poller has not completed a successful tick since "
                f"{last_success.isoformat()} — {detail}.\n"
                f"Check the poller service/container and its last error on the control panel.\n"
            ),
        )
        if sent is not None:
            _set_stale_alerted(session_factory, now)
    return HealthReport(
        ok=False, db="ok", poller="stale", last_success_at=last_success, detail=detail
    )


def _set_stale_alerted(session_factory: sessionmaker[Session], when: datetime | None) -> None:
    with session_scope(session_factory) as session:
        hb = read_heartbeat(session)
        if hb is not None:
            hb.stale_alerted_at = when
