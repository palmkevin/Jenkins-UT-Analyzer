"""Predicted cause / LLM hypothesis per episode (Information model: 'Classifications').

Deterministic prediction (CODE/DATA/INFRA/UNKNOWN) from time-windowed candidates (M2). A
**confidence** number is deferred per design — there is no KB to rank against on day one — so the
column is nullable and stays null in v1. Rows are append-only for auditability; the latest by
``created_at`` is the current prediction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uta.db import Base
from uta.models.enums import PredictedCause
from uta.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from uta.models.lifecycle import FailureEpisode


class Classification(Base, TimestampMixin):
    __tablename__ = "classifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("failure_episodes.id"), index=True)

    predicted_cause: Mapped[str] = mapped_column(String(16), default=PredictedCause.UNKNOWN)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # deferred (v1: null)
    suggested_contact: Mapped[str | None] = mapped_column(String(128), nullable=True)
    llm_hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON of the signals behind it

    episode: Mapped[FailureEpisode] = relationship(back_populates="classifications")
