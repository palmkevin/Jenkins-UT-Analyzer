"""Overrunning in-progress builds (issue #184): Expected Duration median, the poller's snapshot
observation + one-email de-dup, the dashboard banner projection, and the alert email builder.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from uta.analyze.duration import expected_duration_seconds
from uta.control.heartbeat import read_heartbeat
from uta.control.overrunning import observe_overrunning
from uta.db import session_scope
from uta.delivery.alert import AlertKind
from uta.delivery.email import build_overrun_alert
from uta.ingest.jenkins import LastBuild
from uta.models import Build
from uta.web import views

_ANCHOR = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)


def _add_build(
    session, number: int, *, status: str, duration_minutes: int, start: datetime
) -> None:
    session.add(
        Build(
            build_number=number,
            status=status,
            started_at=start,
            finished_at=start + timedelta(minutes=duration_minutes),
            complete=True,
        )
    )


def _seed_green_builds(session_factory, count: int, *, duration_minutes: int = 60) -> None:
    """`count` SUCCESS builds, each `duration_minutes` long, staggered oldest-first."""
    with session_scope(session_factory) as s:
        for i in range(count):
            _add_build(
                s,
                1000 + i,
                status="SUCCESS",
                duration_minutes=duration_minutes,
                start=_ANCHOR - timedelta(days=count - i),
            )


def _last_build(number: int, *, building: bool, started_at: datetime) -> LastBuild:
    return LastBuild(number=number, building=building, timestamp=int(started_at.timestamp() * 1000))


# ── Expected Duration median ─────────────────────────────────────────────────


def test_expected_duration_undefined_below_sample(session_factory):
    _seed_green_builds(session_factory, 19, duration_minutes=60)
    with session_scope(session_factory) as s:
        assert expected_duration_seconds(s) is None


def test_expected_duration_is_median_of_last_20_green(session_factory):
    _seed_green_builds(session_factory, 20, duration_minutes=60)
    with session_scope(session_factory) as s:
        assert expected_duration_seconds(s) == 3600.0


def test_expected_duration_ignores_non_green_builds(session_factory):
    # 20 green (60 min) + a FAILURE/ABORTED that must not enter the median.
    _seed_green_builds(session_factory, 20, duration_minutes=60)
    with session_scope(session_factory) as s:
        _add_build(s, 2001, status="FAILURE", duration_minutes=600, start=_ANCHOR)
        _add_build(s, 2002, status="ABORTED", duration_minutes=600, start=_ANCHOR)
    with session_scope(session_factory) as s:
        # Only the 20 green count → still 20 samples, median unchanged; the long non-green
        # builds are excluded (else the median would move).
        assert expected_duration_seconds(s) == 3600.0


# ── The poller's observation (single source of truth) ────────────────────────


def test_no_building_build_clears_snapshot_and_no_alert(session_factory):
    _seed_green_builds(session_factory, 20)
    with session_scope(session_factory) as s:
        alert = observe_overrunning(
            s, _last_build(1100, building=False, started_at=_ANCHOR), overrun_ratio=1.0, detect=True
        )
        assert alert is None
    with session_scope(session_factory) as s:
        hb = read_heartbeat(s)
        assert hb is not None and hb.overrunning_building is False
        assert hb.overrunning is False and hb.overrunning_build_number is None


def test_in_progress_below_threshold_stores_snapshot_not_flagged(session_factory):
    _seed_green_builds(session_factory, 20, duration_minutes=60)  # median 3600s
    now = _ANCHOR + timedelta(minutes=90)  # elapsed 90 min < 2×60
    with session_scope(session_factory) as s:
        alert = observe_overrunning(
            s,
            _last_build(1100, building=True, started_at=_ANCHOR),
            overrun_ratio=1.0,
            detect=True,
            now=now,
        )
        assert alert is None
    with session_scope(session_factory) as s:
        hb = read_heartbeat(s)
        assert hb.overrunning_building is True and hb.overrunning is False
        assert hb.overrunning_build_number == 1100
        assert hb.overrunning_expected_seconds == 3600.0


def test_overrunning_flags_and_alerts_once(session_factory):
    _seed_green_builds(session_factory, 20, duration_minutes=60)  # median 3600s → threshold 2×
    now = _ANCHOR + timedelta(minutes=150)  # elapsed 150 min > 120 min threshold
    lb = _last_build(1100, building=True, started_at=_ANCHOR)
    with session_scope(session_factory) as s:
        alert = observe_overrunning(s, lb, overrun_ratio=1.0, detect=True, now=now)
        assert alert is not None
        assert alert.build_number == 1100
        assert alert.expected_seconds == 3600.0
        assert alert.elapsed_seconds == 150 * 60
    with session_scope(session_factory) as s:
        hb = read_heartbeat(s)
        assert hb.overrunning is True
        assert hb.overrunning_alerted_build_number == 1100
    # A second tick on the *same* build must not re-alert (de-duped by the persisted marker).
    with session_scope(session_factory) as s:
        again = observe_overrunning(s, lb, overrun_ratio=1.0, detect=True, now=now)
        assert again is None
    with session_scope(session_factory) as s:
        assert read_heartbeat(s).overrunning is True


def test_new_in_progress_build_re_alerts(session_factory):
    _seed_green_builds(session_factory, 20, duration_minutes=60)
    now = _ANCHOR + timedelta(minutes=150)
    with session_scope(session_factory) as s:
        assert (
            observe_overrunning(
                s,
                _last_build(1100, building=True, started_at=_ANCHOR),
                overrun_ratio=1.0,
                detect=True,
                now=now,
            )
            is not None
        )
    # A *different* build number that is also overrunning gets its own single alert.
    with session_scope(session_factory) as s:
        alert = observe_overrunning(
            s,
            _last_build(1101, building=True, started_at=_ANCHOR),
            overrun_ratio=1.0,
            detect=True,
            now=now,
        )
        assert alert is not None and alert.build_number == 1101


def test_below_baseline_never_flags_even_if_slow(session_factory):
    _seed_green_builds(session_factory, 5, duration_minutes=60)  # < 20 → Expected Duration None
    now = _ANCHOR + timedelta(hours=10)  # very long, but no baseline to compare against
    with session_scope(session_factory) as s:
        alert = observe_overrunning(
            s,
            _last_build(1100, building=True, started_at=_ANCHOR),
            overrun_ratio=1.0,
            detect=True,
            now=now,
        )
        assert alert is None
    with session_scope(session_factory) as s:
        hb = read_heartbeat(s)
        # Banner still shows (building), elapsed available, but expected omitted + never flagged.
        assert hb.overrunning_building is True
        assert hb.overrunning is False
        assert hb.overrunning_expected_seconds is None


def test_detection_off_clears_snapshot(session_factory):
    _seed_green_builds(session_factory, 20)
    now = _ANCHOR + timedelta(minutes=150)
    with session_scope(session_factory) as s:
        observe_overrunning(
            s,
            _last_build(1100, building=True, started_at=_ANCHOR),
            overrun_ratio=1.0,
            detect=True,
            now=now,
        )
    # Detection turned off → the snapshot is wiped so the banner disappears next tick.
    with session_scope(session_factory) as s:
        observe_overrunning(s, None, overrun_ratio=1.0, detect=False, now=now)
    with session_scope(session_factory) as s:
        hb = read_heartbeat(s)
        assert hb.overrunning_building is False and hb.overrunning_build_number is None


# ── The dashboard banner projection ──────────────────────────────────────────


def test_banner_none_when_nothing_building(session_factory):
    with session_scope(session_factory) as s:
        assert views.overrunning_banner(s) is None  # no heartbeat at all


def test_banner_reflects_stored_snapshot_with_jenkins_link(session_factory):
    _seed_green_builds(session_factory, 20, duration_minutes=60)
    now = _ANCHOR + timedelta(minutes=150)
    with session_scope(session_factory) as s:
        observe_overrunning(
            s,
            _last_build(1100, building=True, started_at=_ANCHOR),
            overrun_ratio=1.0,
            detect=True,
            now=now,
        )
    with session_scope(session_factory) as s:
        banner = views.overrunning_banner(s, jenkins_job_url="https://jenkins.example/job/x/")
        assert banner is not None
        assert banner["build_number"] == 1100
        assert banner["overrunning"] is True
        assert banner["expected_seconds"] == 3600.0
        assert banner["jenkins_url"] == "https://jenkins.example/job/x/1100/"


# ── The alert email builder ──────────────────────────────────────────────────


def test_overrun_alert_contents():
    alert = build_overrun_alert(
        1100,
        elapsed_seconds=9000,
        expected_seconds=3600,
        jenkins_build_url="https://jenkins.example/job/x/1100/",
        app_base_url="http://uta.example",
    )
    assert alert.kind is AlertKind.overrun
    assert "#1100" in alert.title
    assert "2h 30m" in alert.body  # 9000s elapsed
    assert "1h" in alert.body  # 3600s expected
    assert "https://jenkins.example/job/x/1100/" in alert.body
    assert "Dashboard: http://uta.example/" in alert.body


def test_overrun_alert_without_baseline_says_unknown():
    alert = build_overrun_alert(1100, elapsed_seconds=9000, expected_seconds=None)
    assert "unknown" in alert.body  # expected omitted → "unknown"


# ── The poller tick wiring (fetch lastBuild → observe → email once) ──────────


class _InProgressJenkins:
    """A minimal client whose ``lastBuild`` is a long-running in-progress build."""

    def __init__(self, number: int, started_at: datetime) -> None:
        self._number = number
        self._started_at = started_at

    def last_build(self) -> LastBuild:
        return _last_build(self._number, building=True, started_at=self._started_at)


def test_observe_overrunning_tick_alerts_once(session_factory):
    from tests.fakes.alert import RecordingAlertChannel
    from uta.config import Settings
    from uta.poller import observe_overrunning_tick

    _seed_green_builds(session_factory, 20, duration_minutes=60)
    client = _InProgressJenkins(1100, _ANCHOR)
    channel = RecordingAlertChannel()
    cfg = Settings(detect_overrunning_builds=True, overrun_ratio=1.0)
    now = _ANCHOR + timedelta(minutes=150)

    observe_overrunning_tick(client, session_factory, cfg, channels=[channel], now=now)
    observe_overrunning_tick(client, session_factory, cfg, channels=[channel], now=now)
    overrun_alerts = [a for a in channel.sent if "overrunning build" in a.title]
    assert len(overrun_alerts) == 1  # de-duped across ticks
    with session_scope(session_factory) as s:
        assert read_heartbeat(s).overrunning is True
