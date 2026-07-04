"""A fake email sender — records messages instead of opening a socket (offline gate)."""

from __future__ import annotations

from uta.delivery.email import EmailMessage


class RecordingEmailSender:
    """Implements the :class:`~uta.delivery.email.EmailSender` protocol; keeps what it was sent."""

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)
