"""Clock discipline — the riskiest assumption, so the most thorough tests.

Pins the empirically-confirmed facts: Jenkins millis are UTC; ut_ref CREDATIM is naive
Europe/Luxembourg; conversion is DST-aware (NOT a fixed +2).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from uta.ingest.clock import (
    from_jenkins_millis,
    from_ut_ref_local,
    to_ut_ref_local,
)


def test_jenkins_millis_are_utc():
    # 1782493274808 ms == 2026-06-26 17:01:14.808 UTC (build #1702 start).
    dt = from_jenkins_millis(1782493274808)
    assert dt.tzinfo == UTC
    assert dt == datetime(2026, 6, 26, 17, 1, 14, 808000, tzinfo=UTC)


def test_ut_ref_summer_is_utc_plus_2():
    # CEST: naive local 19:01 -> 17:01 UTC (a real #1702-era timestamp).
    local = datetime(2026, 6, 26, 19, 1, 14)
    assert from_ut_ref_local(local) == datetime(2026, 6, 26, 17, 1, 14, tzinfo=UTC)


def test_ut_ref_winter_is_utc_plus_1():
    # CET: naive local 12:00 in January -> 11:00 UTC. A fixed +2 would be wrong here.
    local = datetime(2026, 1, 15, 12, 0, 0)
    assert from_ut_ref_local(local) == datetime(2026, 1, 15, 11, 0, 0, tzinfo=UTC)


def test_dst_is_not_a_fixed_offset():
    summer = from_ut_ref_local(datetime(2026, 7, 1, 12, 0, 0))
    winter = from_ut_ref_local(datetime(2026, 1, 1, 12, 0, 0))
    # Same wall-clock, different UTC -> proves DST-aware conversion.
    assert summer.hour == 10  # CEST: -2
    assert winter.hour == 11  # CET:  -1


def test_round_trip_utc_to_local_to_utc():
    utc = datetime(2026, 6, 26, 17, 1, 14, tzinfo=UTC)
    assert from_ut_ref_local(to_ut_ref_local(utc)) == utc


def test_to_ut_ref_local_builds_naive_predicate_bounds():
    utc = datetime(2026, 6, 26, 17, 1, 14, tzinfo=UTC)
    local = to_ut_ref_local(utc)
    assert local.tzinfo is None
    assert local == datetime(2026, 6, 26, 19, 1, 14)


def test_from_ut_ref_local_rejects_aware_input():
    with pytest.raises(ValueError):
        from_ut_ref_local(datetime(2026, 6, 26, 19, 0, 0, tzinfo=UTC))


def test_to_ut_ref_local_rejects_naive_input():
    with pytest.raises(ValueError):
        to_ut_ref_local(datetime(2026, 6, 26, 19, 0, 0))
