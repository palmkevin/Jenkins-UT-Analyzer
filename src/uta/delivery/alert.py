"""Channel-neutral alerting: the Alert value, the AlertChannel seam, and the dispatcher.

An **Alert** is composed once — channel-neutrally — from already-persisted facts, then handed to
every enabled **Alert Channel** whose subscription includes the Alert's **kind**. Each channel
renders it its own way: :class:`~uta.delivery.email.EmailAlertChannel` as the plain-text email the
tool has always sent, :class:`~uta.delivery.teams.TeamsAlertChannel` as a Microsoft Teams Adaptive
Card. See docs/adr/0007.

Delivery is **best-effort and independent per channel**: :func:`dispatch` wraps each channel's send
so one channel's outage (an SMTP relay down, a webhook 5xx) can neither raise, block the other
channel, nor roll back the ingest that composed the Alert — the same discipline the single-channel
email path established (issue #81).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

logger = logging.getLogger(__name__)


class AlertKind(StrEnum):
    """Which build condition an Alert announces — the unit an Alert Channel subscribes to."""

    incident = "incident"  # a pipeline_failure Build Incident opened
    regression = "regression"  # a build introduced >=1 new failing test
    recovery = "recovery"  # the suite went back to green
    overrun = "overrun"  # an in-progress build exceeded its Expected Duration
    ops = "ops"  # a poller-health / quarantine condition


class AlertSeverity(StrEnum):
    """Card accent for the Alert — maps to Adaptive Card text colours in the Teams channel."""

    good = "good"
    warning = "warning"
    attention = "attention"


@dataclass(frozen=True)
class Alert:
    """A single channel-neutral notification.

    ``body`` is the canonical plain-text rendering — what the email channel sends verbatim, so the
    email stays byte-for-byte what it was before multi-channel. ``summary`` + ``facts`` are the
    structured content a rich channel (Teams) renders as an Adaptive Card; ``dashboard_url`` /
    ``jenkins_url`` are the optional deep-links a channel turns into buttons. The Alert deliberately
    carries **no recipients** — who receives it is an Email-channel concern (issue #181).
    """

    kind: AlertKind
    title: str
    body: str
    summary: str = ""
    facts: tuple[tuple[str, str], ...] = ()
    dashboard_url: str | None = None
    jenkins_url: str | None = None
    severity: AlertSeverity = AlertSeverity.warning


class AlertChannel(Protocol):
    """A delivery destination. ``subscriptions`` are the kinds it wants; ``send`` delivers one."""

    subscriptions: frozenset[AlertKind]

    def send(self, alert: Alert) -> None: ...


def wants(channels: Iterable[AlertChannel] | None, kind: AlertKind) -> bool:
    """Whether *some* enabled channel subscribes to ``kind`` — the call-site compose guard.

    Composing an Alert costs classification/episode DB queries, so a call site skips them entirely
    when no enabled channel would take that kind (ADR-0007).
    """
    return any(kind in channel.subscriptions for channel in (channels or ()))


def dispatch(alert: Alert, channels: Iterable[AlertChannel] | None) -> int:
    """Send ``alert`` to every subscribing channel, best-effort and isolated. Returns # delivered.

    Each channel's send is wrapped: an exception is logged and swallowed so it can neither break the
    caller (ingest / poll tick / health probe) nor stop the remaining channels. A channel that does
    not subscribe to ``alert.kind`` is skipped. The count of successful deliveries lets a latching
    caller (``check_health``'s stale alert) fire once and re-arm only when nothing went out.
    """
    delivered = 0
    for channel in channels or ():
        if alert.kind not in channel.subscriptions:
            continue
        try:
            channel.send(alert)
        except Exception:  # noqa: BLE001 — best-effort; never break the caller or other channels
            logger.warning(
                "alert %r failed on %s — dropped; other channels and the ingest are unaffected",
                alert.title,
                type(channel).__name__,
                exc_info=True,
            )
            continue
        delivered += 1
    return delivered
