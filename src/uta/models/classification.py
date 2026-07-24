"""Predicted cause / LLM hypothesis per episode (Information model: 'Classifications').

Deterministic prediction (CODE/DATA/INFRA/UNKNOWN) from time-windowed candidates (M2). The
**confidence** number is derived deterministically at classification time (issue #73) from the
relevance-score gap between the winning and losing candidate kinds plus the KB provenance weight of
the failure's signature — see :mod:`uta.analyze.classify`. The column stays nullable: rows
classified before the formula existed keep ``NULL``. Rows are append-only for auditability; the
latest by ``created_at`` is the current prediction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uta.db import Base
from uta.models.enums import PredictedCause
from uta.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from uta.models.incident import BuildIncident
    from uta.models.lifecycle import FailureEpisode


class Classification(Base, TimestampMixin):
    __tablename__ = "classifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    # A classification belongs to EITHER a test-level episode OR a build-level incident (issue #171)
    # — exactly one of the two FKs is set. Both stay nullable so the same append-only, provenance-
    # weighted prediction/hypothesis machinery serves both surfaces.
    episode_id: Mapped[int | None] = mapped_column(
        ForeignKey("failure_episodes.id"), nullable=True, index=True
    )
    incident_id: Mapped[int | None] = mapped_column(
        ForeignKey("build_incidents.id"), nullable=True, index=True
    )

    predicted_cause: Mapped[str] = mapped_column(String(16), default=PredictedCause.UNKNOWN)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # null pre-#73 rows
    suggested_contact: Mapped[str | None] = mapped_column(String(128), nullable=True)
    llm_hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON of the signals behind it

    episode: Mapped[FailureEpisode | None] = relationship(back_populates="classifications")
    incident: Mapped[BuildIncident | None] = relationship(back_populates="classifications")
