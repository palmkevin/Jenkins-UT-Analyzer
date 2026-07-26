"""The email Alert Channel and the ``build_*`` Alert composers.

Every commit triggers a build, so a per-build digest would be constant noise. The tool alerts
**only** on a noteworthy condition: a build that introduces ≥1 new failing test (a **regression**),
a newly-opened pipeline-failure **incident**, an **overrunning** in-progress build, a poller-health
/ quarantine **ops** condition, and — when subscribed — the suite going back to green
(**recovery**).

Each ``build_*`` function composes a channel-neutral :class:`~uta.delivery.alert.Alert` (title,
plain-text body, structured summary/facts, deep-links, kind); the dispatcher then hands it to every
enabled Alert Channel that subscribes to its kind (ADR-0007). :class:`EmailAlertChannel` renders an
Alert back to the **exact plain-text email** the tool always sent (subject = title, body = the
Alert's ``body``) and delivers it over the SMTP boundary behind :class:`EmailSender`, so the offline
suite drives a fake and never opens a socket.

The alert is two-phased around the ingest commit (issue #81): the composer runs *inside* the ingest
transaction (it needs the session) and the dispatcher delivers *after* the transaction commits,
swallowing any send failure — so an SMTP/webhook outage can never fail or roll back an ingest, and a
commit failure means nothing was sent yet. The poller passes real channels for live builds, while
back-fill and the on-demand re-ingest job pass none (so historical regressions are never
re-alerted).
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
from uta.delivery.alert import Alert, AlertKind, AlertSeverity
from uta.models import Build, BuildIncident, Classification, FailureEpisode, TestIdentity

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


class EmailAlertChannel:
    """The email Alert Channel: renders an Alert to the exact plain-text email and sends via SMTP.

    Wraps an :class:`EmailSender` (the real :class:`SmtpEmailSender` or a test fake). The rendered
    message is byte-for-byte what each ``build_*`` composer produced before multi-channel — subject
    = the Alert title, body = the Alert's plain-text ``body`` — addressed to this channel's
    configured recipients. Subscribes to the kinds in ``subscriptions`` (``EMAIL_EVENTS``); the
    dispatcher only calls :meth:`send` for a subscribed kind.
    """

    def __init__(
        self,
        sender: EmailSender,
        recipients: tuple[str, ...],
        subscriptions: frozenset[AlertKind] | set[AlertKind],
    ) -> None:
        self._sender = sender
        self._recipients = tuple(recipients)
        self.subscriptions = frozenset(subscriptions)

    def send(self, alert: Alert) -> None:
        self._sender.send(
            EmailMessage(subject=alert.title, body=alert.body, recipients=self._recipients)
        )


def _dashboard_url(base_url: str, path: str) -> str | None:
    """Absolute dashboard deep link, or ``None`` when no base URL is configured (issue #108).

    Joins robustly whether or not the configured base carries a trailing slash, so
    ``http://host:8000/`` + ``/builds/5`` never yields ``//builds/5``.
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


def _new_failure_lines(session: Session, build: Build, regression_ids: list[int]) -> list[dict]:
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
    build: Build,
    *,
    recovery_notice: bool = False,
    app_base_url: str = "",
) -> Alert | None:
    """The Alert for a processed build, or ``None`` if nothing should be sent.

    Returns a ``regression``-kind Alert only when the build introduced ≥1 new failing test, or — if
    ``recovery_notice`` is on (i.e. some channel subscribes to ``recovery``) — a ``recovery``-kind
    Alert when the build is back to green (no new failures and no failing tests at all). "Back to
    green" means an actual **red→green transition**: the baseline had ≥1 failing test that this
    build resolved — fixed (``diff.newly_fixed``) or absent this build (``diff.removed``; a deleted
    failing test still turns the suite green). A build that is merely *still* green (already-green
    baseline, or a first-ever all-green build with no baseline) sends nothing — silence stays the
    steady state.

    When ``app_base_url`` is set (issue #108) the body carries dashboard deep links — each new
    failure links to its per-test record (``/tests/{identity_id}``) and the message links the build
    summary (``/builds/{build}``) beside the Jenkins URL. Unset (the default), the body is exactly
    link-free, as before.
    """
    baseline = (
        session.get(Build, build.baseline_build_id)
        if build.baseline_build_id is not None
        else select_baseline(session, build)
    )
    diff = compute_diff(session, build, baseline)
    new_failures = _new_failure_lines(session, build, diff.regressions)
    build_link = _dashboard_url(app_base_url, f"/builds/{build.build_number}")

    if not new_failures:
        transitioned = bool(diff.newly_fixed or diff.removed)  # baseline had ≥1 failing test
        if recovery_notice and build.total_failed == 0 and not diff.still_failing and transitioned:
            body = (
                f"Build #{build.build_number} introduced no new failures and has no failing "
                f"tests.\nNewly fixed this build: {len(diff.newly_fixed)}.\n{build.url}\n"
            )
            if build_link:
                body += f"Dashboard: {build_link}\n"
            return Alert(
                kind=AlertKind.recovery,
                title=f"UT back to green — build #{build.build_number}",
                body=body,
                summary=(
                    f"Build #{build.build_number} introduced no new failures and has no "
                    f"failing tests."
                ),
                facts=(("Newly fixed this build", str(len(diff.newly_fixed))),),
                dashboard_url=build_link,
                jenkins_url=build.url or None,
                severity=AlertSeverity.good,
            )
        return None

    lines = [
        f"Build #{build.build_number} introduced {len(new_failures)} new failing test(s).",
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
        build.url or "",
    ]
    if build_link:
        lines.append(f"Dashboard: {build_link}")
    return Alert(
        kind=AlertKind.regression,
        title=f"UT regressions — build #{build.build_number}: {len(new_failures)} new failing",
        body="\n".join(lines) + "\n",
        summary=f"Build #{build.build_number} introduced {len(new_failures)} new failing test(s).",
        facts=(
            ("New failing", str(len(new_failures))),
            ("Still failing", str(len(diff.still_failing))),
            ("Newly fixed", str(len(diff.newly_fixed))),
            ("Removed", str(len(diff.removed))),
        ),
        dashboard_url=build_link,
        jenkins_url=build.url or None,
        severity=AlertSeverity.warning,
    )


