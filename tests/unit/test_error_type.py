"""Error-type derivation (uta.analyze.error_type)."""

from __future__ import annotations

import pytest

from uta.analyze.error_type import derive_error_type
from uta.models.enums import ErrorType


@pytest.mark.parametrize("status", ["PASSED", "FIXED", "SKIPPED"])
def test_non_failures_have_no_error_type(status):
    assert derive_error_type(status, "anything", "traceback") is None


def test_assertion():
    trace = "self.assertEqual(x, y)\nAssertionError: 42 != 37"
    assert derive_error_type("FAILED", None, trace) == ErrorType.ASSERTION


def test_infra_beats_exception():
    # A ConnectionError is an exception too, but INFRA must win.
    details = "OperationalError: ORA-12541: TNS:no listener"
    assert derive_error_type("REGRESSION", details, None) == ErrorType.INFRA


@pytest.mark.parametrize(
    "details",
    [
        "OracleError: connection to the database was lost",
        "oracledb.OperationalError: DPY-6005: cannot connect to database",
        "oracledb.DatabaseError: DPY-4011: the database or network closed the connection",
        "ORA-01234: cannot end backup of file",
        "ORA-12541: TNS:listener does not currently know of service",
        "socket.timeout: timed out",
        "ConnectionRefusedError: [Errno 111] Connection refused",
    ],
)
def test_infra_signals(details):
    assert derive_error_type("FAILED", details, None) == ErrorType.INFRA


@pytest.mark.parametrize(
    "details",
    [
        # "oerror" hides inside these names — must not read as OracleError (issue #86).
        "IOError: [Errno 2] No such file or directory: 'cfg.ini'",
        "ProtoError: unexpected wire type",
    ],
)
def test_error_suffix_substrings_are_not_infra(details):
    assert derive_error_type("FAILED", details, None) == ErrorType.EXCEPTION


def test_websocket_is_not_socket_infra():
    # "socket." must not fire inside "websocket." (issue #86).
    details = "websocket.exceptions.ConnectionClosed: code = 1006 (connection closed abnormally)"
    assert derive_error_type("FAILED", details, None) == ErrorType.UNKNOWN


def test_embedded_http_status_digits_are_not_infra():
    # "503 " inside a larger number must not read as an HTTP 503.
    assert derive_error_type("FAILED", "expected 1503 rows, got 7", None) == ErrorType.UNKNOWN


@pytest.mark.parametrize(
    "details",
    [
        "AssertionError: Decimal('12.504 ') != Decimal('12.50')",
        "AssertionError: 1.503 != 1.5 within 7 places",
        "AssertionError: Lists differ: [1, 504 , 3] != [1, 2, 3]",
    ],
)
def test_numeric_5xx_lookalikes_are_not_infra(details):
    assert derive_error_type("FAILED", "test failure", details) == ErrorType.ASSERTION


@pytest.mark.parametrize(
    "details",
    [
        "urllib.error.HTTPError: HTTP Error 502: Bad Gateway",
        "HTTP Error 502 : Bad Gateway",
        "HTTP/1.1 503 ",
        "requests.exceptions.HTTPError: 504 Server Error: Gateway Time-out for url: x",
        "unexpected status code 504",
        "curl: (22) The requested URL returned error: 502",
    ],
)
def test_http_5xx_is_infra(details):
    assert derive_error_type("FAILED", details, None) == ErrorType.INFRA


def test_timeout():
    assert derive_error_type("FAILED", "Operation timed out after 30s", None) == ErrorType.TIMEOUT


def test_timeout_in_frame_path_is_not_timeout():
    trace = (
        "Traceback (most recent call last):\n"
        '  File "/w/release/permanent/tests/dev/ut_a/test_timeout_rules.py", line 12, in '
        "test_session_timeout\n"
        "    self.assertEqual(rule.minutes, 30)\n"
        "AssertionError: 15 != 30"
    )
    assert derive_error_type("FAILED", "test failure", trace) == ErrorType.ASSERTION


def test_timeout_exception_line_still_typed_timeout():
    trace = (
        "Traceback (most recent call last):\n"
        '  File "/w/release/permanent/tests/dev/ut_a/test_x.py", line 3, in test_x\n'
        "TimeoutError: lock wait exceeded"
    )
    assert derive_error_type("FAILED", None, trace) == ErrorType.TIMEOUT


def test_generic_exception():
    trace = "ValueError: bad input"
    assert derive_error_type("FAILED", None, trace) == ErrorType.EXCEPTION


def test_unknown_when_no_signal():
    assert derive_error_type("FAILED", "test failed", "") == ErrorType.UNKNOWN
