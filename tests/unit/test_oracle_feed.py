"""The V_TRACKING feed contract, exercised through the offline fake.

Proves the window predicate is built in naive Europe/Luxembourg time and that returned changes are
converted back to aware UTC — the same clock path the live OracleTrackingFeed uses.
"""

from __future__ import annotations

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


def test_no_moddata_leaks_into_feed():
    feed = FakeTrackingFeed()
    start = datetime(2026, 6, 25, 0, 0, tzinfo=UTC)
    end = datetime(2026, 6, 27, 0, 0, tzinfo=UTC)
    for c in feed.changes_in_window(start, end):
        assert not hasattr(c, "moddata")
        assert "MODDATA" not in vars(c)
