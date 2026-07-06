"""Regression-only email.

The contract: a message goes out **only** when a processed run introduces ≥1 new failing test;
otherwise silence (unless the recovery-notice toggle is on and the run is back to green).
"""

from __future__ import annotations

from tests.builders import _EPOCH, make_run
from tests.fakes.email import RecordingEmailSender
from uta.analyze.classify import classify_run
from uta.analyze.lifecycle import apply_run
from uta.delivery.email import build_regression_report, maybe_notify
from uta.models import CodeChangeCandidate

RCPT = ("team@example.com",)


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


def test_maybe_notify_sends_via_sender(session_factory):
    sender = RecordingEmailSender()
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED"})
        run = _process(s, 2, {"a.test": "FAILED"})
        s.commit()
        out = maybe_notify(s, run, sender, RCPT)
    assert out is not None
    assert len(sender.sent) == 1
    assert sender.sent[0].subject == out.subject


def test_maybe_notify_noop_without_sender_or_recipients(session_factory):
    sender = RecordingEmailSender()
    with session_factory() as s:
        _process(s, 1, {"a.test": "PASSED"})
        run = _process(s, 2, {"a.test": "FAILED"})
        s.commit()
        assert maybe_notify(s, run, None, RCPT) is None  # no sender
        assert maybe_notify(s, run, sender, ()) is None  # no recipients
    assert sender.sent == []
