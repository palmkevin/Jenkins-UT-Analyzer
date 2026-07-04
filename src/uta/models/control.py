"""Operational state for the in-app control panel (issue #16).

Three small tables, all **operational** (not part of the failure Information model) — they let the
monitor tune and drive the engine from the dashboard instead of editing env + redeploying:

- :class:`SettingOverride` — a runtime override for one whitelisted tunable threshold. The row's
  presence means "use this instead of the env default"; deleting it reverts to the default. Only
  the whitelisted keys (see :mod:`uta.control.tunables`) are ever written here — secrets and URLs
  are never overridable.
- :class:`IngestJob` — one on-demand ingest / re-analysis request over a build range, with its live
  status (queued → running → done/error) and progress so the UI can poll it.
- :class:`PollerHeartbeat` — a **singleton** (``id == 1``) row the scheduled poller stamps every
  tick, surfacing last-poll time and the last error to the dashboard.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from uta.db import Base
from uta.models.enums import IngestJobStatus
from uta.models.mixins import TimestampMixin


class SettingOverride(Base, TimestampMixin):
    """A runtime override for one whitelisted tunable, keyed by its settings attribute name.

    ``value`` is stored as text and coerced/validated by the tunable registry on both read and
    write, so the DB stays schema-portable (Postgres + SQLite) and the type/bounds live in one
    place. ``updated_by`` records the acting user (Phase-1 self-declared string, like every other
    human action).
    """

    __tablename__ = "setting_overrides"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255))
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)


class IngestJob(Base, TimestampMixin):
    """An on-demand ingest / re-analysis of a build (or ``build_start..build_end`` range).

    Runs with **back-fill semantics** — no email, no LLM — so a re-ingest never re-mails historical
    regressions or re-spends on hypotheses. ``builds_done`` advances as each build completes so the
    UI can render running → done progress; ``error`` holds the failure detail when ``status`` is
    ``ERROR``.
    """

    __tablename__ = "ingest_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    build_start: Mapped[int] = mapped_column(Integer)
    build_end: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default=IngestJobStatus.QUEUED)
    builds_total: Mapped[int] = mapped_column(Integer, default=0)
    builds_done: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PollerHeartbeat(Base, TimestampMixin):
    """Singleton (``id == 1``) heartbeat the scheduled poller stamps each tick.

    Surfaces poller health to the dashboard: when it last ran, how many builds the last tick
    ingested, and the last error (with its time) if a tick failed. The high-water mark is *not*
    stored here — it is derived from the max ingested build (``highest_ingested_build``), so there
    is no second copy to drift.
    """

    __tablename__ = "poller_heartbeats"

    id: Mapped[int] = mapped_column(primary_key=True)
    last_poll_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_processed_count: Mapped[int] = mapped_column(Integer, default=0)
    last_processed: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
