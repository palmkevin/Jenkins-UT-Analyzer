"""Lifecycle state + failure episodes (Information model: 'Test lifecycle', 'Failure episodes').

Two things are deliberately separated (PLAN §1): the **lifecycle state** (about the result:
FAILING/FIXED/REMOVED + a FLAKY flag) and **acknowledgement** (an orthogonal flag + actor +
timestamp that splits the New vs Still-failing buckets, *not* a state). Episodes make regressions
first-class: one row per fail→fix cycle so history accumulates instead of being overwritten.

``actor`` columns are plain strings (Phase-1 self-declared name; Phase-2 Keycloak swaps the value
with no data-model change) — the single shared identity field the PLAN calls for.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uta.db import Base
from uta.models.enums import LifecycleState, TriageStatus
from uta.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from uta.models.attribution import Attribution
    from uta.models.classification import Classification
    from uta.models.identity import TestIdentity


class TestLifecycle(Base, TimestampMixin):
    """Current state of one test identity (1:1)."""

    __test__ = False  # not a pytest test class despite the Test* name
    __tablename__ = "test_lifecycles"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_identity_id: Mapped[int] = mapped_column(
        ForeignKey("test_identities.id"), unique=True, index=True
    )

    state: Mapped[str] = mapped_column(String(16), default=LifecycleState.FAILING, index=True)
    flaky: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    reopen_count: Mapped[int] = mapped_column(Integer, default=0)

    # Acknowledgement — orthogonal attribute, cleared on reopen (PLAN §1).
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # All-time first failure is retained across episodes (the current episode tracks its own).
    all_time_first_failure_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("runs.id"), nullable=True
    )
    all_time_first_failure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_failing_run_id: Mapped[int | None] = mapped_column(ForeignKey("runs.id"), nullable=True)
    last_failing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    current_episode_id: Mapped[int | None] = mapped_column(
        ForeignKey("failure_episodes.id", use_alter=True, name="fk_lifecycle_current_episode"),
        nullable=True,
    )

    identity: Mapped[TestIdentity] = relationship(back_populates="lifecycle")
    current_episode: Mapped[FailureEpisode | None] = relationship(
        foreign_keys=[current_episode_id], post_update=True
    )


class FailureEpisode(Base, TimestampMixin):
    """One fail→fix cycle for a test identity."""

    __tablename__ = "failure_episodes"
    __table_args__ = (
        UniqueConstraint("test_identity_id", "episode_number", name="uq_episode_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    test_identity_id: Mapped[int] = mapped_column(ForeignKey("test_identities.id"), index=True)
    episode_number: Mapped[int] = mapped_column(Integer)  # 1, 2, 3 … per identity

    first_failure_run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"))
    first_failure_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_failing_run_id: Mapped[int | None] = mapped_column(ForeignKey("runs.id"), nullable=True)
    last_failing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Set ONLY when the test ran and passed again — never on REMOVED (disappeared ≠ fixed).
    fixed_in_run_id: Mapped[int | None] = mapped_column(ForeignKey("runs.id"), nullable=True)
    fixed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_open: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    age_runs: Mapped[int] = mapped_column(Integer, default=0)
    triage_status: Mapped[str] = mapped_column(String(16), default=TriageStatus.UNTRIAGED)
    # Human-entered Jira ticket this episode is tracked under (e.g. "ABC-123"); links into Jira.
    jira_ticket: Mapped[str | None] = mapped_column(String(32), nullable=True)

    identity: Mapped[TestIdentity] = relationship(
        back_populates="episodes", foreign_keys=[test_identity_id]
    )
    attribution: Mapped[Attribution | None] = relationship(
        back_populates="episode", uselist=False, cascade="all, delete-orphan"
    )
    classifications: Mapped[list[Classification]] = relationship(
        back_populates="episode", cascade="all, delete-orphan"
    )
