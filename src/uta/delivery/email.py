"""Regression-only email.

Every commit triggers a run, so a per-run digest would be constant noise. The tool emails **only
when a processed run introduces ≥1 new failing test** (a regression vs the baseline). Runs with no
new failures send **nothing** — silence means "no worse than before". The email leads with the
**new failures** (predicted cause + suggested contact each) and carries still-failing / newly-fixed
counts as context.

A **recovery notice** ("back to green") is an optional, separately-toggleable exception.

The SMTP boundary sits behind :class:`EmailSender` so the offline suite drives a fake and never
opens a socket. The alert is two-phased around the ingest commit (issue #81):
:func:`build_regression_report` composes the message *inside* the ingest transaction (it needs the
session), and :func:`send_alert` delivers it *after* the transaction commits, swallowing any send
failure — so an SMTP outage can never fail or roll back an ingest, and a commit failure means
nothing was sent yet. The poller passes a real sender for live runs, while back-fill and the
on-demand re-ingest job pass none (so historical regressions are never re-mailed).
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage as _MimeMessage
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from uta.analyze.baseline import compute_diff, select_baseline
from uta.models import Classification, FailureEpisode, Run, TestIdentity

logger = logging.getLogger(__name__)

#: Connect/read timeout for the SMTP dial — a black-holed relay must fail fast, not hang the
#: caller (``/health`` probes the sender synchronously when the poller goes stale).
_SMTP_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class EmailMessage:
    subject: str
    body: str
    recipients: tuple[str, ...]


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class SmtpEmailSender:
    """Sends via stdlib ``smtplib`` (PLAN tech stack). Lives behind :class:`EmailSender`.

    Credentials are optional: with ``user`` set the sender negotiates STARTTLS and logs in before
    sending (an authenticated relay); with no credentials it stays the plain unauthenticated send.
    ``starttls`` overrides that TLS default explicitly — ``None`` means "on exactly when ``user``
    is set". The password is held for :meth:`send` only and never logged.
    """

    def __init__(
        self,
        host: str,
        port: int,
        sender: str,
        *,
        user: str = "",
        password: str = "",
        starttls: bool | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._sender = sender
        self._user = user
        self._password = password
        self._starttls = bool(user) if starttls is None else starttls

    def send(self, message: EmailMessage) -> None:
        if not message.recipients:
            return
        mime = _MimeMessage()
        mime["From"] = self._sender
        mime["To"] = ", ".join(message.recipients)
        mime["Subject"] = message.subject
        mime.set_content(message.body)
        with smtplib.SMTP(self._host, self._port, timeout=_SMTP_TIMEOUT_SECONDS) as smtp:
            if self._starttls:
                smtp.starttls()
            if self._user:
                smtp.login(self._user, self._password)
            smtp.send_message(mime)


def _dashboard_url(base_url: str, path: str) -> str | None:
    """Absolute dashboard deep link, or ``None`` when no base URL is configured (issue #108).

    Joins robustly whether or not the configured base carries a trailing slash, so
    ``http://host:8000/`` + ``/runs/5`` never yields ``//runs/5``.
    """
    if not base_url.strip():
        return None
    return f"{base_url.strip().rstrip('/')}{path}"


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
                "identity_id": identity_id,
                "test_id": ident.canonical_name if ident else str(identity_id),
                "owner": ident.main_developer if ident else None,
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
    app_base_url: str = "",
) -> EmailMessage | None:
    """The email for a processed run, or ``None`` if nothing should be sent.

    Returns a message only when the run introduced ≥1 new failing test, or — if ``recovery_notice``
    is on — when the run is back to green (no new failures and no failing tests at all). "Back to
    green" means an actual **red→green transition**: the baseline had ≥1 failing test that this run
    resolved — fixed (``diff.newly_fixed``) or absent this run (``diff.removed``; a deleted failing
    test still turns the suite green). A run that is merely *still* green (already-green baseline,
    or a first-ever all-green run with no baseline) sends nothing — silence stays the steady state.

    When ``app_base_url`` is set (issue #108) the body carries dashboard deep links — each new
    failure links to its per-test record (``/tests/{identity_id}``) and the message links the run
    summary (``/runs/{build}``) beside the Jenkins URL. Unset (the default), the body is exactly
    link-free, as before.
    """
    baseline = (
        session.get(Run, run.baseline_run_id)
        if run.baseline_run_id is not None
        else select_baseline(session, run)
    )
    diff = compute_diff(session, run, baseline)
    new_failures = _new_failure_lines(session, run, diff.regressions)
    run_link = _dashboard_url(app_base_url, f"/runs/{run.build_number}")

    if not new_failures:
        transitioned = bool(diff.newly_fixed or diff.removed)  # baseline had ≥1 failing test
        if recovery_notice and run.total_failed == 0 and not diff.still_failing and transitioned:
            body = (
                f"Build #{run.build_number} introduced no new failures and has no failing "
                f"tests.\nNewly fixed this run: {len(diff.newly_fixed)}.\n{run.url}\n"
            )
            if run_link:
                body += f"Dashboard: {run_link}\n"
            return EmailMessage(
                subject=f"UT back to green — build #{run.build_number}",
                body=body,
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
        test_link = _dashboard_url(app_base_url, f"/tests/{nf['identity_id']}")
        if test_link:
            lines.append(f"    {test_link}")
    lines += [
        "",
        f"Still failing: {len(diff.still_failing)}   Newly fixed: {len(diff.newly_fixed)}"
        f"   Removed: {len(diff.removed)}",
        run.url or "",
    ]
    if run_link:
        lines.append(f"Dashboard: {run_link}")
    return EmailMessage(
        subject=f"UT regressions — build #{run.build_number}: {len(new_failures)} new failing",
        body="\n".join(lines) + "\n",
        recipients=recipients,
    )


def send_ops_alert(
    sender: EmailSender | None,
    recipients: tuple[str, ...],
    *,
    subject: str,
    body: str,
) -> EmailMessage | None:
    """Send an operational alert (poller stale, build quarantined/skipped — issue #51).

    Rides the same :class:`EmailSender` seam as the regression report; a missing sender or empty
    recipient list means email is not configured, so nothing is sent. Delivery is **best-effort**,
    like :func:`send_alert`: a send failure is logged and swallowed, never raised — an SMTP outage
    must not turn ``/health`` into a 500 or wipe the poller tick's heartbeat record. Returns the
    message only when it actually went out (``None`` otherwise), so callers that latch on delivery
    (``check_health``'s ``stale_alerted_at``) re-try on the next occasion.
    """
    if sender is None or not recipients:
        return None
    message = EmailMessage(subject=f"UT Analyzer ops — {subject}", body=body, recipients=recipients)
    try:
        sender.send(message)
    except Exception:  # noqa: BLE001 — ops alerting is best-effort; never break the caller
        logger.warning(
            "ops alert %r failed to send — the fault stays visible on /health and the "
            "control panel; the alert is dropped",
            message.subject,
            exc_info=True,
        )
        return None
    return message


def send_alert(sender: EmailSender, message: EmailMessage) -> bool:
    """Send a composed alert, swallowing any failure. Returns whether it went out.

    Called by the ingest pipeline **after** the run's transaction has committed: the alert is
    best-effort delivery of already-persisted facts, so a send failure must never fail — let alone
    roll back — the ingest (the same discipline the LLM providers apply to enrichment). The failure
    is logged and the alert dropped; the regression stays visible on the dashboard.
    """
    try:
        sender.send(message)
    except Exception:  # noqa: BLE001 — alerting is best-effort; never break ingest (issue #81)
        logger.warning(
            "alert %r failed to send — the run is persisted, the alert is dropped",
            message.subject,
            exc_info=True,
        )
        return False
    return True
