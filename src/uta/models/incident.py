"""Build Incidents (Information model: 'Build incidents').

A **Build Incident** is a *build-level* condition requiring human triage — the pipeline itself
failing (``result == FAILURE``) or being aborted (``result == ABORTED``) — as opposed to a
test-level :class:`~uta.models.lifecycle.FailureEpisode`. The two are orthogonal: one build can
produce both a Build Incident *and* test episodes, and they never merge.

Streak model (mirrors how episodes collapse consecutive test failures): consecutive non-green
builds collapse into **one** incident. The ``kind`` is whatever opened the streak; mixed kinds
within one streak stay one incident (the others are noted in ``mixed_kinds``). The incident
**recovers** on the next build reaching ``SUCCESS`` or ``UNSTABLE`` — independent of the
EXPECTED_TRACKS completeness check — recording the recovered-in build; ``recovered_build_id`` is
null while open. A later non-green build after a recovery opens a *new* incident and bumps
``reopen_count`` (the flap counter), exactly like an episode reopen.

The triage/documentation surface is **generalized** with test episodes (issue #171): ``assignee``
(the person handling the fix — distinct from the causing person in the reused
:class:`~uta.models.attribution.Attribution`), ``cause_ticket`` (the ticket describing the cause)
and ``resolution_ticket`` (the ticket the assignee is working on to resolve it — *not* a claim that
it is resolved). ``actor`` columns are plain strings (Phase-1 self-declared), like everywhere else.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uta.db import Base
from uta.models.enums import IncidentKind, TriageStatus
from uta.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from uta.models.attribution import Attribution
    from uta.models.classification import Classification
    from uta.models.kb import FailureSignature


class BuildIncident(Base, TimestampMixin):
    """One streak of consecutive non-green builds requiring build-level triage."""

    __tablename__ = "build_incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), default=IncidentKind.PIPELINE_FAILURE, index=True)

    # The build that opened the streak, the most recent non-green build in it, and — once green
    # again — the build that recovered it (null while open).
    opened_build_id: Mapped[int] = mapped_column(ForeignKey("builds.id"), index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_build_id: Mapped[int | None] = mapped_column(ForeignKey("builds.id"), nullable=True)
    last_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recovered_build_id: Mapped[int | None] = mapped_column(ForeignKey("builds.id"), nullable=True)
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_open: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    # Flap counter — how many times a streak reopened after a recovery (like an episode reopen).
    reopen_count: Mapped[int] = mapped_column(Integer, default=0)
    # How many non-green builds this streak spans (bumped as it extends).
    build_count: Mapped[int] = mapped_column(Integer, default=1)
    # Other kinds seen within the same streak (comma-joined), when a mixed streak occurs — the kind
    # column stays whatever opened it.
    mixed_kinds: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # The failing stage that characterises the incident (the signature's text is drawn from its log
    # for a pipeline_failure); None for an aborted incident.
    failing_stage: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Triage / documentation (generalized with test episodes, issue #171) ──────────────────────
    triage_status: Mapped[str] = mapped_column(String(16), default=TriageStatus.UNTRIAGED)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # The person handling the fix (distinct from the causing person in the Attribution).
    assignee: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # The ticket describing the cause of the incident.
    cause_ticket: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # The ticket the assignee is working on to resolve this (NOT a claim that it is resolved).
    resolution_ticket: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Free-text human documentation: the problem statement (pipeline_failure) or the aborted reason.
    problem_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Incident-namespaced failure signature (pipeline_failure only; never for aborted).
    signature_id: Mapped[int | None] = mapped_column(
        ForeignKey("failure_signatures.id"), nullable=True, index=True
    )

    signature: Mapped[FailureSignature | None] = relationship()
    classifications: Mapped[list[Classification]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )
    attribution: Mapped[Attribution | None] = relationship(
        back_populates="incident", uselist=False, cascade="all, delete-orphan"
    )
