"""Live Oracle ut_ref checks — LOCAL ONLY (needs network to Oracle). Never run in CI.

Pins the empirically-proven timezone behaviour: a naive-local ``CREDATIM`` round-trips through the
feed to the correct UTC instant (the #1702 day's latest tracked change is 15:46 local == 13:46 UTC).

Run with: ``pytest -m live tests/live/test_oracle_live.py``
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from uta.config import get_settings
from uta.refdb.oracle import OracleTrackingFeed

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def feed():
    s = get_settings()
    return OracleTrackingFeed(
        s.ut_ref_host,
        s.ut_ref_port,
        s.ut_ref_service,
        s.ut_ref_user,
        s.ut_ref_password,
        thick=s.ut_ref_thick,
    )


def test_live_window_returns_candidates_converted_to_utc(feed):
    # #1702 day, with lookback (changes precede the nightly run).
    start = datetime(2026, 6, 26, 5, 8, tzinfo=UTC)
    end = datetime(2026, 6, 26, 18, 42, tzinfo=UTC)
    changes = feed.changes_in_window(start, end)
    assert changes, "expected data-change candidates in the #1702 day window"
    assert all(c.cre_utc.tzinfo == UTC for c in changes)
    assert changes == sorted(changes, key=lambda c: c.cre_utc)
    # Proven tz fact: latest change stored as naive-local 15:46 -> 13:46 UTC.
    assert changes[-1].cre_utc == datetime(2026, 6, 26, 13, 46, 17, tzinfo=UTC)
    assert all(c.change_type in {"C", "U", "D"} for c in changes)
