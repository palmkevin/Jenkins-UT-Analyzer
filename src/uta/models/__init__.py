"""Minimal Slice-0 schema: a run and its per-(test, track) results.

This is intentionally small — enough to persist one ingested run and render it. The full
Information model (lifecycle, episodes, signals, KB signatures, …) arrives in Milestone 1 behind
Alembic migrations.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uta.db import Base


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    build_number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32))
    url: Mapped[str] = mapped_column(String(512), default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    complete: Mapped[bool] = mapped_column(default=False)

    results: Mapped[list[TestResult]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class TestResult(Base):
    __test__ = False  # not a pytest test class despite the Test* name
    __tablename__ = "test_results"
    __table_args__ = (UniqueConstraint("run_id", "test_id", "track", name="uq_run_test_track"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    test_id: Mapped[str] = mapped_column(String(512), index=True)  # class_name.name
    track: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner_initials: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped[Run] = relationship(back_populates="results")


__all__ = ["Run", "TestResult"]
