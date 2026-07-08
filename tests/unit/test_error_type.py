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


def test_timeout():
    assert derive_error_type("FAILED", "Operation timed out after 30s", None) == ErrorType.TIMEOUT


def test_generic_exception():
    trace = "ValueError: bad input"
    assert derive_error_type("FAILED", None, trace) == ErrorType.EXCEPTION


def test_unknown_when_no_signal():
    assert derive_error_type("FAILED", "test failed", "") == ErrorType.UNKNOWN
