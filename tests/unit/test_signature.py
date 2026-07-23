"""Signature normalization (the load-bearing mask set).

The whole learning loop dies if the same bug doesn't hash to itself across builds, and collapses if
distinct bugs collide. These tests pin both directions: same-bug variants normalize identically;
different bugs stay apart; the mask table from the PLAN is honoured.
"""

from __future__ import annotations

from uta.kb.signature import compute_hash, display_message, normalize

_STACK_TMPL = (
    "Traceback (most recent call last):\n"
    '  File "/opt/ls/lx/release/{track}/tests/dev/ut_accounting/ac_csvc.py", '
    "line {line}, in test_x\n"
    "    self.assertEqual(a, b)\n"
    "AssertionError: {msg}\n"
)


def test_masks_match_the_plan_table():
    sig = normalize(
        "expected 42 but was 37; User 0x7f3a9c at 2026-06-26T14:03:11 "
        "from 10.2.3.4:5432 id 550e8400-e29b-41d4-a716-446655440000",
        None,
    )
    assert sig is not None
    assert "<NUM>" in sig.text and "42" not in sig.text and "37" not in sig.text
    assert "<HEX>" in sig.text and "0x7f3a9c" not in sig.text
    assert "<TS>" in sig.text and "2026-06-26" not in sig.text
    assert "<IP>:<PORT>" in sig.text and "10.2.3.4" not in sig.text
    assert "<UUID>" in sig.text and "550e8400" not in sig.text


def test_same_bug_different_run_normalizes_identically():
    a = normalize("test failure", _STACK_TMPL.format(track="permanent", line=793, msg="13 != 99"))
    b = normalize("test failure", _STACK_TMPL.format(track="permanent", line=801, msg="5 != 7"))
    assert a is not None and b is not None
    # line numbers + assertion values differ build-to-build; the signature must not.
    assert a.text == b.text
    assert a.exception_type == "AssertionError"


def test_same_bug_across_tracks_normalizes_identically():
    perm = normalize("f", _STACK_TMPL.format(track="permanent", line=12, msg="x"))
    py39 = normalize("f", _STACK_TMPL.format(track="permanent_py39", line=12, msg="x"))
    assert perm is not None and py39 is not None
    assert perm.text == py39.text  # track is an attribute, not part of identity


def test_distinct_exceptions_do_not_collide():
    a = normalize("f", _STACK_TMPL.format(track="permanent", line=1, msg="nope"))
    b = normalize(
        "f",
        "Traceback (most recent call last):\n"
        '  File "/opt/ls/lx/release/permanent/tests/dev/ut_accounting/ac_csvc.py", '
        "line 1, in test_x\n"
        "    raise ValueError(x)\n"
        "ValueError: bad value\n",
    )
    assert a is not None and b is not None
    assert a.text != b.text


def test_hash_is_identity_scoped_and_stable():
    sig = normalize("f", _STACK_TMPL.format(track="permanent", line=1, msg="x"))
    assert sig is not None
    h1 = compute_hash("ut_accounting.ac_csvc.test_a", sig.text)
    h2 = compute_hash("ut_accounting.ac_csvc.test_a", sig.text)
    h3 = compute_hash("ut_accounting.ac_csvc.test_b", sig.text)
    assert h1 == h2  # deterministic
    assert h1 != h3  # same text, different test ⇒ different signature
    assert len(h1) == 64


def test_empty_input_yields_no_signature():
    assert normalize(None, None) is None
    assert normalize("", "") is None


def test_display_message_prefers_exception_line_over_details():
    """`errorDetails` is usually the constant "test failure" — the exception line is the signal."""
    stack = _STACK_TMPL.format(track="permanent", line=42, msg="13 != 99")
    assert display_message("test failure", stack) == "AssertionError: 13 != 99"


def test_display_message_keeps_last_exception_line_of_chained_traceback():
    stack = (
        "Traceback (most recent call last):\n"
        '  File "/opt/ls/lx/release/permanent/tests/dev/a.py", line 1, in test_a\n'
        "KeyError: 'MSH'\n"
        "\n"
        "During handling of the above exception, another exception occurred:\n"
        "\n"
        "Traceback (most recent call last):\n"
        '  File "/opt/ls/lx/release/permanent/tests/dev/a.py", line 2, in test_a\n'
        "RuntimeError: could not build ACK\n"
    )
    # Same "last exception line wins" rule as normalize() — snippet and signature agree.
    assert display_message("test failure", stack) == "RuntimeError: could not build ACK"


def test_display_message_falls_back_to_details_then_none():
    assert display_message("boom happened", None) == "boom happened"
    assert display_message("boom happened", "no traceback here") == "boom happened"
    assert display_message("  ", None) is None
    assert display_message(None, None) is None


def test_keeps_only_our_frames_top_n():
    stack = (
        "Traceback (most recent call last):\n"
        '  File "/usr/lib/python3.12/unittest/case.py", line 59, in build\n'
        '  File "/opt/ls/lx/release/permanent/tests/dev/a.py", line 1, in test_a\n'
        '  File "/opt/ls/lx/release/permanent/tests/dev/b.py", line 2, in helper\n'
        "RuntimeError: boom\n"
    )
    sig = normalize("x", stack, top_frames=1)
    assert sig is not None
    assert "unittest/case.py" not in sig.text  # stdlib frame dropped
    assert sig.text.count(" in ") == 1  # only the top OUR frame kept
    assert "a.py:<LINE> in test_a" in sig.text
