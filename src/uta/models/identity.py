"""Test identity & aliases (Information model: 'Test identity & aliases').

Test-level identity (one per ``suite/class/method``); the track is an attribute on the *result*,
never a separate identity. Renames/moves are handled by an ``alias_of`` self-pointer so lifecycle
and flakiness history survive — manual merge ships v1, automatic alias *suggestion* is post-v1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uta.db import Base
from uta.models.enums import AliasState
from uta.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from uta.models.lifecycle import FailureEpisode, TestLifecycle
    from uta.models.result import TestResult


class TestIdentity(Base, TimestampMixin):
    __test__ = False  # not a pytest test class despite the Test* name
    __tablename__ = "test_identities"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Canonical fully-qualified name == className.name (the v1 ingest key).
    canonical_name: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    suite: Mapped[str | None] = mapped_column(String(255), nullable=True)
    class_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    method: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Identity stability: history/flakiness queries follow this pointer when set & confirmed.
    alias_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("test_identities.id"), nullable=True, index=True
    )
    alias_state: Mapped[str] = mapped_column(String(16), default=AliasState.NONE)

    # Ownership fallback contact (ZEPHYR initials / SVN blame), resolved at identity level.
    owner_initials: Mapped[str | None] = mapped_column(String(32), nullable=True)

    alias_of: Mapped[TestIdentity | None] = relationship(remote_side=[id])
    results: Mapped[list[TestResult]] = relationship(back_populates="identity")
    lifecycle: Mapped[TestLifecycle | None] = relationship(
        back_populates="identity", uselist=False, cascade="all, delete-orphan"
    )
    episodes: Mapped[list[FailureEpisode]] = relationship(
        back_populates="identity", cascade="all, delete-orphan"
    )