def build_incident_alert(
    session: Session,
    incident: BuildIncident,
    build: Build,
    *,
    app_base_url: str = "",
) -> Alert:
    """The Alert for a **newly-opened** ``pipeline_failure`` Build Incident (issue #171).

    Sent only for the *opening* build of a streak (the caller enforces that), and only for
    ``pipeline_failure`` — ``aborted`` incidents and recoveries are suppressed by default. Leads
    with the failing stage and the deterministic prediction (+ suggested contact), and — when
    ``app_base_url`` is set — deep-links the incident's build page. Returns an ``incident``-kind
    Alert; composed inside the ingest transaction, delivered after commit by the dispatcher.
    """
    classification = session.scalar(
        select(Classification)
        .where(Classification.incident_id == incident.id)
        .order_by(Classification.created_at.desc(), Classification.id.desc())
        .limit(1)
    )
    cause = classification.predicted_cause if classification else "UNKNOWN"
    contact = classification.suggested_contact if classification else None
    lines = [
        f"Build #{build.build_number} FAILED — a new pipeline-failure incident was opened.",
        "",
        f"Failing stage: {incident.failing_stage or 'unknown'}",
        f"Predicted cause: {cause}",
    ]
    if contact:
        lines.append(f"Suggested contact: {contact}")
    if classification and classification.llm_hypothesis:
        lines += ["", f"Hypothesis: {classification.llm_hypothesis}"]
    lines.append("")
    lines.append(build.url or "")
    build_link = _dashboard_url(app_base_url, f"/builds/{build.build_number}")
    if build_link:
        lines.append(f"Dashboard: {build_link}")
    facts: list[tuple[str, str]] = [
        ("Failing stage", incident.failing_stage or "unknown"),
        ("Predicted cause", cause),
    ]
    if contact:
        facts.append(("Suggested contact", contact))
    if classification and classification.llm_hypothesis:
        facts.append(("Hypothesis", classification.llm_hypothesis))
    return Alert(
        kind=AlertKind.incident,
        title=f"UT pipeline failure — build #{build.build_number} incident opened",
        body="\n".join(lines) + "\n",
        summary=f"Build #{build.build_number} FAILED — a new pipeline-failure incident was opened.",
        facts=tuple(facts),
        dashboard_url=build_link,
        jenkins_url=build.url or None,
        severity=AlertSeverity.attention,
    )


def _compact_duration(seconds: float | None) -> str:
    """``3900`` → ``1h 5m``; sub-minute → ``Ns``; ``None`` → ``unknown`` (link-free plain text)."""
    if seconds is None:
        return "unknown"
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def build_overrun_alert(
    build_number: int,
    *,
    elapsed_seconds: float,
    expected_seconds: float | None,
    jenkins_build_url: str | None = None,
    app_base_url: str = "",
) -> Alert:
    """The one-per-build Alert for an **overrunning** in-progress build (issue #184).

    Fired on the first tick the poller sets the ``overrunning`` flag (the caller de-dups by the
    persisted marker), so a human can go stop the build. Leads with how long it has been running
    versus the Expected Duration and links straight to the build in Jenkins; unlike the aborted
    Build Incident that opens if someone acts on it, this is the *only* notification for an
    overrunning build. Returns an ``overrun``-kind Alert.
    """
    lines = [
        f"Build #{build_number} is still running and has overrun its expected duration.",
        "",
        f"Elapsed: {_compact_duration(elapsed_seconds)}",
        f"Expected (median of recent builds): {_compact_duration(expected_seconds)}",
        "",
        "It may be stuck — check it and stop it in Jenkins if so.",
    ]
    if jenkins_build_url:
        lines.append(jenkins_build_url)
    dashboard = _dashboard_url(app_base_url, "/")
    if dashboard:
        lines.append(f"Dashboard: {dashboard}")
    return Alert(
        kind=AlertKind.overrun,
        title=f"UT overrunning build — #{build_number} still running past expected duration",
        body="\n".join(lines) + "\n",
        summary=f"Build #{build_number} is still running and has overrun its expected duration.",
        facts=(
            ("Elapsed", _compact_duration(elapsed_seconds)),
            ("Expected (median of recent builds)", _compact_duration(expected_seconds)),
        ),
        dashboard_url=dashboard,
        jenkins_url=jenkins_build_url,
        severity=AlertSeverity.warning,
    )


def build_ops_alert(*, subject: str, body: str) -> Alert:
    """An operational Alert (poller stale, build quarantined/skipped — issues #51/#121).

    Returns an ``ops``-kind Alert with the ``UT Analyzer ops — `` subject prefix the email channel
    has always used. Delivery is best-effort via the dispatcher; a latching caller
    (``check_health``) fires once on a successful delivery and re-arms when nothing went out.
    """
    first_line = next((ln for ln in body.splitlines() if ln.strip()), subject)
    return Alert(
        kind=AlertKind.ops,
        title=f"UT Analyzer ops — {subject}",
        body=body,
        summary=first_line,
        severity=AlertSeverity.attention,
    )
