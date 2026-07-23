"""Builds and their per-shard timing (Information model: 'Builds')."""

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


class Build(Base, TimestampMixin):
    __tablename__ = "builds"

    id: Mapped[int] = mapped_column(primary_key=True)
    build_number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32))
    url: Mapped[str] = mapped_column(String(512), default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Completeness: finished + all expected shards reported. Incomplete builds are stored
    # and shown but skipped when picking a baseline.
    complete: Mapped[bool] = mapped_column(Boolean, default=False)
    # Which complete build this build was diffed against (set by the baseline selector, M2).
    baseline_build_id: Mapped[int | None] = mapped_column(ForeignKey("builds.id"), nullable=True)

    total_passed: Mapped[int] = mapped_column(Integer, default=0)
    total_failed: Mapped[int] = mapped_column(Integer, default=0)
    total_skipped: Mapped[int] = mapped_column(Integer, default=0)

    shards: Mapped[list[BuildShard]] = relationship(
        back_populates="build", cascade="all, delete-orphan"
    )
    results: Mapped[list[TestResult]] = relationship(
        back_populates="build", cascade="all, delete-orphan"
    )
    code_changes: Mapped[list[CodeChangeCandidate]] = relationship(
        back_populates="build", cascade="all, delete-orphan"
    )
    data_changes: Mapped[list[DataChangeCandidate]] = relationship(
        back_populates="build", cascade="all, delete-orphan"
    )
    baseline_build: Mapped[Build | None] = relationship(remote_side=[id])


class BuildShard(Base):
    """Per-shard (track) timing & status from ``wfapi`` — drives completeness + the build
    summary."""

    __tablename__ = "build_shards"
    __table_args__ = (UniqueConstraint("build_id", "track", name="uq_build_shard_track"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    build_id: Mapped[int] = mapped_column(ForeignKey("builds.id"), index=True)
    track: Mapped[str] = mapped_column(String(32))  # permanent / permanent_py39
    status: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    build: Mapped[Build] = relationship(back_populates="shards")
