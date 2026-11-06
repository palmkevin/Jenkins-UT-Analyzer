"""In-app control panel: tunable overrides, on-demand ingest jobs, poller heartbeat (issue #16)."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from tests.fakes import FakeJenkinsClient
from uta.config import Settings
from uta.control.heartbeat import read_heartbeat, record_heartbeat
from uta.control.jobs import (
    IngestGapError,
    create_ingest_job,
    first_unreached_build,
    run_ingest_job,
    trigger_ingest,
)
from uta.control.tunables import (
    TUNABLES_BY_KEY,
    clear_override,
    effective_settings,
    load_overrides,
    set_override,
)
from uta.db import session_scope
from uta.models import Build, IngestJob, SettingOverride
from uta.models.enums import IngestJobStatus
from uta.poller import builds_to_ingest, poll_once, poll_tick


class _MultiBuildFake(FakeJenkinsClient):
    """Serves the #1702 golden fixtures for any build number (configurable last-completed)."""

    def __init__(self, last_completed: int = 2) -> None:
        super().__init__()
        self._last_completed = last_completed

    def _load(self, name: str, build: int) -> dict:
        return super()._load(name, self._build)

    def stage_describe(self, build: int, node_id: str) -> dict:
        return super().stage_describe(self._build, node_id)

    def stage_log(self, build: int, node_id: str) -> dict:
        return super().stage_log(self._build, node_id)

    def last_completed_build(self) -> int | None:
        return self._last_completed


# ── Tunable coercion / validation ────────────────────────────────────────────


def test_int_tunable_coerces_and_bounds():
    t = TUNABLES_BY_KEY["kb_top_k"]
    assert t.coerce("5") == 5
    assert t.coerce(7) == 7
    with pytest.raises(ValueError, match="between"):
        t.coerce("0")  # below minimum (1)
    with pytest.raises(ValueError, match="between"):
        t.coerce("999")  # above maximum (50)
    with pytest.raises(ValueError, match="integer"):
        t.coerce("abc")


def test_float_tunable_coerces_and_bounds():
    t = TUNABLES_BY_KEY["flaky_transition_threshold"]
    assert t.coerce("0.4") == pytest.approx(0.4)
    with pytest.raises(ValueError, match="between"):
        t.coerce("1.5")
    with pytest.raises(ValueError, match="number"):
        t.coerce("nope")


# ── Override CRUD + effective settings ───────────────────────────────────────


def test_set_load_and_clear_override(session_factory):
    with session_scope(session_factory) as s:
        set_override(s, "flaky_window_days", "45", actor="kevin")
    with session_scope(session_factory) as s:
        assert load_overrides(s) == {"flaky_window_days": "45"}
        row = s.get(SettingOverride, "flaky_window_days")
        assert row.value == "45" and row.updated_by == "kevin"
    with session_scope(session_factory) as s:
        clear_override(s, "flaky_window_days")
    with session_scope(session_factory) as s:
        assert load_overrides(s) == {}


def test_set_override_rejects_non_whitelisted_key(session_factory):
    with session_scope(session_factory) as s:
        with pytest.raises(ValueError, match="not an overridable setting"):
            set_override(s, "database_url", "postgres://evil")
        with pytest.raises(ValueError, match="not an overridable setting"):
            set_override(s, "anthropic_api_key", "sk-leak")
    with session_scope(session_factory) as s:
        assert s.scalar(select(func.count()).select_from(SettingOverride)) == 0


def test_set_override_validates_bounds(session_factory):
    with session_scope(session_factory) as s:
        with pytest.raises(ValueError):
            set_override(s, "expected_tracks", "99")
        # A rejected override is never persisted.
        assert s.scalar(select(func.count()).select_from(SettingOverride)) == 0


def test_effective_settings_applies_and_reverts():
    base = Settings(flaky_window_days=30, kb_top_k=5)
    merged = effective_settings(base, {"flaky_window_days": "45", "kb_top_k": "8"})
    assert merged.flaky_window_days == 45
    assert merged.kb_top_k == 8
    # Base is untouched (copy semantics) and a property still derives from it.
    assert base.flaky_window_days == 30
    assert effective_settings(base, {}).flaky_window_days == 30


