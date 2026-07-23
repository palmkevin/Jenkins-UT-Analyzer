"""Regression-only email.

The contract: a message goes out **only** when a processed build introduces ≥1 new failing test;
otherwise silence (unless the recovery-notice toggle is on and the build is back to green).
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
from uta.delivery.email import (
    EmailMessage,
    SmtpEmailSender,
    build_regression_report,
    send_alert,
    send_ops_alert,
)
from uta.models import CodeChangeCandidate, TestIdentity

RCPT = ("team@example.com",)
BASE = "http://uta.example:8000"


def _process(session, build, statuses, **kw):
    build = make_build(session, build, statuses, **kw)
    apply_build(session, build)  # drives baseline + episodes so regressions are known
    session.flush()
    return build


def test_no_email_when_no_new_failures(session_factory):
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED"})
        build = _process(s, 2, {"a.test": "PASSED"})
        s.commit()
        assert build_regression_report(s, build, RCPT) is None


def test_email_on_regression_leads_with_new_failures(session_factory):
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED", "b.test": "PASSED"})
        build = _process(s, 2, {"a.test": "FAILED", "b.test": "PASSED"})
        s.commit()
        msg = build_regression_report(s, build, RCPT)
    assert msg is not None
    assert "1 new failing" in msg.subject
    assert "a.test" in msg.body
    assert "NEW FAILURES" in msg.body
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
        msg = build_regression_report(s, build, RCPT)
    assert msg is not None
    assert "cause: CODE_CHANGE" in msg.body
    assert "contact: R. Devlin" in msg.body


def test_recovery_notice_only_when_toggled_and_green(session_factory):
    with session_factory() as s:
        _process(s, 1, {"a.test": "FAILED"})
        build = _process(s, 2, {"a.test": "FIXED"})  # back to green
        s.commit()
        assert build_regression_report(s, build, RCPT) is None  # off by default
        msg = build_regression_report(s, build, RCPT, recovery_notice=True)
    assert msg is not None
    assert "back to green" in msg.subject


def test_no_recovery_notice_when_already_green(session_factory):
    """A green build after a green baseline is *still* green, not *back to* green — no email."""
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED"})
        build = _process(s, 2, {"a.test": "PASSED"})
        s.commit()
        assert build_regression_report(s, build, RCPT, recovery_notice=True) is None


def test_no_recovery_notice_on_first_ever_green_run(session_factory):
    """An all-green first build has no baseline, so nothing transitioned — no email."""
    with session_factory() as s:
        build = _process(s, 1, {"a.test": "PASSED"})
        s.commit()
        assert build_regression_report(s, build, RCPT, recovery_notice=True) is None


def test_recovery_notice_when_baseline_failure_was_removed(session_factory):
    """A baseline failure absent this build (test deleted) still turns the suite green — notice."""
    with session_factory() as s:
        _process(s, 1, {"a.test": "FAILED", "b.test": "PASSED"})
        build = _process(s, 2, {"b.test": "PASSED"})  # a.test removed
        s.commit()
        msg = build_regression_report(s, build, RCPT, recovery_notice=True)
    assert msg is not None
    assert "back to green" in msg.subject


def test_dashboard_links_when_base_url_set(session_factory):
    """Each new failure links its per-test record; the build summary is linked too (#108)."""
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED", "b.test": "PASSED"})
        build = _process(s, 2, {"a.test": "FAILED", "b.test": "FAILED"})
        s.commit()
        msg = build_regression_report(s, build, RCPT, app_base_url=BASE)
        ids = {
            i.canonical_name: i.id
            for i in s.scalars(
                select(TestIdentity).where(TestIdentity.canonical_name.in_(["a.test", "b.test"]))
            )
        }
    assert msg is not None
    assert f"{BASE}/tests/{ids['a.test']}" in msg.body
    assert f"{BASE}/tests/{ids['b.test']}" in msg.body
    assert f"Dashboard: {BASE}/builds/2" in msg.body


def test_no_dashboard_links_when_base_url_unset(session_factory):
    """The default (no APP_BASE_URL) keeps the body exactly link-free — no 'Dashboard:' stubs."""
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED"})
        build = _process(s, 2, {"a.test": "FAILED"})
        s.commit()
        msg = build_regression_report(s, build, RCPT)
    assert msg is not None
    assert "Dashboard:" not in msg.body
    assert "http" not in msg.body  # make_build sets no Jenkins url either — zero URLs at all
    assert "/tests/" not in msg.body


def test_dashboard_links_join_cleanly_with_trailing_slash(session_factory):
    """A trailing-slash base URL never produces '//tests/…' or '//builds/…'."""
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED"})
        build = _process(s, 2, {"a.test": "FAILED"})
        s.commit()
        msg = build_regression_report(s, build, RCPT, app_base_url=BASE + "/")
    assert msg is not None
    assert f"{BASE}/builds/2" in msg.body
    assert f"{BASE}/tests/" in msg.body
    assert "//tests/" not in msg.body.replace("://", "")
    assert "//builds/" not in msg.body.replace("://", "")


def test_recovery_notice_includes_build_link_when_base_url_set(session_factory):
    with session_factory() as s:
        _process(s, 1, {"a.test": "FAILED"})
        build = _process(s, 2, {"a.test": "FIXED"})  # back to green
        s.commit()
        msg = build_regression_report(s, build, RCPT, recovery_notice=True, app_base_url=BASE)
        bare = build_regression_report(s, build, RCPT, recovery_notice=True)
    assert msg is not None
    assert f"Dashboard: {BASE}/builds/2" in msg.body
    assert bare is not None
    assert "Dashboard:" not in bare.body


def test_send_alert_delivers_via_sender(session_factory):
    sender = RecordingEmailSender()
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED"})
        build = _process(s, 2, {"a.test": "FAILED"})
        s.commit()
        msg = build_regression_report(s, build, RCPT)
    assert msg is not None
    assert send_alert(sender, msg) is True
    assert sender.sent == [msg]


def test_send_alert_swallows_sender_failure():
    """A raising sender is logged and dropped, never raised — alerting is best-effort (#81)."""

    class _RaisingSender:
        def send(self, message: EmailMessage) -> None:
            raise smtplib.SMTPException("relay down")

    msg = EmailMessage(subject="s", body="b", recipients=RCPT)
    assert send_alert(_RaisingSender(), msg) is False


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


def test_send_ops_alert_delivers_via_sender():
    sender = RecordingEmailSender()
    msg = send_ops_alert(sender, RCPT, subject="poller is stale", body="b")
    assert msg is not None
    assert sender.sent == [msg]
    assert msg.subject == "UT Analyzer ops — poller is stale"


def test_send_ops_alert_swallows_sender_failure():
    """Ops alerting is best-effort like send_alert: a raising sender yields ``None``, not an
    exception — an SMTP outage must not 500 ``/health`` or erase the poller's tick record."""

    class _RaisingSender:
        def send(self, message: EmailMessage) -> None:
            raise smtplib.SMTPException("relay down")

    assert send_ops_alert(_RaisingSender(), RCPT, subject="poller is stale", body="b") is None


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
