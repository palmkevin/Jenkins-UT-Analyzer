"""Unit tests for the ``reltime`` relative-timestamp display filter (issue #79).

Where age matters (triage first-failed/fixed-at, test-record lifecycle/episode times) timestamps
render as coarse relative text ("2 days ago") with the absolute form in a hover ``title`` — pure
server-side markup, no JS.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from markupsafe import Markup

from uta.web.app import _TEMPLATES, format_reltime


def _ago(**kwargs) -> datetime:
    return datetime.now(UTC) - timedelta(**kwargs)


def test_just_now_under_a_minute():
    assert ">just now<" in format_reltime(_ago(seconds=10))


def test_minutes():
    assert ">5 min ago<" in format_reltime(_ago(minutes=5, seconds=5))


def test_hours():
    assert ">3 h ago<" in format_reltime(_ago(hours=3, minutes=1))


def test_days_plural():
    assert ">2 days ago<" in format_reltime(_ago(days=2, minutes=1))


def test_one_day_singular():
    assert ">1 day ago<" in format_reltime(_ago(days=1, minutes=1))


def test_future_renders_as_in():
    assert ">in 3 h<" in format_reltime(datetime.now(UTC) + timedelta(hours=3, minutes=1))


def test_absolute_timestamp_in_title_tooltip():
    dt = _ago(days=2, minutes=1)
    out = format_reltime(dt)
    # The hover title carries the absolute form, explicitly labelled UTC (issue #144).
    assert f'<span title="{dt.strftime("%Y-%m-%d %H:%M:%S")} UTC">' in out


def test_output_is_safe_markup_not_escaped():
    # Returned as Markup so Jinja autoescaping leaves the <span> intact.
    assert isinstance(format_reltime(_ago(hours=1, minutes=1)), Markup)


def test_naive_datetime_treated_as_utc():
    # SQLite (offline tests) drops tzinfo; a naive timestamp must not be misread as local time.
    naive = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=3, minutes=1)
    assert ">3 h ago<" in format_reltime(naive)


def test_none_falls_back_to_dash():
    assert format_reltime(None) == "—"


def test_non_datetime_falls_through_to_str():
    assert format_reltime("already a string") == "already a string"


def test_filter_registered_on_templates_env():
    assert _TEMPLATES.env.filters.get("reltime") is format_reltime