def test_effective_settings_skips_unknown_and_corrupt_overrides():
    base = Settings(flaky_window_days=30, expected_tracks=2)
    # An unknown key and an out-of-bounds/garbage value are both ignored — the default stands.
    merged = effective_settings(
        base,
        {"not_a_setting": "1", "expected_tracks": "999", "flaky_window_days": "12"},
    )
    assert merged.expected_tracks == 2  # corrupt value skipped
    assert merged.flaky_window_days == 12  # valid one applied


def test_non_overridable_secret_is_preserved_through_merge():
    base = Settings(anthropic_api_key="secret", jenkins_base_url="https://j")
    merged = effective_settings(base, {"kb_top_k": "9"})
    assert merged.anthropic_api_key == "secret"
    assert merged.jenkins_job_url.startswith("https://j")


# ── Ingest jobs ──────────────────────────────────────────────────────────────


def test_create_ingest_job_normalises_range(session_factory):
    with session_scope(session_factory) as s:
        job = create_ingest_job(s, 5, 3, actor="kevin")
        s.flush()
        assert job.build_start == 3 and job.build_end == 5
        assert job.builds_total == 3
        assert job.status == IngestJobStatus.QUEUED


def test_run_ingest_job_ingests_range_and_finishes(session_factory):
    with session_scope(session_factory) as s:
        job = create_ingest_job(s, 1, 2)
        s.flush()
        job_id = job.id

    run_ingest_job(
        session_factory, job_id, settings=Settings(), client=_MultiBuildFake(), feed=None
    )

    with session_scope(session_factory) as s:
        job = s.get(IngestJob, job_id)
        assert job.status == IngestJobStatus.DONE
        assert job.builds_done == 2
        assert job.finished_at is not None
        # The builds were actually ingested.
        assert s.scalar(select(func.count()).select_from(Build)) == 2


def test_run_ingest_job_records_failure(session_factory):
    class _Boom(_MultiBuildFake):
        def build_meta(self, build: int) -> dict:
            raise RuntimeError("jenkins exploded")

    with session_scope(session_factory) as s:
        job = create_ingest_job(s, 1, 1)
        s.flush()
        job_id = job.id

    run_ingest_job(session_factory, job_id, settings=Settings(), client=_Boom(), feed=None)

    with session_scope(session_factory) as s:
        job = s.get(IngestJob, job_id)
        assert job.status == IngestJobStatus.ERROR
        assert "jenkins exploded" in job.error


def test_trigger_ingest_runs_synchronously_when_asked(session_factory):
    job_id = trigger_ingest(
        session_factory,
        build_start=1,
        build_end=1,
        settings=Settings(),
        client=_MultiBuildFake(),
        feed=None,
        run_in_thread=False,
    )
    with session_scope(session_factory) as s:
        assert s.get(IngestJob, job_id).status == IngestJobStatus.DONE


def test_ingest_job_above_high_water_is_refused(session_factory):
    """Ingesting #5 while the store tops out at #2 would strand #3–#4 below the new high-water
    mark — the poller would never select them (ondemand-ingest-jumps-high-water)."""
    poll_once(_MultiBuildFake(2), session_factory)
    with pytest.raises(IngestGapError, match="#3"):
        trigger_ingest(
            session_factory,
            build_start=5,
            build_end=5,
            settings=Settings(ingest_unittest_stages=False),
            client=_MultiBuildFake(5),
            feed=None,
            run_in_thread=False,
        )
    with session_scope(session_factory) as s:
        assert s.scalar(select(func.count()).select_from(IngestJob)) == 0  # no job row created
    assert builds_to_ingest(_MultiBuildFake(5), session_factory) == [3, 4, 5]


def test_ingest_job_at_or_below_high_water_plus_one_is_allowed(session_factory):
    poll_once(_MultiBuildFake(2), session_factory)
    with session_scope(session_factory) as s:
        assert first_unreached_build(s, 1) is None  # re-ingest of an older build
        assert first_unreached_build(s, 3) is None  # contiguous with the mark
        assert first_unreached_build(s, 4) == 3
        create_ingest_job(s, 3, 9)  # a range starting at mark + 1 never leaves a hole


