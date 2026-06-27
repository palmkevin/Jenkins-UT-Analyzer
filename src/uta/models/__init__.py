"""Full Information model — Milestone 1.

Table dependency order (each references only what came before it):
  runs → run_shards → test_identity → test_results → test_lifecycle
  → failure_episodes → run_signals → test_classifications → kb_signatures
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uta.db import Base

# ── Lifecycle / provenance constants ──────────────────────────────────────────
LIFECYCLE_FAILING = "FAILING"
LIFECYCLE_FIXED = "FIXED"
LIFECYCLE_REMOVED = "REMOVED"

TRIAGE_UNTRIAGED = "UNTRIAGED"
TRIAGE_INVESTIGATING = "INVESTIGATING"
TRIAGE_ROOT_CAUSED = "ROOT_CAUSED"
TRIAGE_RESOLVED = "RESOLVED"

PROVENANCE_AI_UNCONFIRMED = "AI_UNCONFIRMED"
PROVENANCE_AI_CONFIRMED = "AI_CONFIRMED"
PROVENANCE_HUMAN_CORRECTED = "HUMAN_CORRECTED"
PROVENANCE_HUMAN_ENTERED = "HUMAN_ENTERED"

CAUSE_CODE_CHANGE = "CODE_CHANGE"
CAUSE_DATA_CHANGE = "DATA_CHANGE"
CAUSE_INFRASTRUCTURE = "INFRASTRUCTURE"
CAUSE_UNKNOWN = "UNKNOWN"

SIGNAL_SVN_COMMIT = "SVN_COMMIT"
SIGNAL_DATA_CHANGE = "DATA_CHANGE"

EPISODE_OPEN = "OPEN"
EPISODE_CLOSED = "CLOSED"


# ── Run ───────────────────────────────────────────────────────────────────────


class Run(Base):
    """One Jenkins build. ``complete`` is True iff all expected shards reported."""

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    build_number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32))
    url: Mapped[str] = mapped_column(String(512), default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    complete: Mapped[bool] = mapped_column(default=False)
    # which complete run was the baseline when this run was processed
    baseline_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("runs.id"), nullable=True, index=True
    )

    shards: Mapped[list[RunShard]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    results: Mapped[list[TestResult]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    signals: Mapped[list[RunSignal]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    baseline_run: Mapped[Run | None] = relationship("Run", remote_side="Run.id")


class RunShard(Base):
    """Per-shard (permanent / permanent_py39) timing captured from Jenkins wfapi."""

    __tablename__ = "run_shards"
    __table_args__ = (UniqueConstraint("run_id", "track", name="uq_run_shard_track"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    track: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    run: Mapped[Run] = relationship(back_populates="shards")


# ── Test identity ─────────────────────────────────────────────────────────────


class TestIdentity(Base):
    """Stable canonical key for a test across runs, tracks, and renames.

    ``alias_of_id`` → the canonical identity when this row is a rename/move alias.
    ``alias_confirmed`` = True means a human has confirmed the alias relationship.
    Until confirmed the old identity is REMOVED and the new one FAILING — no history lost.
    """

    __test__ = False  # not a pytest test class despite the Test* name
    __tablename__ = "test_identity"

    id: Mapped[int] = mapped_column(primary_key=True)
    # "<class_name>.<method>" — the stable lookup key used in all queries
    test_id: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    suite: Mapped[str | None] = mapped_column(String(256), nullable=True)
    class_name: Mapped[str] = mapped_column(String(256))
    method: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    alias_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("test_identity.id"), nullable=True, index=True
    )
    alias_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)

    alias_of: Mapped[TestIdentity | None] = relationship(
        "TestIdentity", remote_side="TestIdentity.id", foreign_keys="TestIdentity.alias_of_id"
    )
    lifecycle: Mapped[TestLifecycle | None] = relationship(
        "TestLifecycle", back_populates="test_identity", uselist=False
    )
    episodes: Mapped[list[FailureEpisode]] = relationship(
        "FailureEpisode", back_populates="test_identity"
    )
    results: Mapped[list[TestResult]] = relationship("TestResult", back_populates="test_identity")
    classifications: Mapped[list[TestClassification]] = relationship(
        "TestClassification", back_populates="test_identity"
    )
    kb_signatures: Mapped[list[KbSignature]] = relationship(
        "KbSignature", back_populates="test_identity"
    )


# ── Test result (per run, per track) ─────────────────────────────────────────


class TestResult(Base):
    """One (run, test, track) result. ``test_identity_id`` FK populated during M2 ingest."""

    __test__ = False  # not a pytest test class despite the Test* name
    __tablename__ = "test_results"
    __table_args__ = (UniqueConstraint("run_id", "test_id", "track", name="uq_run_test_track"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    # denormalized string key for fast lookup; FK set when identity is resolved
    test_id: Mapped[str] = mapped_column(String(512), index=True)
    test_identity_id: Mapped[int | None] = mapped_column(
        ForeignKey("test_identity.id"), nullable=True, index=True
    )
    track: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner_initials: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped[Run] = relationship(back_populates="results")
    test_identity: Mapped[TestIdentity | None] = relationship(
        "TestIdentity", back_populates="results"
    )


# ── Lifecycle ─────────────────────────────────────────────────────────────────


class TestLifecycle(Base):
    """Current state for a test identity. One row per TestIdentity.

    ``state`` ∈ {FAILING, FIXED, REMOVED}.
    ``flaky`` is orthogonal to state (a FAILING test can also be FLAKY).
    ``acknowledged`` is orthogonal to state; clears on reopen (FIXED→FAILING transition).
    """

    __test__ = False  # not a pytest test class despite the Test* name
    __tablename__ = "test_lifecycle"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_identity_id: Mapped[int] = mapped_column(
        ForeignKey("test_identity.id"), unique=True, index=True
    )
    state: Mapped[str] = mapped_column(String(16), default=LIFECYCLE_FAILING)
    flaky: Mapped[bool] = mapped_column(Boolean, default=False)
    reopen_count: Mapped[int] = mapped_column(Integer, default=0)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    test_identity: Mapped[TestIdentity] = relationship("TestIdentity", back_populates="lifecycle")


# ── Failure episodes ──────────────────────────────────────────────────────────


class FailureEpisode(Base):
    """One row per fail→fix cycle for a test identity.

    ``episode_number`` is 1-based and increments on each reopen.
    ``fixed_in_run_id`` is NULL while the episode is still open (FAILING / REMOVED).
    The ``state`` column mirrors whether the episode is still open or closed.

    Human attribution fields:
    - ``cause`` — deterministic class (CODE_CHANGE / DATA_CHANGE / INFRASTRUCTURE / UNKNOWN)
    - ``reason`` — free text entered by the monitor
    - ``provenance`` — how the conclusion was reached (see PROVENANCE_* constants)
    - ``original_ai_value`` — preserved when the human overrides the AI suggestion
    - ``confirmed_by`` / ``confirmed_at`` — who validated + when
    - ``causing_person`` — the human-entered responsible party
    - ``triage_status`` — operational triage workflow state
    """

    __tablename__ = "failure_episodes"
    __table_args__ = (
        UniqueConstraint("test_identity_id", "episode_number", name="uq_episode_per_test"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    test_identity_id: Mapped[int] = mapped_column(ForeignKey("test_identity.id"), index=True)
    episode_number: Mapped[int] = mapped_column(Integer)
    first_failure_run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    fixed_in_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("runs.id"), nullable=True, index=True
    )
    state: Mapped[str] = mapped_column(String(16), default=EPISODE_OPEN)

    # attribution
    cause: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    provenance: Mapped[str | None] = mapped_column(String(32), nullable=True)
    original_ai_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    causing_person: Mapped[str | None] = mapped_column(String(128), nullable=True)
    triage_status: Mapped[str] = mapped_column(String(32), default=TRIAGE_UNTRIAGED)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    test_identity: Mapped[TestIdentity] = relationship("TestIdentity", back_populates="episodes")
    first_failure_run: Mapped[Run] = relationship("Run", foreign_keys=[first_failure_run_id])
    fixed_in_run: Mapped[Run | None] = relationship("Run", foreign_keys=[fixed_in_run_id])
    kb_signatures: Mapped[list[KbSignature]] = relationship("KbSignature", back_populates="episode")


# ── Signals (candidate code/data changes per run) ─────────────────────────────


class RunSignal(Base):
    """A candidate change (SVN commit or data change) associated with a run's window.

    ``signal_type`` ∈ {SVN_COMMIT, DATA_CHANGE}.
    ``details`` holds type-specific structured data (paths, component, entity, etc.).
    """

    __tablename__ = "run_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    signal_type: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    author: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    run: Mapped[Run] = relationship(back_populates="signals")


# ── Classification (deterministic per-test cause prediction per run) ──────────


class TestClassification(Base):
    """Predicted cause for a (run, test_identity) pair, produced by the ingest pipeline.

    ``predicted_cause`` ∈ {CODE_CHANGE, DATA_CHANGE, INFRASTRUCTURE, UNKNOWN}.
    ``llm_hypothesis`` is the LLM-generated narrative (null in v1 with the no-op stub).
    """

    __test__ = False  # not a pytest test class despite the Test* name

    __tablename__ = "test_classifications"
    __table_args__ = (
        UniqueConstraint("run_id", "test_identity_id", name="uq_classification_run_test"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    test_identity_id: Mapped[int] = mapped_column(ForeignKey("test_identity.id"), index=True)
    predicted_cause: Mapped[str | None] = mapped_column(String(32), nullable=True)
    llm_hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_contact: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[Run] = relationship("Run")
    test_identity: Mapped[TestIdentity] = relationship(
        "TestIdentity", back_populates="classifications"
    )


# ── Knowledge base signatures ─────────────────────────────────────────────────


class KbSignature(Base):
    """Normalized failure signature for knowledge-base lookups.

    ``sig_hash`` — SHA-256 of (test_id + normalized error text) for exact-match lookup.
    ``sig_text`` — normalized error text; a GIN/pg_trgm index on this column enables
    fuzzy similarity search (``similarity(sig_text, :query)`` with ``ORDER BY … DESC``).
    The GIN index is created in the Alembic migration (not in the SQLAlchemy model) so
    it is Postgres-only and does not affect the SQLite-based offline test suite.

    When a human confirms or corrects the cause/reason on an episode, a KbSignature row
    is created/updated with the validated attribution, making it available for future
    recurrence matching and LLM context retrieval.
    """

    __tablename__ = "kb_signatures"

    id: Mapped[int] = mapped_column(primary_key=True)
    sig_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    sig_text: Mapped[str] = mapped_column(Text)
    test_identity_id: Mapped[int] = mapped_column(ForeignKey("test_identity.id"), index=True)
    episode_id: Mapped[int | None] = mapped_column(
        ForeignKey("failure_episodes.id"), nullable=True, index=True
    )
    confirmed_cause: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confirmed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    provenance: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    test_identity: Mapped[TestIdentity] = relationship(
        "TestIdentity", back_populates="kb_signatures"
    )
    episode: Mapped[FailureEpisode | None] = relationship(
        "FailureEpisode", back_populates="kb_signatures"
    )


__all__ = [
    # constants
    "LIFECYCLE_FAILING",
    "LIFECYCLE_FIXED",
    "LIFECYCLE_REMOVED",
    "TRIAGE_UNTRIAGED",
    "TRIAGE_INVESTIGATING",
    "TRIAGE_ROOT_CAUSED",
    "TRIAGE_RESOLVED",
    "PROVENANCE_AI_UNCONFIRMED",
    "PROVENANCE_AI_CONFIRMED",
    "PROVENANCE_HUMAN_CORRECTED",
    "PROVENANCE_HUMAN_ENTERED",
    "CAUSE_CODE_CHANGE",
    "CAUSE_DATA_CHANGE",
    "CAUSE_INFRASTRUCTURE",
    "CAUSE_UNKNOWN",
    "SIGNAL_SVN_COMMIT",
    "SIGNAL_DATA_CHANGE",
    "EPISODE_OPEN",
    "EPISODE_CLOSED",
    # models
    "Run",
    "RunShard",
    "TestIdentity",
    "TestResult",
    "TestLifecycle",
    "FailureEpisode",
    "RunSignal",
    "TestClassification",
    "KbSignature",
]
