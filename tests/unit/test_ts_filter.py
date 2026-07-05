"""Unit tests for the ``ts`` timestamp display filter (issue #35).

Timestamps must render to seconds precision — no microseconds, no ``+00:00`` tz suffix — as
ordinary wrappable text (no ``&nbsp;`` / ``white-space:nowrap``).
"""

from __future__ import annotations

from datetime import UTC, datetime

from uta.web.app import _TEMPLATES, format_ts


def test_formats_aware_datetime_to_seconds_precision():
    # A tz-aware UTC datetime with microseconds — the exact shape the ticket complained about.
    dt = datetime(2026, 6, 29, 16, 15, 46, 142000, tzinfo=UTC)
    assert format_ts(dt) == "2026-06-29 16:15:46"


def test_formats_naive_datetime():
    dt = datetime(2026, 6, 29, 16, 15, 46)
    assert format_ts(dt) == "2026-06-29 16:15:46"


def test_none_falls_back_to_dash():
    assert format_ts(None) == "—"


def test_non_datetime_falls_through_to_str():
    assert format_ts("already a string") == "already a string"


def test_output_is_plain_wrappable_text():
    dt = datetime(2026, 6, 29, 16, 15, 46, 142000, tzinfo=UTC)
    out = format_ts(dt)
    # The date/time separator is an ordinary breakable space, not a non-breaking join, and there
    # is no forced-nowrap markup — so the browser is free to wrap it.
    assert " " in out  # ordinary space present
    assert "\xa0" not in out  # no non-breaking space
    assert "&nbsp;" not in out
    assert "nowrap" not in out


def test_filter_registered_on_templates_env():
    assert _TEMPLATES.env.filters.get("ts") is format_ts