def test_ingest_gap_ignores_quarantined_builds(session_factory):
    from uta.control.quarantine import quarantine_immediately

    poll_once(_MultiBuildFake(2), session_factory)
    quarantine_immediately(session_factory, 3, "rotated")
    with session_scope(session_factory) as s:
        assert first_unreached_build(s, 4) is None  # #3 is skipped by the poller anyway
        assert first_unreached_build(s, 5) == 4


def test_ingest_gap_allowed_on_empty_store(session_factory):
    with session_scope(session_factory) as s:
        assert first_unreached_build(s, 500) is None


# ── Poller heartbeat + tick ──────────────────────────────────────────────────


def test_record_and_read_heartbeat(session_factory):
    record_heartbeat(session_factory, processed=[7, 8], error=None)
    with session_scope(session_factory) as s:
        hb = read_heartbeat(s)
        assert hb.last_processed_count == 2
        assert hb.last_processed == "7,8"
        assert hb.last_error is None
    # A later error is stamped; a subsequent clean tick keeps the last error visible.
    record_heartbeat(session_factory, processed=[], error="boom")
    record_heartbeat(session_factory, processed=[9], error=None)
    with session_scope(session_factory) as s:
        hb = read_heartbeat(s)
        assert hb.last_processed_count == 1
        assert hb.last_error == "boom"  # sticky until seen


def test_poll_tick_ingests_and_records_heartbeat(session_factory):
    processed = poll_tick(_MultiBuildFake(last_completed=2), session_factory, Settings())
    assert processed == [1, 2]
    with session_scope(session_factory) as s:
        assert read_heartbeat(s).last_processed_count == 2
        assert s.scalar(select(func.count()).select_from(Build)) == 2


def test_poll_tick_swallows_error_and_records_it(session_factory):
    class _Boom(_MultiBuildFake):
        def last_completed_build(self) -> int | None:
            raise RuntimeError("network down")

    # The tick must not raise — a bad tick can't be allowed to kill the long-lived scheduler.
    assert poll_tick(_Boom(), session_factory, Settings()) == []
    with session_scope(session_factory) as s:
        assert "network down" in read_heartbeat(s).last_error


def test_poll_tick_survives_db_down_at_tick_start():
    """A DB blip while loading overrides (and writing the failure heartbeat) is logged, not raised
    — otherwise the poller dies at startup (compose-no-restart-policy)."""
    from sqlalchemy.exc import OperationalError

    def _broken_factory():
        raise OperationalError("connect", {}, Exception("db down"))

    assert poll_tick(_MultiBuildFake(), _broken_factory, Settings()) == []


def test_run_scheduler_survives_a_raising_first_tick(monkeypatch, session_factory):
    import uta.poller as poller

    started: list[bool] = []

    class _FakeScheduler:
        def start(self) -> None:
            started.append(True)

    def _raise(*a, **k):
        raise RuntimeError("first tick blew up")

    monkeypatch.setattr(poller, "poll_tick", _raise)
    monkeypatch.setattr(poller, "build_scheduler", lambda tick, interval: _FakeScheduler())
    poller.run_scheduler(_MultiBuildFake(), session_factory, Settings())
    assert started == [True]  # the scheduler still starts after a failing startup tick


@pytest.mark.parametrize(
    "env",
    [
        "POLL_RETRY_ATTEMPTS",
        "QUARANTINE_AFTER_ATTEMPTS",
        "POLL_INTERVAL_SECONDS",
        "BACKFILL_DEPTH",
    ],
)
@pytest.mark.parametrize("value", ["0", "-1"])
def test_poller_int_settings_must_be_positive(env, value, monkeypatch):
    """0 retry attempts raised AssertionError("unreachable") every tick (config-int-validation)."""
    from pydantic import ValidationError

    monkeypatch.setenv(env, value)
    with pytest.raises(ValidationError, match="greater than or equal to 1"):
        Settings()
    monkeypatch.setenv(env, "1")
    assert getattr(Settings(), env.lower()) == 1
