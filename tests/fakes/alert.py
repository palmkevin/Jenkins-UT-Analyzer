"""Fake Alert Channels — record (or raise on) sends instead of touching a socket (offline gate)."""

from __future__ import annotations

from uta.delivery.alert import Alert, AlertKind


class RecordingAlertChannel:
    """Implements the :class:`~uta.delivery.alert.AlertChannel` protocol; keeps what it was sent.

    Subscribes to every :class:`~uta.delivery.alert.AlertKind` by default (so it records whatever a
    call site dispatches); pass ``subscriptions`` to restrict it — e.g. to prove per-kind routing.
    """

    def __init__(self, subscriptions=None) -> None:
        self.sent: list[Alert] = []
        self.subscriptions = (
            frozenset(AlertKind) if subscriptions is None else frozenset(subscriptions)
        )

    def send(self, alert: Alert) -> None:
        self.sent.append(alert)


class RaisingAlertChannel:
    """An AlertChannel whose delivery always fails — proves dispatch swallows per-channel faults."""

    def __init__(self, subscriptions=None) -> None:
        self.attempts = 0
        self.subscriptions = (
            frozenset(AlertKind) if subscriptions is None else frozenset(subscriptions)
        )

    def send(self, alert: Alert) -> None:
        self.attempts += 1
        raise RuntimeError("channel down")
