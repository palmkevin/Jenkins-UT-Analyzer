"""The Microsoft Teams Alert Channel: POST an Adaptive Card to an incoming-webhook URL.

Teams is the second Alert Channel (ADR-0007). It renders a channel-neutral
:class:`~uta.delivery.alert.Alert` as an **Adaptive Card** — title, a FactSet of the alert's
structured facts, and an ``Action.OpenUrl`` "Open in dashboard" button; every text value
link-neutralised and capped at :data:`MAX_CARD_VALUE_CHARS` — and POSTs it to a single configured
webhook URL via the already-present ``httpx`` with a short, fail-fast timeout. The card
is wrapped in the Power Automate **Workflows** ``attachments`` envelope (contentType
``application/vnd.microsoft.card.adaptive``), the successor to the retiring Office 365 connector.

The HTTP client sits behind a seam (an injectable ``client``) so the offline suite drives a fake
transport and opens no socket, exactly like the SMTP sender's fake. ``TEAMS_WEBHOOK_URL`` embeds an
auth token — it is a secret, held for the POST only and never logged.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from uta.delivery.alert import Alert, AlertKind, AlertSeverity

if TYPE_CHECKING:
    import httpx

#: POST timeout — a black-holed webhook must fail fast (dispatch swallows the raise), never hang the
#: caller (the ingest/poll tick that dispatches after commit).
_TEAMS_TIMEOUT_SECONDS = 10.0

_CARD_CONTENT_TYPE = "application/vnd.microsoft.card.adaptive"

_SEVERITY_COLOR = {
    AlertSeverity.good: "Good",
    AlertSeverity.warning: "Warning",
    AlertSeverity.attention: "Attention",
}

#: Per-value cap on card text. Hypotheses / test names are unbounded, and Teams rejects a webhook
#: payload over ~28 KB — so a single runaway value must not sink the whole card.
MAX_CARD_VALUE_CHARS = 1000

#: A Markdown inline link's ``](`` hinge. Adaptive Cards render ``[text](url)`` as a live link, so
#: free text (an LLM hypothesis) could smuggle one in; a zero-width space between ``]`` and ``(``
#: breaks the syntax while displaying identically.
_LINK_HINGE = "]("
_BROKEN_LINK_HINGE = "]\u200b("


def card_text(value: str) -> str:
    """``value`` made safe as Adaptive Card text: truncated, with link syntax neutralised.

    Alert facts carry free text from the classifier / LLM, and a hypothesis can hold a
    ``[click](https://…)`` link that Teams would render live. Only that link syntax is broken (a
    zero-width space between ``]`` and ``(``); nothing else is escaped, because Adaptive Cards do
    not honour backslash escapes — escaping ``_`` / ``(`` would show ``CODE\\_CHANGE`` literally.
    """
    if len(value) > MAX_CARD_VALUE_CHARS:
        value = value[: MAX_CARD_VALUE_CHARS - 1] + "…"
    return value.replace(_LINK_HINGE, _BROKEN_LINK_HINGE)


def build_card_message(alert: Alert) -> dict:
    """The Power Automate Workflows envelope carrying the Alert rendered as an Adaptive Card."""
    body: list[dict] = [
        {
            "type": "TextBlock",
            "text": card_text(alert.title),
            "weight": "Bolder",
            "size": "Large",
            "wrap": True,
            "color": _SEVERITY_COLOR.get(alert.severity, "Default"),
        }
    ]
    if alert.summary:
        body.append({"type": "TextBlock", "text": card_text(alert.summary), "wrap": True})
    if alert.facts:
        body.append(
            {
                "type": "FactSet",
                "facts": [
                    {"title": card_text(label), "value": card_text(value)}
                    for label, value in alert.facts
                ],
            }
        )
    actions: list[dict] = []
    if alert.dashboard_url:
        actions.append(
            {"type": "Action.OpenUrl", "title": "Open in dashboard", "url": alert.dashboard_url}
        )
    if alert.jenkins_url:
        actions.append(
            {"type": "Action.OpenUrl", "title": "Open in Jenkins", "url": alert.jenkins_url}
        )
    card: dict = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": body,
    }
    if actions:
        card["actions"] = actions
    return {
        "type": "message",
        "attachments": [{"contentType": _CARD_CONTENT_TYPE, "content": card}],
    }


class TeamsDeliveryError(RuntimeError):
    """A failed webhook POST, described without the (secret-bearing) webhook URL."""


class TeamsAlertChannel:
    """The Teams Alert Channel — POSTs the Adaptive Card envelope to the webhook. See module doc.

    ``client`` injects an ``httpx.Client`` (the offline suite passes one backed by a
    ``MockTransport`` so no socket opens); when ``None`` a short-lived client is created per send. A
    non-2xx response (or a transport error) raises a URL-free :class:`TeamsDeliveryError` that
    :func:`~uta.delivery.alert.dispatch` swallows, keeping the webhook best-effort like the SMTP
    dial without ever logging the webhook's auth token.
    """

    def __init__(
        self,
        webhook_url: str,
        *,
        subscriptions: Iterable[AlertKind],
        client: httpx.Client | None = None,
        timeout: float = _TEAMS_TIMEOUT_SECONDS,
    ) -> None:
        self._webhook_url = webhook_url
        self.subscriptions = frozenset(subscriptions)
        self._client = client
        self._timeout = timeout

    def send(self, alert: Alert) -> None:
        import httpx

        payload = build_card_message(alert)
        # httpx errors embed the request URL — and the webhook URL *is* the secret (its ``sig=``
        # token). ``dispatch`` logs the raise with ``exc_info``, so re-raise a sanitized error that
        # names only the status / error class, with ``from None`` so no chained traceback carries
        # the original message either.
        try:
            if self._client is not None:
                response = self._client.post(self._webhook_url, json=payload, timeout=self._timeout)
            else:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(self._webhook_url, json=payload)
        except httpx.HTTPError as exc:
            raise TeamsDeliveryError(
                f"Teams webhook request failed ({type(exc).__name__})"
            ) from None
        if not response.is_success:
            raise TeamsDeliveryError(f"Teams webhook returned HTTP {response.status_code}")
