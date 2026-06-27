"""Human input + provenance per failure episode (Information model: 'Human input').

The causing person + reason are entered/confirmed by a human; each conclusion carries *how it was
reached* (provenance tier) because the KB (§4) weights entries by validation, not just text. When
the AI was corrected, the **original AI value** is retained alongside the correction (the strongest
learning signal). ``actor`` columns are plain strings (see lifecycle.py).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uta.db import Base
from uta.models.enums import Provenance
from uta.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from uta.models.kb import FailureSignature
    from uta.models.lifecycle import FailureEpisode


class Attribution(Base, TimestampMixin):
    __tablename__ = "attributions"

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("failure_episodes.id"), unique=True, index=True
    )

    # Human conclusions (entered by the person in charge; may differ from the predicted cause).
    causing_person: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Provenance tier per conclusion (they can differ for cause vs reason).
    cause_provenance: Mapped[str] = mapped_column(String(16), default=Provenance.AI_UNCONFIRMED)
    reason_provenance: Mapped[str] = mapped_column(String(16), default=Provenance.AI_UNCONFIRMED)
    # Retained when a human overrode the AI (the most informative case).
    original_ai_cause: Mapped[str | None] = mapped_column(String(128), nullable=True)
    original_ai_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Who validated (confirmed/corrected) and entered, + when — stamped from the acting user.
    validated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entered_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # KB hook: confirmed/entered reasons attach to a signature for recurrence retrieval (§4).
    signature_id: Mapped[int | None] = mapped_column(
        ForeignKey("failure_signatures.id"), nullable=True, index=True
    )

    episode: Mapped[FailureEpisode] = relationship(back_populates="attribution")
    signature: Mapped[FailureSignature | None] = relationship(back_populates="attributions")
