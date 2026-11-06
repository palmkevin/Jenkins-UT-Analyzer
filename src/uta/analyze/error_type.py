"""Derive the per-result **error type** from status + stack trace.

A small, ordered set of substring/regex checks over the JUnit ``errorDetails`` and
``errorStackTrace``. It distinguishes the four buckets the monitor cares about — an assertion
(value mismatch), a thrown exception, a timeout, or an infrastructure fault (DB/network) — falling
back to UNKNOWN. INFRA is the load-bearing one: it feeds the deterministic classifier
(:mod:`uta.analyze.classify`), letting an environmental failure outrank code/data candidates.

Kept deliberately conservative and dependency-free so it is cheap to run on every failing result
and easy to test against the committed golden traces.
"""

from __future__ import annotations

import re

from uta.models.enums import ErrorType

_FAILED = frozenset({"FAILED", "REGRESSION"})

# Ordered, most-specific first. Each pattern is matched against details + stack trace (lower-cased).
# Every token is anchored (``\b`` / lookbehind) so a substring can't type an ordinary code failure
# as INFRA — unanchored, "oerror" hid inside IOError/ProtoError and "socket." inside websocket.*
# (issue #86). The generic TIMEOUT/ASSERTION patterns below stay unanchored on purpose: their
# substring hits (ReadTimeoutError, MyAssertionError) are still timeouts/assertions.
#
# A bare 502/503/504 is only an HTTP gateway/availability error in HTTP context — "HTTP Error 502",
# "HTTP/1.1 503", "status code 504", curl's "returned error: 503", or followed by its reason
# phrase. A bare "504 " also occurs in ordinary numeric assertions (``Decimal('12.504 ')``,
# ``[1, 504 , 3]``), which must stay code/data failures, not INFRA.
_5XX = r"50[234]\b(?!\.\d)"
_HTTP_5XX = (
    r"\bhttp(?:/\d(?:\.\d)?)?(?:\s+error)?\s*:?\s*" + _5XX + "|"
    r"\bstatus(?:[ _]code)?\s*[:=]?\s*" + _5XX + "|"
    r"\breturned error:?\s*" + _5XX + "|"
    r"\b50[234]\s*:?\s*(?:bad gateway|service unavailable|gateway time-?out|server error)\b"
)
_INFRA_RE = re.compile(
    r"connection refused|connection reset|could not connect|"
    r"\boperationalerror\b|\boracleerror\b|\boracledb\.|\bora-\d{4,5}\b|\btns:|"
    r"(?<![\w.])socket\.|\beconnrefused\b|network is unreachable|no route to host|"
    r"database is locked|\bdeadlock|service unavailable|" + _HTTP_5XX,
    re.IGNORECASE,
)
_TIMEOUT_RE = re.compile(r"timeout|timed out|timeouterror|deadline exceeded", re.IGNORECASE)
_ASSERTION_RE = re.compile(r"assertionerror|assertion failed|\bassert\b", re.IGNORECASE)
# Any "SomethingError"/"SomethingException" token signals a thrown exception.
_EXCEPTION_RE = re.compile(r"\b\w+(?:Error|Exception)\b")


def derive_error_type(
    status: str, error_details: str | None, error_stack_trace: str | None
) -> str | None:
    """Return the :class:`ErrorType` value for a result, or ``None`` if it did not fail.

    Order matters: INFRA and TIMEOUT are checked before the generic assertion/exception buckets so
    a ``ConnectionError`` reads as INFRA rather than EXCEPTION.
    """
    if status not in _FAILED:
        return None
    blob = f"{error_details or ''}\n{error_stack_trace or ''}"
    if _INFRA_RE.search(blob):
        return ErrorType.INFRA
    if _TIMEOUT_RE.search(blob):
        return ErrorType.TIMEOUT
    if _ASSERTION_RE.search(blob):
        return ErrorType.ASSERTION
    if _EXCEPTION_RE.search(blob):
        return ErrorType.EXCEPTION
    return ErrorType.UNKNOWN
