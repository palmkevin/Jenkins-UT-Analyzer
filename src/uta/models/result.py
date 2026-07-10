"""Per-run test results (Information model: 'Test results per run').

Keyed by ``(run, test_identity, track)`` — the same test runs in both tracks. Across runs these
rows ARE the failure-history feed (counts, last-failed, fail-rate windows); no separate
table is needed, hence the ``(test_identity_id, status)`` and ``run_id`` indexes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uta.db import Base
from uta.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from uta.models.identity import TestIdentity
    from uta.models.kb import FailureSignature
    from uta.models.run import Run


class TestResult(Base, TimestampMixin):
    __test__ = False  # not a pytest test class despite the Test* name
    __tablename__ = "test_results"
    __table_args__ = (
        UniqueConstraint("run_id", "test_identity_id", "track", name="uq_run_test_track"),
        # Composite index for the flaky `_sequence` and lifecycle age queries, which scan a
        # single identity's results across runs — (test_identity_id, run_id) covers both.
        Index("ix_test_results_identity_run", "test_identity_id", "run_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    test_identity_id: Mapped[int] = mapped_column(ForeignKey("test_identities.id"), index=True)
    track: Mapped[str] = mapped_column(String(32))  # permanent / permanent_py39
    status: Mapped[str] = mapped_column(String(32), index=True)  # PASSED/FAILED/REGRESSION/...
    duration: Mapped[float] = mapped_column(Float, default=0.0)

    # Per-run signals carried from the report/stack trace.
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # ZEPHYR test-case owner initials for this run (per-run provenance of the identity-level value);
    # ZEPHYR metadata, not the test's developer — see TestIdentity.zephyr_owner / main_developer.
    zephyr_owner: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # derived (M2)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)

    # KB link: the normalized failure signature for this result (set when failing).
    signature_id: Mapped[int | None] = mapped_column(
        ForeignKey("failure_signatures.id"), nullable=True, index=True
    )

    run: Mapped[Run] = relationship(back_populates="results")
    identity: Mapped[TestIdentity] = relationship(back_populates="results")
    signature: Mapped[FailureSignature | None] = relationship(back_populates="results")
