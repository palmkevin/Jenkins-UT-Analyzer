"""Write-side dashboard actions (PLAN §1): acknowledge, confirm, attribute.

Every action is stamped with the acting user (Phase-1 self-declared string, §"Users & identity").
Conclusions carry **provenance** — *how* they were reached — because the KB (§4) weights entries by
validation, not text:

- **Confirm** an AI suggestion → ``AI_CONFIRMED`` (strong positive signal).
- **Correct** an AI suggestion → ``HUMAN_CORRECTED`` + the original AI value retained (strongest).
- Enter with no AI suggestion in play → ``HUMAN_ENTERED`` (ground truth).

These are pure DB mutations on persisted facts; the route handlers commit via ``session_scope``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from uta.models import (
    Attribution,
    Classification,
    FailureEpisode,
    Run,
    TestLifecycle,
    TestResult,
)
from uta.models.enums import Provenance


def _now() -> datetime:
    return datetime.now(UTC)


def _episode_signature_id(session: Session, episode: FailureEpisode) -> int | None:
    """The failure signature for an episode — the latest failing result of its test that has one.

    Links the human conclusion to the KB signature so confirmed/entered reasons feed recurrence
    retrieval (§4): a future failure with the same signature surfaces "previous reason was …".
    """
    return session.scalar(
        select(TestResult.signature_id)
        .join(Run, Run.id == TestResult.run_id)
        .where(
            TestResult.test_identity_id == episode.test_identity_id,
            TestResult.signature_id.isnot(None),
        )
        .order_by(Run.started_at.desc(), TestResult.id.desc())
        .limit(1)
    )


def _latest_classification(session: Session, episode_id: int) -> Classification | None:
    return session.scalar(
        select(Classification)
        .where(Classification.episode_id == episode_id)
        .order_by(Classification.created_at.desc(), Classification.id.desc())
        .limit(1)
    )


def _get_or_create_attribution(session: Session, episode_id: int) -> Attribution:
    attr = session.scalar(select(Attribution).where(Attribution.episode_id == episode_id))
    if attr is None:
        attr = Attribution(episode_id=episode_id)
        session.add(attr)
    return attr


def acknowledge(session: Session, identity_id: int, actor: str) -> bool:
    """Acknowledge a test's current failure — moves it from the New to the Still-failing bucket.

    Stamps the acting user. Returns False if the test has no lifecycle row (never failed).
    """
    lc = session.scalar(select(TestLifecycle).where(TestLifecycle.test_identity_id == identity_id))
    if lc is None:
        return False
    lc.acknowledged = True
    lc.acknowledged_by = actor
    lc.acknowledged_at = _now()
    return True


def _provenance(submitted: str, ai_value: str | None) -> str:
    """How a human conclusion was reached relative to the AI's suggestion for the same field."""
    if ai_value is not None and submitted.strip() == ai_value.strip():
        return Provenance.AI_CONFIRMED
    if ai_value is not None:
        return Provenance.HUMAN_CORRECTED
    return Provenance.HUMAN_ENTERED


def confirm(session: Session, episode_id: int, actor: str) -> Attribution | None:
    """One-click **Confirm** of the AI suggestion for an episode (cheap → high label volume).

    Accepts the AI's suggested contact + hypothesis as the conclusion, tier ``AI_CONFIRMED``,
    retaining the original AI values for audit. Returns None if the episode doesn't exist.
    """
    episode = session.get(FailureEpisode, episode_id)
    if episode is None:
        return None
    classification = _latest_classification(session, episode_id)
    ai_cause = classification.suggested_contact if classification else None
    ai_reason = classification.llm_hypothesis if classification else None

    attr = _get_or_create_attribution(session, episode_id)
    attr.causing_person = ai_cause
    attr.reason_text = ai_reason
    attr.cause_provenance = Provenance.AI_CONFIRMED
    attr.reason_provenance = Provenance.AI_CONFIRMED
    attr.original_ai_cause = ai_cause
    attr.original_ai_reason = ai_reason
    attr.validated_by = actor
    attr.validated_at = _now()
    attr.signature_id = _episode_signature_id(session, episode)
    return attr


def set_attribution(
    session: Session,
    episode_id: int,
    actor: str,
    *,
    causing_person: str | None = None,
    reason_text: str | None = None,
    triage_status: str | None = None,
    jira_ticket: str | None = None,
) -> Attribution | None:
    """Human edit of cause/reason/triage/Jira-ticket, deriving provenance from the AI suggestion.

    Only non-empty submitted ``causing_person``/``reason_text`` are written (so a partial form
    never clears the others). ``triage_status`` is set on the episode. ``jira_ticket`` is also set
    directly on the episode — a submitted value is trimmed and stored, an empty submission clears it
    (so the ticket is editable both ways); it is not a provenance-tracked conclusion, so it does not
    touch the Attribution row. Returns None if the episode doesn't exist.
    """
    episode = session.get(FailureEpisode, episode_id)
    if episode is None:
        return None
    classification = _latest_classification(session, episode_id)
    ai_cause = classification.suggested_contact if classification else None
    ai_reason = classification.llm_hypothesis if classification else None

    attr = _get_or_create_attribution(session, episode_id)
    touched = False

    if causing_person and causing_person.strip():
        value = causing_person.strip()
        provenance = _provenance(value, ai_cause)
        attr.causing_person = value
        attr.cause_provenance = provenance
        if provenance == Provenance.HUMAN_CORRECTED:
            attr.original_ai_cause = ai_cause
        touched = True

    if reason_text and reason_text.strip():
        value = reason_text.strip()
        provenance = _provenance(value, ai_reason)
        attr.reason_text = value
        attr.reason_provenance = provenance
        if provenance == Provenance.HUMAN_CORRECTED:
            attr.original_ai_reason = ai_reason
        touched = True

    if triage_status:
        episode.triage_status = triage_status

    if jira_ticket is not None:
        episode.jira_ticket = jira_ticket.strip() or None

    if touched:
        attr.entered_by = actor
        attr.validated_by = actor
        attr.validated_at = _now()
        attr.signature_id = _episode_signature_id(session, episode)
    return attr
