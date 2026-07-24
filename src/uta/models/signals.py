"""Candidate change signals (Information model: 'Signals').

Storage is **build-windowed**: candidates are the SVN-update revisions and ``ut_ref`` ``V_TRACKING``
changes that fall inside the build's time window, so they link to the **build**, not a failure. The
per-test view is computed, not stored: :mod:`uta.analyze.relevance` (issue #50) scores this shared
list against each failing test at read/analysis time.

Medical-data invariant: ``MODDATA`` (which may carry patient data) is **never** selected or stored
— only the entity key, change type, author and timestamp.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uta.db import Base
from uta.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from uta.models.build import Build


class CodeChangeCandidate(Base, TimestampMixin):
    """An SVN-update revision in the build's window (a candidate code change)."""

    __tablename__ = "code_change_candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    build_id: Mapped[int] = mapped_column(ForeignKey("builds.id"), index=True)

    commit_id: Mapped[str] = mapped_column(String(64), index=True)
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # UTC
    paths: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON [{editType, file}]

    build: Mapped[Build] = relationship(back_populates="code_changes")


class DataChangeCandidate(Base, TimestampMixin):
    """A candidate ``ut_ref`` ``V_TRACKING`` data change in the build's correlation window.

    The window runs from the previous build's start through this build's end (ADR-0004), so the
    change is attributed to the first build that ran after it.
    """

    __tablename__ = "data_change_candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    build_id: Mapped[int] = mapped_column(ForeignKey("builds.id"), index=True)

    lx_table_code: Mapped[str] = mapped_column(String(64), index=True)  # changed entity table
    pk_lst: Mapped[str | None] = mapped_column(String(255), nullable=True)  # entity key
    change_type: Mapped[str] = mapped_column(String(1))  # normalized C / U / D
    component_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    author: Mapped[str | None] = mapped_column(String(64), nullable=True)  # resolved USRCODE
    session_log_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # CREDATIM normalized from Europe/Luxembourg-local to UTC (never a fixed +2).
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    build: Mapped[Build] = relationship(back_populates="data_changes")
