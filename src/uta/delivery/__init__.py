"""Delivery surfaces beyond the dashboard: the multi-channel Alert layer (ADR-0007).

An :class:`~uta.delivery.alert.Alert` is composed once, channel-neutrally, then dispatched to every
enabled :class:`~uta.delivery.alert.AlertChannel` that subscribes to its kind — currently the SMTP
:class:`~uta.delivery.email.EmailAlertChannel` and the Microsoft Teams
:class:`~uta.delivery.teams.TeamsAlertChannel`.
"""

from __future__ import annotations
