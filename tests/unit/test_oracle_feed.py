"""The V_TRACKING feed contract, exercised through the offline fake.

Proves the window predicate is built in naive Europe/Luxembourg time and that returned changes are
converted back to aware UTC — the same clock path the live OracleTrackingFeed uses.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from tests.fakes import FakeTrackingFeed


def test_window_filter_uses_local_clock_and_returns_utc():
    feed = FakeTrackingFeed()
    # The sample rows are on 2026-06-26 (local). Cover that whole day in UTC.
    start = datetime(2026, 6, 26, 0, 0, tzinfo=UTC)
    end = datetime(2026, 6, 27, 0, 0, tzinfo=UTC)
    changes = feed.changes_in_window(start, end)
    assert changes, "expected sample data-change rows in the day window"
    for c in changes:
        assert c.cre_utc.tzinfo == UTC
        assert c.change_type in {"C", "U", "D"}


def test_changes_are_chronological():
    feed = FakeTrackingFeed()
    start = datetime(2026, 6, 25, 0, 0, tzinfo=UTC)
    end = datetime(2026, 6, 27, 0, 0, tzinfo=UTC)
    changes = feed.changes_in_window(start, end)
    assert changes == sorted(changes, key=lambda c: c.cre_utc)


def test_empty_window_returns_nothing():
    feed = FakeTrackingFeed()
    # The #1702 run window itself (19:01-20:41 local) had no tracked changes.
    start = datetime(2026, 6, 26, 17, 1, tzinfo=UTC)
    end = datetime(2026, 6, 26, 18, 42, tzinfo=UTC)
    assert feed.changes_in_window(start, end) == []


def test_fall_back_night_change_before_window_end_is_not_excluded(tmp_path):
    # Issue #87: fall-back night 2025-10-26 (Europe/Luxembourg) — local 02:00-03:00 occurs twice.
    # A change at 00:40 UTC stores CREDATIM 02:40 (first pass, CEST); the window ends 01:25 UTC =
    # naive 02:25 (second pass, CET). With plain conversion 02:40 > 02:25 and the change — 45 min
    # BEFORE the window end — silently never became a candidate. The fold-safe bounds keep it.
    row = {
        "SESSIONLOGID": 1,
        "LXTABLECODE": "LORDER",
        "PKLST": "1",
        "LXTABLECODEREF": None,
        "PKLSTREF": None,
        "TYPE": "U",
        "COMPONENTNAME": "LORDER_CSVC",
        "CREDATIM": "2025-10-26T02:40:00",
        "UPDDATIM": None,
        "USRIDCRE": 1,
        "USRCODE": "ABC",
    }
    fixture = tmp_path / "v_tracking_fall_back.json"
    fixture.write_text(json.dumps({"rows": [row]}))
    feed = FakeTrackingFeed(fixture)
    start = datetime(2025, 10, 25, 13, 25, tzinfo=UTC)  # 12h lookback before the end
    end = datetime(2025, 10, 26, 1, 25, tzinfo=UTC)
    changes = feed.changes_in_window(start, end)
    assert len(changes) == 1
    # Ambiguous CREDATIM 02:40 reads as the first occurrence (CEST) -> the true 00:40 UTC.
    assert changes[0].cre_utc == datetime(2025, 10, 26, 0, 40, tzinfo=UTC)


def test_no_moddata_leaks_into_feed():
    feed = FakeTrackingFeed()
    start = datetime(2026, 6, 25, 0, 0, tzinfo=UTC)
    end = datetime(2026, 6, 27, 0, 0, tzinfo=UTC)
    for c in feed.changes_in_window(start, end):
        assert not hasattr(c, "moddata")
        assert "MODDATA" not in vars(c)
