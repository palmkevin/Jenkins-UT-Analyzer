"""AI-suggestion accuracy metric (uta.control.ai_accuracy, issue #73).

Built on hand-inserted Attribution rows (the episode FK is unenforced on SQLite and irrelevant to
the aggregate — the metric keys on provenance + the conclusion columns), so each verdict mix is
explicit and offline.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from uta.control.ai_accuracy import ai_accuracy
from uta.db import session_scope
from uta.models import Attribution
from uta.models.enums import Provenance

_NOW = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)


def _attr(
    episode_id: int,
    *,
    causing_person: str | None = None,
    cause_provenance: str = Provenance.AI_UNCONFIRMED,
    reason_text: str | None = None,
    reason_provenance: str = Provenance.AI_UNCONFIRMED,
    validated_at: datetime | None = None,
) -> Attribution:
    return Attribution(
        episode_id=episode_id,
        causing_person=causing_person,
        cause_provenance=cause_provenance,
        reason_text=reason_text,
        reason_provenance=reason_provenance,
        validated_at=validated_at or _NOW - timedelta(days=1),
    )


def test_empty_store_has_no_data(session_factory):
    with session_scope(session_factory) as s:
        acc = ai_accuracy(s, now=_NOW)
        assert acc["has_data"] is False
        assert acc["all_time"]["cause"] == {
            "confirmed": 0,
            "corrected": 0,
            "total": 0,
            "precision": None,
        }


def test_confirmed_vs_corrected_precision_per_field(session_factory):
    with session_scope(session_factory) as s:
        s.add(_attr(1, causing_person="dev-a", cause_provenance=Provenance.AI_CONFIRMED))
        s.add(_attr(2, causing_person="dev-b", cause_provenance=Provenance.AI_CONFIRMED))
        s.add(_attr(3, causing_person="dev-c", cause_provenance=Provenance.HUMAN_CORRECTED))
        s.add(_attr(4, reason_text="flaky fixture", reason_provenance=Provenance.HUMAN_CORRECTED))
    with session_scope(session_factory) as s:
        acc = ai_accuracy(s, now=_NOW)
        assert acc["has_data"] is True
        assert acc["all_time"]["cause"]["confirmed"] == 2
        assert acc["all_time"]["cause"]["corrected"] == 1
        assert acc["all_time"]["cause"]["precision"] == pytest.approx(0.667)
        # The reason verdicts are scored independently of the cause verdicts.
        assert acc["all_time"]["reason"]["confirmed"] == 0
        assert acc["all_time"]["reason"]["corrected"] == 1
        assert acc["all_time"]["reason"]["precision"] == 0.0


def test_recent_window_cuts_on_validation_time(session_factory):
    with session_scope(session_factory) as s:
        s.add(_attr(1, causing_person="dev-a", cause_provenance=Provenance.AI_CONFIRMED))
        s.add(
            _attr(
                2,
                causing_person="dev-b",
                cause_provenance=Provenance.HUMAN_CORRECTED,
                validated_at=_NOW - timedelta(days=90),  # outside the window
            )
        )
    with session_scope(session_factory) as s:
        acc = ai_accuracy(s, window_days=30, now=_NOW)
        assert acc["all_time"]["cause"]["confirmed"] == 1
        assert acc["all_time"]["cause"]["corrected"] == 1
        assert acc["recent"]["cause"]["confirmed"] == 1
        assert acc["recent"]["cause"]["corrected"] == 0
        assert acc["recent"]["cause"]["precision"] == 1.0


def test_human_entered_and_unconfirmed_are_excluded(session_factory):
    # No AI suggestion was in play for these — they say nothing about AI quality.
    with session_scope(session_factory) as s:
        s.add(_attr(1, causing_person="dev-a", cause_provenance=Provenance.HUMAN_ENTERED))
        s.add(_attr(2, causing_person="dev-b", cause_provenance=Provenance.AI_UNCONFIRMED))
    with session_scope(session_factory) as s:
        acc = ai_accuracy(s, now=_NOW)
        assert acc["has_data"] is False


def test_confirm_without_a_suggestion_is_excluded(session_factory):
    # A one-click Confirm on an episode with no suggested contact stamps AI_CONFIRMED provenance
    # but records no conclusion — there is no suggestion whose accuracy it could measure.
    with session_scope(session_factory) as s:
        s.add(_attr(1, causing_person=None, cause_provenance=Provenance.AI_CONFIRMED))
    with session_scope(session_factory) as s:
        acc = ai_accuracy(s, now=_NOW)
        assert acc["all_time"]["cause"]["total"] == 0
