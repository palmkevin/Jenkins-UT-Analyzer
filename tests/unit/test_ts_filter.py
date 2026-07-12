"""Unit tests for the ``ts`` timestamp display filter (issues #35, #144).

Timestamps must render to seconds precision — no microseconds — with an explicit `` UTC`` label
(readers are in Luxembourg, UTC+1/+2, so an unlabelled wall-clock string is silently ambiguous)
and the full ISO-8601 form (with offset) in a hover ``title``. The visible text stays ordinary,
wrappable text (no ``&nbsp;`` / ``white-space:nowrap``).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from markupsafe import Markup

from uta.web.app import _TEMPLATES, format_ts


def test_formats_aware_datetime_to_seconds_precision_with_utc_label():
    # A tz-aware UTC datetime with microseconds — the exact shape the ticket complained about.
    dt = datetime(2026, 6, 29, 16, 15, 46, 142000, tzinfo=UTC)
    assert ">2026-06-29 16:15:46 UTC</span>" in format_ts(dt)


def test_title_carries_full_iso_timestamp_with_offset():
    dt = datetime(2026, 6, 29, 16, 15, 46, 142000, tzinfo=UTC)
    assert '<span title="2026-06-29T16:15:46+00:00">' in format_ts(dt)


def test_naive_datetime_treated_as_utc():
    # SQLite (offline tests) drops tzinfo; a naive timestamp must still label + offset as UTC.
    dt = datetime(2026, 6, 29, 16, 15, 46)
    out = format_ts(dt)
    assert ">2026-06-29 16:15:46 UTC</span>" in out
    assert 'title="2026-06-29T16:15:46+00:00"' in out


def test_non_utc_offset_is_preserved_in_title():
    dt = datetime(2026, 6, 29, 18, 15, 46, tzinfo=timezone(timedelta(hours=2)))
    assert 'title="2026-06-29T18:15:46+02:00"' in format_ts(dt)


def test_output_is_safe_markup_not_escaped():
    # Returned as Markup so Jinja autoescaping leaves the <span> intact.
    assert isinstance(format_ts(datetime(2026, 6, 29, 16, 15, 46, tzinfo=UTC)), Markup)


def test_none_falls_back_to_dash():
    assert format_ts(None) == "—"


def test_non_datetime_falls_through_to_str():
    assert format_ts("already a string") == "already a string"


def test_visible_text_is_plain_wrappable_text():
    dt = datetime(2026, 6, 29, 16, 15, 46, 142000, tzinfo=UTC)
    out = format_ts(dt)
    # The date/time separator is an ordinary breakable space, not a non-breaking join, and there
    # is no forced-nowrap markup — so the browser is free to wrap it.
    assert "2026-06-29 16:15:46 UTC" in out  # ordinary spaces present
    assert "\xa0" not in out  # no non-breaking space
    assert "&nbsp;" not in out
    assert "nowrap" not in out


def test_filter_registered_on_templates_env():
    assert _TEMPLATES.env.filters.get("ts") is format_ts
