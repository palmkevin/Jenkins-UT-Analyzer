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
    to_ut_ref_local_window_end,
    to_ut_ref_local_window_start,
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


def test_window_helpers_reject_naive_input():
    for fn in (to_ut_ref_local_window_start, to_ut_ref_local_window_end):
        with pytest.raises(ValueError):
            fn(datetime(2026, 6, 26, 19, 0, 0))


# --- The fall-back fold (issue #87). Real transition: 2025-10-26 Europe/Luxembourg —
# 03:00 CEST jumps back to 02:00 CET at 01:00 UTC, so local 02:00-03:00 occurs twice
# (first pass = 00:00-01:00 UTC, second pass = 01:00-02:00 UTC).


def test_fall_back_window_end_keeps_a_change_before_the_window_end():
    # The issue-#87 scenario: window ends 01:25 UTC (second pass, naive 02:25); a change written
    # 00:40 UTC — 45 minutes BEFORE the end — carries CREDATIM 02:40 (first pass). A plain naive
    # bound (02:25) would exclude it; the fold-safe end widens past it.
    win_end = to_ut_ref_local_window_end(datetime(2025, 10, 26, 1, 25, tzinfo=UTC))
    credatim_of_earlier_change = to_ut_ref_local(datetime(2025, 10, 26, 0, 40, tzinfo=UTC))
    assert credatim_of_earlier_change == datetime(2025, 10, 26, 2, 40)  # first pass, CEST
    assert credatim_of_earlier_change <= win_end
    assert win_end == datetime(2025, 10, 26, 3, 25)  # widened by the repeated hour


def test_fall_back_window_end_in_first_pass_is_not_widened():
    # An end in the FIRST pass needs no widening: everything earlier has a smaller naive value.
    win_end = to_ut_ref_local_window_end(datetime(2025, 10, 26, 0, 40, tzinfo=UTC))
    assert win_end == datetime(2025, 10, 26, 2, 40)


def test_fall_back_window_start_keeps_a_change_after_the_window_start():
    # Mirror image: window starts 00:25 UTC (first pass, naive 02:25); a change written 01:10 UTC
    # — 45 minutes AFTER the start — carries CREDATIM 02:10 (second pass). A plain naive bound
    # (02:25) would exclude it; the fold-safe start widens below it.
    win_start = to_ut_ref_local_window_start(datetime(2025, 10, 26, 0, 25, tzinfo=UTC))
    credatim_of_later_change = to_ut_ref_local(datetime(2025, 10, 26, 1, 10, tzinfo=UTC))
    assert credatim_of_later_change == datetime(2025, 10, 26, 2, 10)  # second pass, CET
    assert win_start <= credatim_of_later_change
    assert win_start == datetime(2025, 10, 26, 1, 25)  # widened by the repeated hour


def test_fall_back_window_start_in_second_pass_is_not_widened():
    # A start in the SECOND pass needs no widening: everything later has a larger naive value.
    win_start = to_ut_ref_local_window_start(datetime(2025, 10, 26, 1, 25, tzinfo=UTC))
    assert win_start == datetime(2025, 10, 26, 2, 25)


def test_window_helpers_match_plain_conversion_on_ordinary_days():
    # Away from the repeated hour the helpers ARE the plain conversion — byte-identical bounds.
    for utc in (
        datetime(2026, 6, 26, 17, 1, 14, tzinfo=UTC),  # summer (CEST)
        datetime(2026, 1, 15, 11, 0, 0, tzinfo=UTC),  # winter (CET)
        datetime(2025, 10, 25, 23, 59, 59, tzinfo=UTC),  # just before the fold
        datetime(2025, 10, 26, 2, 0, 0, tzinfo=UTC),  # just after the fold
        datetime(2026, 3, 29, 1, 30, 0, tzinfo=UTC),  # spring-forward night (no fold)
    ):
        assert to_ut_ref_local_window_start(utc) == to_ut_ref_local(utc)
        assert to_ut_ref_local_window_end(utc) == to_ut_ref_local(utc)


def test_from_ut_ref_local_ambiguous_reads_first_occurrence():
    # Naive 02:30 on the fall-back night happened twice. Documented reading: the FIRST
    # occurrence (CEST -> 00:30 UTC) — erring early keeps a candidate inside its lookback
    # window rather than drifting past the window end.
    assert from_ut_ref_local(datetime(2025, 10, 26, 2, 30)) == datetime(
        2025, 10, 26, 0, 30, tzinfo=UTC
    )


def test_from_ut_ref_local_nonexistent_spring_forward_is_deterministic():
    # 2026-03-29 Europe/Luxembourg: 02:00 CET jumps to 03:00 CEST — local 02:30 never happens
    # (only clock skew / bad data can produce it). Documented reading: the pre-transition offset
    # (CET, +1) -> 01:30 UTC. No crash, deterministic.
    assert from_ut_ref_local(datetime(2026, 3, 29, 2, 30)) == datetime(
        2026, 3, 29, 1, 30, tzinfo=UTC
    )
