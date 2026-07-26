"""The email Alert Channel and the ``build_*`` Alert composers.

The composers return channel-neutral :class:`~uta.delivery.alert.Alert` values; the
:class:`~uta.delivery.email.EmailAlertChannel` renders them back to the exact plain-text email the
tool always sent (subject = title, body = the Alert body). The contract is unchanged: a regression
Alert only when a processed build introduces ≥1 new failing test; otherwise silence (unless the
recovery kind is subscribed and the build is back to green).
"""

from __future__ import annotations

import smtplib

from sqlalchemy import select

from tests.builders import _EPOCH, make_build
from tests.fakes.email import RecordingEmailSender
from uta.analyze.classify import classify_build
from uta.analyze.lifecycle import apply_build
from uta.clients import build_email_sender
from uta.config import Settings
from uta.delivery.alert import Alert, AlertKind
from uta.delivery.email import (
    EmailAlertChannel,
    EmailMessage,
    SmtpEmailSender,
    build_ops_alert,
    build_regression_report,
)
from uta.models import CodeChangeCandidate, TestIdentity

RCPT = ("team@example.com",)
BASE = "http://uta.example:8000"


def _process(session, build, statuses, **kw):
    build = make_build(session, build, statuses, **kw)
    apply_build(session, build)  # drives baseline + episodes so regressions are known
    session.flush()
    return build


def _email_of(alert: Alert, recipients: tuple[str, ...] = RCPT) -> EmailMessage:
    """The EmailMessage the email channel renders for ``alert`` (byte-for-byte the old output)."""
    sender = RecordingEmailSender()
    EmailAlertChannel(sender, recipients, frozenset(AlertKind)).send(alert)
    assert len(sender.sent) == 1
    return sender.sent[0]


def test_no_email_when_no_new_failures(session_factory):
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED"})
        build = _process(s, 2, {"a.test": "PASSED"})
        s.commit()
        assert build_regression_report(s, build) is None


def test_email_on_regression_leads_with_new_failures(session_factory):
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED", "b.test": "PASSED"})
        build = _process(s, 2, {"a.test": "FAILED", "b.test": "PASSED"})
        s.commit()
        alert = build_regression_report(s, build)
    assert alert is not None
    assert alert.kind is AlertKind.regression
    assert "1 new failing" in alert.title
    assert "a.test" in alert.body
    assert "NEW FAILURES" in alert.body
    # The email channel renders it to the exact message, addressed to its recipients.
    msg = _email_of(alert)
    assert msg.subject == alert.title
    assert msg.body == alert.body
    assert msg.recipients == RCPT


def test_email_shows_suggested_contact_for_new_failure(session_factory):
    # The classifier suggests the sole commit author (#49); the new-failure line carries it.
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED"})
        build = make_build(s, 2, {"a.test": "FAILED"})
        build.code_changes.append(
            CodeChangeCandidate(commit_id="r888", author="R. Devlin", committed_at=_EPOCH)
        )
        analysis = apply_build(s, build)
        s.flush()
        classify_build(s, build, analysis.opened_episodes)
        s.commit()
        alert = build_regression_report(s, build)
    assert alert is not None
    assert "cause: CODE_CHANGE" in alert.body
    assert "contact: R. Devlin" in alert.body


def test_recovery_notice_only_when_subscribed_and_green(session_factory):
    with session_factory() as s:
        _process(s, 1, {"a.test": "FAILED"})
        build = _process(s, 2, {"a.test": "FIXED"})  # back to green
        s.commit()
        assert build_regression_report(s, build) is None  # recovery off by default
        alert = build_regression_report(s, build, recovery_notice=True)
    assert alert is not None
    assert alert.kind is AlertKind.recovery
    assert "back to green" in alert.title


def test_no_recovery_notice_when_already_green(session_factory):
    """A green build after a green baseline is *still* green, not *back to* green — no email."""
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED"})
        build = _process(s, 2, {"a.test": "PASSED"})
        s.commit()
        assert build_regression_report(s, build, recovery_notice=True) is None


def test_no_recovery_notice_on_first_ever_green_run(session_factory):
    """An all-green first build has no baseline, so nothing transitioned — no email."""
    with session_factory() as s:
        build = _process(s, 1, {"a.test": "PASSED"})
        s.commit()
        assert build_regression_report(s, build, recovery_notice=True) is None


