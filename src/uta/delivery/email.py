"""Regression-only email.

Every commit triggers a run, so a per-run digest would be constant noise. The tool emails **only
when a processed run introduces ≥1 new failing test** (a regression vs the baseline). Runs with no
new failures send **nothing** — silence means "no worse than before". The email leads with the
**new failures** (predicted cause + suggested contact each) and carries still-failing / newly-fixed
counts as context.

A **recovery notice** ("back to green") is an optional, separately-toggleable exception.

The SMTP boundary sits behind :class:`EmailSender` so the offline suite drives a fake and never
opens a socket. ``maybe_notify`` is the single entry point; the poller passes a real sender for
live runs, while back-fill passes none (so historical regressions are never re-mailed).
"""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage as _MimeMessage
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from uta.analyze.baseline import compute_diff, select_baseline
from uta.models import Classification, FailureEpisode, Run, TestIdentity


@dataclass(frozen=True)
class EmailMessage:
    subject: str
    body: str
    recipients: tuple[str, ...]


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class SmtpEmailSender:
    """Sends via stdlib ``smtplib`` (PLAN tech stack). Lives behind :class:`EmailSender`."""

    def __init__(self, host: str, port: int, sender: str) -> None:
        self._host = host
        self._port = port
        self._sender = sender

    def send(self, message: EmailMessage) -> None:
        if not message.recipients:
            return
        mime = _MimeMessage()
        mime["From"] = self._sender
        mime["To"] = ", ".join(message.recipients)
        mime["Subject"] = message.subject
        mime.set_content(message.body)
        with smtplib.SMTP(self._host, self._port) as smtp:
            smtp.send_message(mime)


def _latest_classification(session: Session, episode_id: int) -> Classification | None:
    return session.scalar(
        select(Classification)
        .where(Classification.episode_id == episode_id)
        .order_by(Classification.created_at.desc(), Classification.id.desc())
        .limit(1)
    )


def _new_failure_lines(session: Session, run: Run, regression_ids: list[int]) -> list[dict]:
    names = {
        i.id: i
        for i in session.scalars(
            select(TestIdentity).where(TestIdentity.id.in_(regression_ids))
        ).all()
    }
    out: list[dict] = []
    for identity_id in regression_ids:
        ident = names.get(identity_id)
        episode = session.scalar(
            select(FailureEpisode).where(
                FailureEpisode.test_identity_id == identity_id,
                FailureEpisode.is_open.is_(True),
            )
        )
        classification = _latest_classification(session, episode.id) if episode else None
        out.append(
            {
                "test_id": ident.canonical_name if ident else str(identity_id),
                "owner": ident.owner_initials if ident else None,
                "predicted_cause": classification.predicted_cause if classification else "UNKNOWN",
                "suggested_contact": classification.suggested_contact if classification else None,
            }
        )
    out.sort(key=lambda r: r["test_id"])
    return out


def build_regression_report(
    session: Session,
    run: Run,
    recipients: tuple[str, ...],
    *,
    recovery_notice: bool = False,
) -> EmailMessage | None:
    """The email for a processed run, or ``None`` if nothing should be sent.

    Returns a message only when the run introduced ≥1 new failing test, or — if ``recovery_notice``
    is on — when the run is back to green (no new failures and no failing tests at all).
    """
    baseline = (
        session.get(Run, run.baseline_run_id)
        if run.baseline_run_id is not None
        else select_baseline(session, run)
    )
    diff = compute_diff(session, run, baseline)
    new_failures = _new_failure_lines(session, run, diff.regressions)

    if not new_failures:
        if recovery_notice and run.total_failed == 0 and not diff.still_failing:
            return EmailMessage(
                subject=f"UT back to green — build #{run.build_number}",
                body=(
                    f"Build #{run.build_number} introduced no new failures and has no failing "
                    f"tests.\nNewly fixed this run: {len(diff.newly_fixed)}.\n{run.url}\n"
                ),
                recipients=recipients,
            )
        return None

    lines = [
        f"Build #{run.build_number} introduced {len(new_failures)} new failing test(s).",
        "",
        "NEW FAILURES",
    ]
    for nf in new_failures:
        contact = f" — contact: {nf['suggested_contact']}" if nf["suggested_contact"] else ""
        owner = f" (owner {nf['owner']})" if nf["owner"] else ""
        lines.append(f"  • {nf['test_id']}{owner} — cause: {nf['predicted_cause']}{contact}")
    lines += [
        "",
        f"Still failing: {len(diff.still_failing)}   Newly fixed: {len(diff.newly_fixed)}"
        f"   Removed: {len(diff.removed)}",
        run.url or "",
    ]
    return EmailMessage(
        subject=f"UT regressions — build #{run.build_number}: {len(new_failures)} new failing",
        body="\n".join(lines) + "\n",
        recipients=recipients,
    )


def maybe_notify(
    session: Session,
    run: Run,
    sender: EmailSender | None,
    recipients: tuple[str, ...],
    *,
    recovery_notice: bool = False,
) -> EmailMessage | None:
    """Build and (if a sender + recipients are present) send the regression email. Returns it."""
    if sender is None or not recipients:
        return None
    message = build_regression_report(session, run, recipients, recovery_notice=recovery_notice)
    if message is not None:
        sender.send(message)
    return message
