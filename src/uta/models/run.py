"""Runs and their per-shard timing (Information model: 'Runs')."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uta.db import Base
from uta.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from uta.models.result import TestResult
    from uta.models.signals import CodeChangeCandidate, DataChangeCandidate


class Run(Base, TimestampMixin):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    build_number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32))
    url: Mapped[str] = mapped_column(String(512), default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Completeness (PLAN §2): finished + all expected shards reported. Incomplete runs are stored
    # and shown but skipped when picking a baseline.
    complete: Mapped[bool] = mapped_column(Boolean, default=False)
    # Which complete run this run was diffed against (set by the baseline selector, M2).
    baseline_run_id: Mapped[int | None] = mapped_column(ForeignKey("runs.id"), nullable=True)

    total_passed: Mapped[int] = mapped_column(Integer, default=0)
    total_failed: Mapped[int] = mapped_column(Integer, default=0)
    total_skipped: Mapped[int] = mapped_column(Integer, default=0)

    shards: Mapped[list[RunShard]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    results: Mapped[list[TestResult]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    code_changes: Mapped[list[CodeChangeCandidate]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    data_changes: Mapped[list[DataChangeCandidate]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    baseline_run: Mapped[Run | None] = relationship(remote_side=[id])


class RunShard(Base):
    """Per-shard (track) timing & status from ``wfapi`` — drives completeness + the §2 summary."""

    __tablename__ = "run_shards"
    __table_args__ = (UniqueConstraint("run_id", "track", name="uq_run_shard_track"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    track: Mapped[str] = mapped_column(String(32))  # permanent / permanent_py39
    status: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run: Mapped[Run] = relationship(back_populates="shards")