def test_recovery_notice_when_baseline_failure_was_removed(session_factory):
    """A baseline failure absent this build (test deleted) still turns the suite green — notice."""
    with session_factory() as s:
        _process(s, 1, {"a.test": "FAILED", "b.test": "PASSED"})
        build = _process(s, 2, {"b.test": "PASSED"})  # a.test removed
        s.commit()
        alert = build_regression_report(s, build, recovery_notice=True)
    assert alert is not None
    assert "back to green" in alert.title


def test_dashboard_links_when_base_url_set(session_factory):
    """Each new failure links its per-test record; the build summary is linked too (#108)."""
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED", "b.test": "PASSED"})
        build = _process(s, 2, {"a.test": "FAILED", "b.test": "FAILED"})
        s.commit()
        alert = build_regression_report(s, build, app_base_url=BASE)
        ids = {
            i.canonical_name: i.id
            for i in s.scalars(
                select(TestIdentity).where(TestIdentity.canonical_name.in_(["a.test", "b.test"]))
            )
        }
    assert alert is not None
    assert f"{BASE}/tests/{ids['a.test']}" in alert.body
    assert f"{BASE}/tests/{ids['b.test']}" in alert.body
    assert f"Dashboard: {BASE}/builds/2" in alert.body
    assert alert.dashboard_url == f"{BASE}/builds/2"


def test_no_dashboard_links_when_base_url_unset(session_factory):
    """The default (no APP_BASE_URL) keeps the body exactly link-free — no 'Dashboard:' stubs."""
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED"})
        build = _process(s, 2, {"a.test": "FAILED"})
        s.commit()
        alert = build_regression_report(s, build)
    assert alert is not None
    assert "Dashboard:" not in alert.body
    assert "http" not in alert.body  # make_build sets no Jenkins url either — zero URLs at all
    assert "/tests/" not in alert.body
    assert alert.dashboard_url is None


def test_dashboard_links_join_cleanly_with_trailing_slash(session_factory):
    """A trailing-slash base URL never produces '//tests/…' or '//builds/…'."""
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED"})
        build = _process(s, 2, {"a.test": "FAILED"})
        s.commit()
        alert = build_regression_report(s, build, app_base_url=BASE + "/")
    assert alert is not None
    assert f"{BASE}/builds/2" in alert.body
    assert f"{BASE}/tests/" in alert.body
    assert "//tests/" not in alert.body.replace("://", "")
    assert "//builds/" not in alert.body.replace("://", "")


def test_recovery_notice_includes_build_link_when_base_url_set(session_factory):
    with session_factory() as s:
        _process(s, 1, {"a.test": "FAILED"})
        build = _process(s, 2, {"a.test": "FIXED"})  # back to green
        s.commit()
        alert = build_regression_report(s, build, recovery_notice=True, app_base_url=BASE)
        bare = build_regression_report(s, build, recovery_notice=True)
    assert alert is not None
    assert f"Dashboard: {BASE}/builds/2" in alert.body
    assert bare is not None
    assert "Dashboard:" not in bare.body


# ── The email channel: renders an Alert to the exact message, addressed to its recipients ─────────


def test_email_channel_renders_alert_verbatim():
    alert = Alert(kind=AlertKind.ops, title="UT Analyzer ops — x", body="line one\nline two\n")
    msg = _email_of(alert, recipients=("a@x", "b@x"))
    assert msg == EmailMessage(
        subject="UT Analyzer ops — x", body="line one\nline two\n", recipients=("a@x", "b@x")
    )


def test_build_ops_alert_prefixes_subject():
    alert = build_ops_alert(subject="poller is stale", body="the poller is stale\n")
    assert alert.kind is AlertKind.ops
    assert alert.title == "UT Analyzer ops — poller is stale"
    assert alert.body == "the poller is stale\n"


# ── SmtpEmailSender: the SMTP boundary (no socket is opened) ──────────────────────────────────────


class _RecordingSmtp:
    """A fake ``smtplib.SMTP`` recording the call sequence — no socket is ever opened (#120)."""

    def __init__(self, host: str, port: int, timeout: float | None = None) -> None:
        self.host, self.port, self.timeout = host, port, timeout
        self.calls: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        pass

    def starttls(self) -> None:
        self.calls.append(("starttls",))

    def login(self, user: str, password: str) -> None:
        self.calls.append(("login", user, password))

    def send_message(self, mime) -> None:
        self.calls.append(("send_message", mime["To"]))


