"""The channel-neutral alert layer: allowlist parsing, dispatcher routing, best-effort isolation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.fakes.alert import RaisingAlertChannel, RecordingAlertChannel
from uta.config import Settings
from uta.delivery.alert import Alert, AlertKind, dispatch, wants


def _alert(kind: AlertKind) -> Alert:
    return Alert(kind=kind, title=f"{kind.value} title", body="body")


# ── Config: per-channel allowlists parse to a set of kinds, fail fast on an unknown kind ──────────


def test_email_events_default_preserves_pre_multichannel_behaviour():
    """Default EMAIL_EVENTS = everything the tool alerted on before, i.e. recovery OFF."""
    assert Settings().email_event_set == frozenset(
        {AlertKind.incident, AlertKind.regression, AlertKind.overrun, AlertKind.ops}
    )
    assert AlertKind.recovery not in Settings().email_event_set


def test_teams_events_default_is_empty_opt_in():
    assert Settings().teams_event_set == frozenset()


def test_allowlist_parses_and_trims_whitespace():
    s = Settings(email_events=" incident , recovery ", teams_events="ops")
    assert s.email_event_set == frozenset({AlertKind.incident, AlertKind.recovery})
    assert s.teams_event_set == frozenset({AlertKind.ops})


def test_empty_allowlist_means_subscribed_to_nothing():
    s = Settings(email_events="", teams_events="")
    assert s.email_event_set == frozenset()
    assert s.teams_event_set == frozenset()


@pytest.mark.parametrize("field", ["email_events", "teams_events"])
def test_unknown_alert_kind_fails_fast_at_startup(field):
    with pytest.raises(ValidationError) as excinfo:
        Settings(**{field: "incident,bogus"})
    assert "unknown alert kind" in str(excinfo.value)
    assert "bogus" in str(excinfo.value)


# ── wants(): the call-site compose guard ──────────────────────────────────────────────────────────


def test_wants_true_only_when_some_channel_subscribes():
    channels = [RecordingAlertChannel(subscriptions={AlertKind.incident})]
    assert wants(channels, AlertKind.incident) is True
    assert wants(channels, AlertKind.regression) is False
    assert wants(None, AlertKind.incident) is False
    assert wants([], AlertKind.incident) is False


# ── dispatch(): per-kind routing + best-effort isolation ──────────────────────────────────────────


def test_dispatch_routes_only_to_channels_subscribing_to_the_kind():
    incident_ch = RecordingAlertChannel(subscriptions={AlertKind.incident})
    regression_ch = RecordingAlertChannel(subscriptions={AlertKind.regression})
    both = [incident_ch, regression_ch]

    assert dispatch(_alert(AlertKind.incident), both) == 1
    assert dispatch(_alert(AlertKind.regression), both) == 1

    assert [a.kind for a in incident_ch.sent] == [AlertKind.incident]
    assert [a.kind for a in regression_ch.sent] == [AlertKind.regression]


def test_dispatch_sends_to_every_subscribing_channel():
    a = RecordingAlertChannel(subscriptions={AlertKind.ops})
    b = RecordingAlertChannel(subscriptions={AlertKind.ops})
    assert dispatch(_alert(AlertKind.ops), [a, b]) == 2
    assert len(a.sent) == 1 and len(b.sent) == 1


def test_dispatch_skips_unsubscribed_kind_entirely():
    ch = RecordingAlertChannel(subscriptions={AlertKind.regression})
    assert dispatch(_alert(AlertKind.recovery), [ch]) == 0
    assert ch.sent == []


def test_dispatch_is_best_effort_and_isolated():
    """One channel raising is logged and swallowed — it never raises, nor stops the other."""
    raising = RaisingAlertChannel()
    recording = RecordingAlertChannel()
    delivered = dispatch(_alert(AlertKind.incident), [raising, recording])
    assert raising.attempts == 1
    assert delivered == 1  # only the healthy channel counts as delivered
    assert len(recording.sent) == 1  # the healthy channel still received it


def test_dispatch_returns_zero_with_no_channels():
    assert dispatch(_alert(AlertKind.ops), None) == 0
    assert dispatch(_alert(AlertKind.ops), []) == 0
