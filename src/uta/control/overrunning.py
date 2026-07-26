"""The poller's overrunning-build observation — the single source of truth (issue #184).

Each poll tick the poller observes Jenkins' current in-progress build and writes a **single-row
snapshot** onto the poller heartbeat: the build's number/start, the Expected Duration median, and a
poller-computed ``overrunning`` flag. The web tier reads that snapshot like everything else and
computes only ``elapsed`` live at render — so the dashboard stays a pure reflection of stored facts
and never queries Jenkins (ADR-0006). An **Overrunning Build is never a Build Incident**; the
durable record only ever comes from the ``aborted`` incident if a human stops the build.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from uta.analyze.duration import expected_duration_seconds
from uta.ingest.jenkins import LastBuild
from uta.models import PollerHeartbeat

_HEARTBEAT_ID = 1


@dataclass(frozen=True)
class OverrunAlert:
    """A newly-overrunning build the poller should email exactly one alert for."""

    build_number: int
    started_at: datetime
    expected_seconds: float | None
    elapsed_seconds: float


def _get_or_create(session: Session) -> PollerHeartbeat:
    hb = session.get(PollerHeartbeat, _HEARTBEAT_ID)
    if hb is None:
        hb = PollerHeartbeat(id=_HEARTBEAT_ID)
        session.add(hb)
    return hb


def _clear(hb: PollerHeartbeat) -> None:
    """No in-progress build (or detection off) → wipe the snapshot so the banner disappears."""
    hb.overrunning_build_number = None
    hb.overrunning_started_at = None
    hb.overrunning_expected_seconds = None
    hb.overrunning_building = False
    hb.overrunning = False
    hb.overrunning_alerted_build_number = None


def observe_overrunning(
    session: Session,
    last_build: LastBuild | None,
    *,
    overrun_ratio: float,
    detect: bool,
    now: datetime | None = None,
) -> OverrunAlert | None:
    """Compute + persist the overrunning snapshot for one tick; return an alert to send, if any.

    With detection off or no build currently ``building``, the snapshot is cleared (the banner
    goes away). Otherwise the build is **overrunning** when its elapsed time
    (``now − started_at``) exceeds ``expected × (1 + overrun_ratio)`` — and only when a full
    Expected Duration baseline exists (:func:`expected_duration_seconds` returns ``None`` with too
    few green builds, so it never flags). Returns an :class:`OverrunAlert` exactly once per
    overrunning build: the persisted ``overrunning_alerted_build_number`` marker de-dups across
    ticks and survives a poller restart, and it resets when the in-progress build changes or
    finishes — so the eventual aborted incident stays silent (no double alert).
    """
    now = now or datetime.now(UTC)
    hb = _get_or_create(session)

    if not detect or last_build is None or not last_build.building:
        _clear(hb)
        return None

    started_at = datetime.fromtimestamp(last_build.timestamp / 1000, tz=UTC)
    expected = expected_duration_seconds(session)
    elapsed = max(0.0, (now - started_at).total_seconds())
    overrunning = expected is not None and elapsed > expected * (1 + overrun_ratio)

    hb.overrunning_build_number = last_build.number
    hb.overrunning_started_at = started_at
    hb.overrunning_expected_seconds = expected
    hb.overrunning_building = True
    hb.overrunning = overrunning

    if overrunning and hb.overrunning_alerted_build_number != last_build.number:
        hb.overrunning_alerted_build_number = last_build.number
        return OverrunAlert(
            build_number=last_build.number,
            started_at=started_at,
            expected_seconds=expected,
            elapsed_seconds=elapsed,
        )
    return None
