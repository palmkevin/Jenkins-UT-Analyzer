"""Regression-only email.

The contract: a message goes out **only** when a processed run introduces ≥1 new failing test;
otherwise silence (unless the recovery-notice toggle is on and the run is back to green).
"""

from __future__ import annotations

import smtplib

from sqlalchemy import select

from tests.builders import _EPOCH, make_run
from tests.fakes.email import RecordingEmailSender
from uta.analyze.classify import classify_run
from uta.analyze.lifecycle import apply_run
from uta.delivery.email import EmailMessage, build_regression_report, send_alert
from uta.models import CodeChangeCandidate, TestIdentity

RCPT = ("team@example.com",)
BASE = "http://uta.example:8000"


def _process(session, build, statuses, **kw):
    run = make_run(session, build, statuses, **kw)
    apply_run(session, run)  # drives baseline + episodes so regressions are known
    session.flush()
    return run


def test_no_email_when_no_new_failures(session_factory):
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED"})
        run = _process(s, 2, {"a.test": "PASSED"})
        s.commit()
        assert build_regression_report(s, run, RCPT) is None


def test_email_on_regression_leads_with_new_failures(session_factory):
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED", "b.test": "PASSED"})
        run = _process(s, 2, {"a.test": "FAILED", "b.test": "PASSED"})
        s.commit()
        msg = build_regression_report(s, run, RCPT)
    assert msg is not None
    assert "1 new failing" in msg.subject
    assert "a.test" in msg.body
    assert "NEW FAILURES" in msg.body
    assert msg.recipients == RCPT


def test_email_shows_suggested_contact_for_new_failure(session_factory):
    # The classifier suggests the sole commit author (#49); the new-failure line carries it.
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED"})
        run = make_run(s, 2, {"a.test": "FAILED"})
        run.code_changes.append(
            CodeChangeCandidate(commit_id="r888", author="R. Devlin", committed_at=_EPOCH)
        )
        analysis = apply_run(s, run)
        s.flush()
        classify_run(s, run, analysis.opened_episodes)
        s.commit()
        msg = build_regression_report(s, run, RCPT)
    assert msg is not None
    assert "cause: CODE_CHANGE" in msg.body
    assert "contact: R. Devlin" in msg.body


def test_recovery_notice_only_when_toggled_and_green(session_factory):
    with session_factory() as s:
        _process(s, 1, {"a.test": "FAILED"})
        run = _process(s, 2, {"a.test": "FIXED"})  # back to green
        s.commit()
        assert build_regression_report(s, run, RCPT) is None  # off by default
        msg = build_regression_report(s, run, RCPT, recovery_notice=True)
    assert msg is not None
    assert "back to green" in msg.subject


def test_dashboard_links_when_base_url_set(session_factory):
    """Each new failure links its per-test record; the run summary is linked too (#108)."""
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED", "b.test": "PASSED"})
        run = _process(s, 2, {"a.test": "FAILED", "b.test": "FAILED"})
        s.commit()
        msg = build_regression_report(s, run, RCPT, app_base_url=BASE)
        ids = {
            i.canonical_name: i.id
            for i in s.scalars(
                select(TestIdentity).where(TestIdentity.canonical_name.in_(["a.test", "b.test"]))
            )
        }
    assert msg is not None
    assert f"{BASE}/tests/{ids['a.test']}" in msg.body
    assert f"{BASE}/tests/{ids['b.test']}" in msg.body
    assert f"Dashboard: {BASE}/runs/2" in msg.body


def test_no_dashboard_links_when_base_url_unset(session_factory):
    """The default (no APP_BASE_URL) keeps the body exactly link-free — no 'Dashboard:' stubs."""
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED"})
        run = _process(s, 2, {"a.test": "FAILED"})
        s.commit()
        msg = build_regression_report(s, run, RCPT)
    assert msg is not None
    assert "Dashboard:" not in msg.body
    assert "http" not in msg.body  # make_run sets no Jenkins url either — zero URLs at all
    assert "/tests/" not in msg.body


def test_dashboard_links_join_cleanly_with_trailing_slash(session_factory):
    """A trailing-slash base URL never produces '//tests/…' or '//runs/…'."""
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED"})
        run = _process(s, 2, {"a.test": "FAILED"})
        s.commit()
        msg = build_regression_report(s, run, RCPT, app_base_url=BASE + "/")
    assert msg is not None
    assert f"{BASE}/runs/2" in msg.body
    assert f"{BASE}/tests/" in msg.body
    assert "//tests/" not in msg.body.replace("://", "")
    assert "//runs/" not in msg.body.replace("://", "")


def test_recovery_notice_includes_run_link_when_base_url_set(session_factory):
    with session_factory() as s:
        _process(s, 1, {"a.test": "FAILED"})
        run = _process(s, 2, {"a.test": "FIXED"})  # back to green
        s.commit()
        msg = build_regression_report(s, run, RCPT, recovery_notice=True, app_base_url=BASE)
        bare = build_regression_report(s, run, RCPT, recovery_notice=True)
    assert msg is not None
    assert f"Dashboard: {BASE}/runs/2" in msg.body
    assert bare is not None
    assert "Dashboard:" not in bare.body


def test_send_alert_delivers_via_sender(session_factory):
    sender = RecordingEmailSender()
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED"})
        run = _process(s, 2, {"a.test": "FAILED"})
        s.commit()
        msg = build_regression_report(s, run, RCPT)
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
