"""Expected Duration — the reference wall-clock a build is expected to take (issue #184).

The **median** end-to-end (``finished_at − started_at``) wall-clock of the most recent
:data:`SAMPLE_SIZE` ``SUCCESS``/``UNSTABLE`` builds. It is the shared yardstick for both the
overrunning (in-progress) detector here and the future slow (completed) detector — so it lives in
one place. **Undefined (``None``) until that many green builds exist**: a small sample would make a
noisy median, and the overrunning banner must not highlight against a baseline it can't trust
(CONTEXT.md: *Expected Duration*).
"""

from __future__ import annotations

from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from uta.analyze.incident import GREEN_RESULTS
from uta.models import Build

#: How many recent green builds the median is taken over. Matches CONTEXT.md's "last 20".
SAMPLE_SIZE = 20


def _median(values: list[float]) -> float:
    """The median of a non-empty, already-sorted-agnostic list (sorts a copy)."""
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def expected_duration_seconds(session: Session, *, sample_size: int = SAMPLE_SIZE) -> float | None:
    """Median wall-clock (seconds) of the last ``sample_size`` green builds, or ``None``.

    Green means ``SUCCESS``/``UNSTABLE`` (:data:`~uta.analyze.incident.GREEN_RESULTS`), the same
    set the incident feed treats as a recovery. Builds are taken newest-first by ``started_at`` and
    the median is computed only when at least ``sample_size`` of them exist — fewer ⇒ ``None`` (the
    detector then never flags, and the banner omits "expected").
    """
    rows = session.execute(
        select(Build.started_at, Build.finished_at)
        .where(Build.status.in_(GREEN_RESULTS))
        .order_by(Build.started_at.desc(), Build.id.desc())
        .limit(sample_size)
    ).all()
    if len(rows) < sample_size:
        return None
    durations: list[float] = []
    for started_at, finished_at in rows:
        if started_at is None or finished_at is None:
            continue
        start = started_at if started_at.tzinfo is not None else started_at.replace(tzinfo=UTC)
        finish = finished_at if finished_at.tzinfo is not None else finished_at.replace(tzinfo=UTC)
        durations.append(max(0.0, (finish - start).total_seconds()))
    if len(durations) < sample_size:
        return None
    return _median(durations)
