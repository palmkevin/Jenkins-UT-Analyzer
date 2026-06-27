"""Knowledge-base failure signatures (Information model: 'Knowledge base').

A signature = **test identity + normalized error text**. We store the normalized text and its
**hash** for instant exact-recurrence lookup, plus a ``pg_trgm`` GIN index on the normalized text
for fuzzy "similar past cases" (§4) — all in stock Postgres, no vector store. The raw error text is
**not** stored here (medical-data invariant); only the normalized/redacted form.

The GIN+``gin_trgm_ops`` index is Postgres-only; on SQLite (offline tests) the dialect kwargs are
ignored and it degrades to a plain index, which is fine for the logic those tests cover.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uta.db import Base
from uta.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from uta.models.attribution import Attribution
    from uta.models.identity import TestIdentity
    from uta.models.result import TestResult


class FailureSignature(Base, TimestampMixin):
    __tablename__ = "failure_signatures"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_identity_id: Mapped[int] = mapped_column(ForeignKey("test_identities.id"), index=True)
    normalized_text: Mapped[str] = mapped_column(Text)
    # sha256 over (identity + normalized_text); exact recurrence is an index-backed equality lookup.
    signature_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    exception_type: Mapped[str | None] = mapped_column(String(255), nullable=True)

    first_seen_run_id: Mapped[int | None] = mapped_column(ForeignKey("runs.id"), nullable=True)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_run_id: Mapped[int | None] = mapped_column(ForeignKey("runs.id"), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)

    identity: Mapped[TestIdentity] = relationship()
    results: Mapped[list[TestResult]] = relationship(back_populates="signature")
    attributions: Mapped[list[Attribution]] = relationship(back_populates="signature")


# Fuzzy "similar past cases" — trigram GIN over the normalized text (PLAN §4). Postgres-only ops;
# degrades to a plain index on SQLite.
Index(
    "ix_failure_signatures_normalized_text_trgm",
    FailureSignature.normalized_text,
    postgresql_using="gin",
    postgresql_ops={"normalized_text": "gin_trgm_ops"},
)
