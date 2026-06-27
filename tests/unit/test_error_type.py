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


def test_timeout():
    assert derive_error_type("FAILED", "Operation timed out after 30s", None) == ErrorType.TIMEOUT


def test_generic_exception():
    trace = "ValueError: bad input"
    assert derive_error_type("FAILED", None, trace) == ErrorType.EXCEPTION


def test_unknown_when_no_signal():
    assert derive_error_type("FAILED", "test failed", "") == ErrorType.UNKNOWN
