"""AI-suggestion accuracy — the confirmed-vs-corrected precision signal (issue #73).

The triage actions already record everything needed to score the AI: a **Confirm** stamps
``AI_CONFIRMED`` provenance (the human accepted the suggestion), a correction stamps
``HUMAN_CORRECTED`` and retains the original AI value (``original_ai_cause`` /
``original_ai_reason``) alongside the human's. This module just counts those verdicts —
per conclusion field (cause vs reason), all-time and over a recent window — and derives

    precision = confirmed / (confirmed + corrected)

``HUMAN_ENTERED`` conclusions are deliberately excluded: with no AI suggestion in play there was
nothing to confirm or correct, so they say nothing about AI quality. Pure read-side projection
(plain dicts, the Slice-0 pattern) consumed by the control panel.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from uta.models import Attribution
from uta.models.enums import Provenance

DEFAULT_WINDOW_DAYS = 30


def _bucket(confirmed: int, corrected: int) -> dict:
    total = confirmed + corrected
    return {
        "confirmed": confirmed,
        "corrected": corrected,
        "total": total,
        "precision": round(confirmed / total, 3) if total else None,
    }


def _count(
    session: Session,
    provenance_column,
    value_column,
    provenance: str,
    since: datetime | None,
) -> int:
    stmt = (
        select(func.count())
        .select_from(Attribution)
        .where(provenance_column == provenance, value_column.isnot(None))
    )
    if since is not None:
        stmt = stmt.where(func.coalesce(Attribution.validated_at, Attribution.created_at) >= since)
    return session.scalar(stmt) or 0


def _field_bucket(
    session: Session, provenance_column, value_column, since: datetime | None
) -> dict:
    return _bucket(
        _count(session, provenance_column, value_column, Provenance.AI_CONFIRMED, since),
        _count(session, provenance_column, value_column, Provenance.HUMAN_CORRECTED, since),
    )


def ai_accuracy(
    session: Session, *, window_days: int = DEFAULT_WINDOW_DAYS, now: datetime | None = None
) -> dict:
    """Confirmed-vs-corrected counts + precision per conclusion field, all-time and recent.

    ``cause`` scores the suggested contact (``causing_person`` vs the AI's suggestion), ``reason``
    the LLM hypothesis. ``recent`` applies a ``window_days`` cutoff on the validation timestamp.
    """
    now = now or datetime.now(UTC)
    since = now - timedelta(days=window_days)
    cause_cols = (Attribution.cause_provenance, Attribution.causing_person)
    reason_cols = (Attribution.reason_provenance, Attribution.reason_text)
    all_time = {
        "cause": _field_bucket(session, *cause_cols, None),
        "reason": _field_bucket(session, *reason_cols, None),
    }
    recent = {
        "cause": _field_bucket(session, *cause_cols, since),
        "reason": _field_bucket(session, *reason_cols, since),
    }
    return {
        "window_days": window_days,
        "all_time": all_time,
        "recent": recent,
        "has_data": bool(all_time["cause"]["total"] or all_time["reason"]["total"]),
    }
