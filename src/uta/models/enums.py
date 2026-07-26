"""String enums for the Information model.

Stored as plain ``varchar`` (not a native DB ENUM type) so the schema stays portable across
Postgres (production/CI) and SQLite (fast offline tests) and migrations don't carry enum-type
churn. The classes give the app a single source of truth for the allowed values.
"""

from __future__ import annotations

from enum import StrEnum


class LifecycleState(StrEnum):
    """About the test *result* — orthogonal to acknowledgement."""

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


class IncidentKind(StrEnum):
    """Discriminator for a **Build Incident** — a build-level condition requiring human triage.

    Two kinds are implemented today, keyed off the build's top-level Jenkins ``result``:

    - ``PIPELINE_FAILURE`` — the build itself failed (``result == FAILURE``): the full analysis
      stack (change candidates → classification → LLM hypothesis) applies.
    - ``ABORTED`` — the build was aborted (``result == ABORTED``): no signature, no classification,
      no change candidates — straight to a human-documented reason.

    ``SLOW`` is **reserved** for issue #172 (a *completed* build slower than its Expected Duration).
    It is defined here so the enum, schema and UI are forward-compatible with no future churn, but
    there is **no detector** for it yet. There is deliberately no ``HUNG`` kind: an overrunning
    *in-progress* build is a live, poller-observed banner, **never** a persisted Build Incident
    (ADR-0006, issue #184) — the durable record comes only from the ``aborted`` incident if a human
    stops it.
    """

    PIPELINE_FAILURE = "PIPELINE_FAILURE"
    ABORTED = "ABORTED"
    # ── Reserved for #172: a completed-build duration regression (no detector yet) ─────────────
    SLOW = "SLOW"


class SignatureKind(StrEnum):
    """Namespace for a :class:`~uta.models.kb.FailureSignature`.

    Test-failure signatures and build-incident signatures live in the **same** table but must never
    cross-match: a recurrence/similarity lookup in one space only sees signatures of that space. The
    kind is folded into the signature hash (so the exact-recurrence key is namespaced too) and every
    retrieval query filters on it.
    """

    TEST = "TEST"
    INCIDENT = "INCIDENT"


class Provenance(StrEnum):
    """How a cause/reason was reached — weights KB retrieval."""

    AI_UNCONFIRMED = "AI_UNCONFIRMED"
    AI_CONFIRMED = "AI_CONFIRMED"
    HUMAN_CORRECTED = "HUMAN_CORRECTED"
    HUMAN_ENTERED = "HUMAN_ENTERED"


class IngestJobStatus(StrEnum):
    """Lifecycle of an on-demand ingest / re-analysis job (in-app control panel, issue #16)."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"


class ChangeType(StrEnum):
    """Normalized ``V_TRACKING.TYPE`` (data-change feed)."""

    CREATE = "C"
    UPDATE = "U"
    DELETE = "D"


class ErrorType(StrEnum):
    """Derived from result + stack trace."""

    ASSERTION = "ASSERTION"
    EXCEPTION = "EXCEPTION"
    TIMEOUT = "TIMEOUT"
    INFRA = "INFRA"
    UNKNOWN = "UNKNOWN"


# Raw Jenkins per-test statuses (kept verbatim on the result; lifecycle is computed separately).
RESULT_STATUSES = ("PASSED", "FAILED", "REGRESSION", "FIXED", "SKIPPED")
