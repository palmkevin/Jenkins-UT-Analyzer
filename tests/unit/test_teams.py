"""The Teams Alert Channel: Adaptive-Card rendering + a POST that opens no real socket.

The HTTP boundary is driven by an ``httpx.MockTransport`` — no network is touched, matching the
offline gate's discipline for the SMTP sender.
"""

from __future__ import annotations

import httpx
import pytest

from uta.clients import build_channels
from uta.config import Settings
from uta.delivery.alert import Alert, AlertKind, AlertSeverity, dispatch
from uta.delivery.teams import TeamsAlertChannel, build_card_message

WEBHOOK = "https://example.webhook.office.com/workflows/abc?sig=secret"


def _incident_alert() -> Alert:
    return Alert(
        kind=AlertKind.incident,
        title="UT pipeline failure — build #1702 incident opened",
        body="plain text body\n",
        summary="Build #1702 FAILED — a new pipeline-failure incident was opened.",
        facts=(("Failing stage", "Compile"), ("Predicted cause", "CODE_CHANGE")),
        dashboard_url="http://uta.example/builds/1702",
        jenkins_url="http://jenkins/1702/",
        severity=AlertSeverity.attention,
    )


def _capture_transport() -> tuple[httpx.MockTransport, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(202)

    return httpx.MockTransport(handler), seen


# ── The Adaptive Card ─────────────────────────────────────────────────────────────────────────────


def test_card_is_workflows_attachments_envelope_with_facts_and_open_url():
    payload = build_card_message(_incident_alert())
    assert payload["type"] == "message"
    (attachment,) = payload["attachments"]
    assert attachment["contentType"] == "application/vnd.microsoft.card.adaptive"
    card = attachment["content"]
    assert card["type"] == "AdaptiveCard"

    title_block = card["body"][0]
    assert title_block["text"] == "UT pipeline failure — build #1702 incident opened"
    assert title_block["color"] == "Attention"

    factset = next(b for b in card["body"] if b["type"] == "FactSet")
    assert {"title": "Failing stage", "value": "Compile"} in factset["facts"]
    assert {"title": "Predicted cause", "value": "CODE_CHANGE"} in factset["facts"]

    open_url = next(a for a in card["actions"] if a["title"] == "Open in dashboard")
    assert open_url["type"] == "Action.OpenUrl"
    assert open_url["url"] == "http://uta.example/builds/1702"


def test_card_omits_actions_and_factset_when_absent():
    card = build_card_message(Alert(kind=AlertKind.ops, title="t", body="b"))["attachments"][0][
        "content"
    ]
    assert "actions" not in card
    assert all(block["type"] != "FactSet" for block in card["body"])


# ── The POST (no real socket) ──────────────────────────────────────────────────────────────


def test_send_posts_the_card_envelope_to_the_webhook():
    transport, seen = _capture_transport()
    channel = TeamsAlertChannel(
        WEBHOOK, subscriptions={AlertKind.incident}, client=httpx.Client(transport=transport)
    )
    channel.send(_incident_alert())

    (request,) = seen
    assert request.method == "POST"
    assert str(request.url) == WEBHOOK
    import json

    body = json.loads(request.content)
    assert body["attachments"][0]["content"]["type"] == "AdaptiveCard"


def test_send_raises_on_non_2xx_so_dispatch_can_swallow_it():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    channel = TeamsAlertChannel(
        WEBHOOK,
        subscriptions={AlertKind.incident},
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(httpx.HTTPStatusError):
        channel.send(_incident_alert())
    # …and dispatch turns that raise into a swallowed, counted-as-not-delivered failure.
    assert dispatch(_incident_alert(), [channel]) == 0


# ── build_channels(): enablement + subscriptions ─────────────────────────────────────────────


def test_teams_channel_disabled_when_webhook_unset():
    assert build_channels(Settings(teams_events="incident")) == []  # no URL ⇒ no channel


def test_teams_channel_enabled_with_url_and_carries_its_subscriptions():
    channels = build_channels(Settings(teams_webhook_url=WEBHOOK, teams_events="incident,ops"))
    (teams,) = [c for c in channels if isinstance(c, TeamsAlertChannel)]
    assert teams.subscriptions == frozenset({AlertKind.incident, AlertKind.ops})
