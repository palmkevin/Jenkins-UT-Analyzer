"""String enums for the Information model.

Stored as plain ``varchar`` (not a native DB ENUM type) so the schema stays portable across
Postgres (production/CI) and SQLite (fast offline tests) and migrations don't carry enum-type
churn. The classes give the app a single source of truth for the allowed values.
"""

from __future__ import annotations

from enum import StrEnum


class LifecycleState(StrEnum):
    """About the test *result* — orthogonal to acknowledgement (see PLAN §1)."""

    FAILING = "FAILING"
    FIXED = "FIXED"
    REMOVED = "REMOVED"


class TriageStatus(StrEnum):
    UNTRIAGED = "UNTRIAGED"
    INVESTIGATING = "INVESTIGATING"
    ROOT_CAUSED = "ROOT_CAUSED"
    RESOLVED = "RESOLVED"


class AliasState(StrEnum):
    """Identity aliasing — manual merge ships v1; automatic *suggestion* is post-v1."""

    NONE = "NONE"
    SUGGESTED = "SUGGESTED"
    CONFIRMED = "CONFIRMED"


class PredictedCause(StrEnum):
    CODE_CHANGE = "CODE_CHANGE"
    DATA_CHANGE = "DATA_CHANGE"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    UNKNOWN = "UNKNOWN"


class Provenance(StrEnum):
    """How a cause/reason was reached — weights KB retrieval (PLAN §4)."""

    AI_UNCONFIRMED = "AI_UNCONFIRMED"
    AI_CONFIRMED = "AI_CONFIRMED"
    HUMAN_CORRECTED = "HUMAN_CORRECTED"
    HUMAN_ENTERED = "HUMAN_ENTERED"


class ChangeType(StrEnum):
    """Normalized ``V_TRACKING.TYPE`` (data-change feed)."""

    CREATE = "C"
    UPDATE = "U"
    DELETE = "D"


class ErrorType(StrEnum):
    """Derived from result + stack trace (PLAN §1 'Error type')."""

    ASSERTION = "ASSERTION"
    EXCEPTION = "EXCEPTION"
    TIMEOUT = "TIMEOUT"
    INFRA = "INFRA"
    UNKNOWN = "UNKNOWN"


# Raw Jenkins per-test statuses (kept verbatim on the result; lifecycle is computed separately).
RESULT_STATUSES = ("PASSED", "FAILED", "REGRESSION", "FIXED", "SKIPPED")