def _send_via_fake_smtp(monkeypatch, sender: SmtpEmailSender) -> _RecordingSmtp:
    made: list[_RecordingSmtp] = []

    def _factory(host, port, timeout=None):
        made.append(_RecordingSmtp(host, port, timeout))
        return made[-1]

    monkeypatch.setattr(smtplib, "SMTP", _factory)
    sender.send(EmailMessage(subject="s", body="b", recipients=RCPT))
    assert len(made) == 1
    return made[0]


def test_smtp_sender_with_credentials_starttls_then_login_before_send(monkeypatch):
    """Configured credentials mean STARTTLS + login, in that order, before the message (#120)."""
    sender = SmtpEmailSender("relay", 587, "uta@example.com", user="bot", password="hunter2")
    smtp = _send_via_fake_smtp(monkeypatch, sender)
    assert smtp.calls == [("starttls",), ("login", "bot", "hunter2"), ("send_message", RCPT[0])]


def test_smtp_sender_without_credentials_is_plain_send(monkeypatch):
    """No credentials ⇒ exactly today's behavior: no starttls, no login."""
    smtp = _send_via_fake_smtp(monkeypatch, SmtpEmailSender("relay", 25, "uta@example.com"))
    assert smtp.calls == [("send_message", RCPT[0])]


def test_smtp_sender_explicit_starttls_overrides_credential_default(monkeypatch):
    """SMTP_STARTTLS set explicitly wins over the "on when credentials" default, both ways."""
    off = SmtpEmailSender("relay", 25, "f@x", user="bot", password="pw", starttls=False)
    assert _send_via_fake_smtp(monkeypatch, off).calls == [
        ("login", "bot", "pw"),
        ("send_message", RCPT[0]),
    ]
    on = SmtpEmailSender("relay", 25, "f@x", starttls=True)
    assert _send_via_fake_smtp(monkeypatch, on).calls == [("starttls",), ("send_message", RCPT[0])]


def test_smtp_sender_skips_send_without_recipients(monkeypatch):
    """An empty recipient list means email isn't addressed anywhere — no socket, no send."""
    made: list[_RecordingSmtp] = []
    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **k: made.append(1))
    SmtpEmailSender("relay", 25, "f@x").send(EmailMessage(subject="s", body="b", recipients=()))
    assert made == []


def test_build_email_sender_passes_credentials_through(monkeypatch):
    """The settings→sender builder forwards user/password/starttls, not just host/port/from."""
    settings = Settings(
        smtp_host="relay",
        smtp_port=587,
        smtp_from="uta@example.com",
        smtp_recipients="team@example.com",
        smtp_user="bot",
        smtp_password="hunter2",
        smtp_starttls=None,
    )
    sender = build_email_sender(settings)
    assert isinstance(sender, SmtpEmailSender)
    smtp = _send_via_fake_smtp(monkeypatch, sender)
    assert smtp.host == "relay"
    assert smtp.port == 587
    assert smtp.calls == [("starttls",), ("login", "bot", "hunter2"), ("send_message", RCPT[0])]


def test_empty_smtp_starttls_env_means_unset():
    """`.env.example` ships `SMTP_STARTTLS=`; an empty value must mean "default", not a crash."""
    assert Settings(smtp_starttls="").smtp_starttls is None
    assert Settings(smtp_starttls="false").smtp_starttls is False


def test_smtp_sender_dials_with_timeout(monkeypatch):
    """A black-holed relay must fail fast, not hang the caller — the dial carries a timeout."""
    seen: dict = {}

    class _FakeSmtp:
        def __init__(self, host, port, timeout=None):
            seen.update(host=host, port=port, timeout=timeout)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def send_message(self, mime):
            seen["sent"] = True

    monkeypatch.setattr(smtplib, "SMTP", _FakeSmtp)
    SmtpEmailSender("relay.example", 25, "uta@example.com").send(
        EmailMessage(subject="s", body="b", recipients=RCPT)
    )
    assert seen["sent"] is True
    assert seen["timeout"] is not None and seen["timeout"] > 0
