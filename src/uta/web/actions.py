"""Write-side dashboard actions: acknowledge, confirm, attribute.

Every action is stamped with the acting user (Phase-1 self-declared string).
Conclusions carry **provenance** — *how* they were reached — because the KB weights entries by
validation, not text:

- **Confirm** an AI suggestion → ``AI_CONFIRMED`` (strong positive signal).
- **Correct** an AI suggestion → ``HUMAN_CORRECTED`` + the original AI value retained (strongest).
- Enter with no AI suggestion in play → ``HUMAN_ENTERED`` (ground truth).

These are pure DB mutations on persisted facts; the route handlers commit via ``session_scope``.
"""

from __future__ import annotations

from collections.abc import Collection
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from uta.models import (
    Attribution,
    Build,
    BuildIncident,
    Classification,
    FailureEpisode,
    FailureSignature,
    TestLifecycle,
    TestResult,
)
from uta.models.enums import LifecycleState, Provenance


def _now() -> datetime:
    return datetime.now(UTC)


def _episode_signature_id(session: Session, episode: FailureEpisode) -> int | None:
    """The failure signature for an episode — the latest failing result of its test that has one.

    Links the human conclusion to the KB signature so confirmed/entered reasons feed recurrence
    retrieval: a future failure with the same signature surfaces "previous reason was …".
    """
    return session.scalar(
        select(TestResult.signature_id)
        .join(Build, Build.id == TestResult.build_id)
        .where(
            TestResult.test_identity_id == episode.test_identity_id,
            TestResult.signature_id.isnot(None),
        )
        .order_by(Build.started_at.desc(), TestResult.id.desc())
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


def bulk_acknowledge(session: Session, identity_ids: Collection[int], actor: str) -> int:
    """Acknowledge many tests' current failure in one action (issue #63's checkbox bulk-ack).

    Silently skips ids with no lifecycle row. Returns the number actually acknowledged.
    """
    if not identity_ids:
        return 0
    now = _now()
    count = 0
    for lc in session.scalars(
        select(TestLifecycle).where(TestLifecycle.test_identity_id.in_(identity_ids))
    ):
        lc.acknowledged = True
        lc.acknowledged_by = actor
        lc.acknowledged_at = now
        count += 1
    return count


def _error_key(normalized_text: str) -> str:
    """The exception type + masked message portion of a normalized signature, stack frames
    stripped out.

    A :class:`FailureSignature` is ``test identity + normalized text`` (:mod:`uta.kb.signature`),
    and the text's stack-frame lines always name *that test's own* function
    (``"<path>:<LINE> in <func>"``) — so two different tests hitting the exact same underlying
    error still get two distinct signature rows with distinct ``normalized_text``. Stripping the
    frame lines leaves just the exception type + message, which *is* comparable across tests —
    the actual "one root cause, many tests" grouping key the bulk action needs.
    """
    return "\n".join(line for line in normalized_text.splitlines() if ":<LINE> in " not in line)


def open_episodes_for_signature(
    session: Session, signature_id: int, *, unacknowledged_only: bool = False
) -> list[tuple[TestLifecycle, FailureEpisode]]:
    """Every **failing** test's current open episode sharing ``signature_id``'s error text.

    The episode-targeting core of the signature-wide bulk actions (acknowledge #63, attribute
    #106): a candidate matches when its current failure has the same exception type + message
    (see :func:`_error_key`) as the source signature. Returns ``[]`` if the signature is unknown.
    The candidate set (failing tests) is small, so this is a handful of queries, not a scan of
    the whole store.
    """
    source = session.get(FailureSignature, signature_id)
    if source is None:
        return []
    key = _error_key(source.normalized_text)

    criteria = [TestLifecycle.state == LifecycleState.FAILING]
    if unacknowledged_only:
        criteria.append(TestLifecycle.acknowledged.is_(False))
    matches: list[tuple[TestLifecycle, FailureEpisode]] = []
    for lc in session.scalars(select(TestLifecycle).where(*criteria)).all():
        ep = lc.current_episode
        if ep is None:
            continue
        candidate_sig_id = _episode_signature_id(session, ep)
        if candidate_sig_id is None:
            continue
        candidate_sig = session.get(FailureSignature, candidate_sig_id)
        if candidate_sig is None or _error_key(candidate_sig.normalized_text) != key:
            continue
        matches.append((lc, ep))
    return matches


def acknowledge_by_signature(session: Session, signature_id: int, actor: str) -> int:
    """Acknowledge every unacknowledged **failing** test sharing ``signature_id``'s error text.

    The high-leverage bulk action for the one-cause-many-tests case (issue #63): one click on a
    New-bucket row clears every other New test whose current failure has the same exception
    type + message (see :func:`open_episodes_for_signature`) — one outage, many tests, one click.
    Returns 0 if the signature is unknown.
    """
    now = _now()
    count = 0
    for lc, _ep in open_episodes_for_signature(session, signature_id, unacknowledged_only=True):
        lc.acknowledged = True
        lc.acknowledged_by = actor
        lc.acknowledged_at = now
        count += 1
    return count


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
    cause_ticket: str | None = None,
    resolution_ticket: str | None = None,
    assignee: str | None = None,
) -> Attribution | None:
    """Human edit of cause/reason/triage + documentation fields, deriving provenance from the AI.

    Only non-empty submitted ``causing_person``/``reason_text`` are written (so a partial form
    never clears the others). ``triage_status`` is set on the episode. The documentation fields —
    ``cause_ticket`` (the ticket describing the cause, formerly the single "Jira ticket"),
    ``resolution_ticket`` (the ticket the ``assignee`` is working on to resolve it) and ``assignee``
    (the person handling the fix, distinct from the causing person) — are set directly on the
    episode: a submitted value is trimmed and stored, an empty submission clears it; ``None`` leaves
    the field untouched. They are not provenance-tracked conclusions. Returns None if the episode
    doesn't exist.
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

    if cause_ticket is not None:
        episode.cause_ticket = cause_ticket.strip() or None
    if resolution_ticket is not None:
        episode.resolution_ticket = resolution_ticket.strip() or None
    if assignee is not None:
        episode.assignee = assignee.strip() or None

    if touched:
        attr.entered_by = actor
        attr.validated_by = actor
        attr.validated_at = _now()
        attr.signature_id = _episode_signature_id(session, episode)
    return attr


def has_attribution_input(
    causing_person: str | None, reason_text: str | None, triage_status: str | None
) -> bool:
    """Whether a submitted cause/reason/triage-status trio would actually write anything.

    Mirrors :func:`set_attribution`'s write conditions (whitespace-only fields are ignored there),
    so callers can tell an all-blank submission from a real edit — the bulk route flashes "nothing
    to apply" instead of claiming an update count that never happened (issue #150).
    """
    return bool(
        (causing_person and causing_person.strip())
        or (reason_text and reason_text.strip())
        or triage_status
    )


def bulk_set_attribution(
    session: Session,
    episode_ids: Collection[int],
    actor: str,
    *,
    causing_person: str | None = None,
    reason_text: str | None = None,
    triage_status: str | None = None,
) -> int:
    """Apply the same cause/reason/triage-status edit to many episodes at once (issue #63).

    Each episode gets the ordinary :func:`set_attribution` treatment (so provenance is still
    derived per-episode against *that* episode's AI suggestion) — this just loops the checkbox
    selection from the Still-failing bucket. Returns the number of episodes actually modified:
    the ones that existed among ``episode_ids``, or 0 straight away when the submitted fields are
    all blank (:func:`has_attribution_input`) — :func:`set_attribution` would write nothing to any
    of them, and the flash count must not claim updates that never happened (issue #150).
    """
    if not has_attribution_input(causing_person, reason_text, triage_status):
        return 0
    count = 0
    for episode_id in episode_ids:
        attr = set_attribution(
            session,
            episode_id,
            actor,
            causing_person=causing_person,
            reason_text=reason_text,
            triage_status=triage_status,
        )
        if attr is not None:
            count += 1
    return count


def attribute_by_signature(
    session: Session,
    signature_id: int,
    actor: str,
    *,
    causing_person: str | None = None,
    reason_text: str | None = None,
    triage_status: str | None = None,
    cause_ticket: str | None = None,
    resolution_ticket: str | None = None,
    assignee: str | None = None,
) -> int:
    """Apply one root-cause conclusion to every open failing episode sharing a signature (#106).

    The attribution twin of :func:`acknowledge_by_signature` — same episode targeting
    (:func:`open_episodes_for_signature`), but instead of acknowledging, each matching test's
    current open episode gets the ordinary :func:`set_attribution` treatment. Provenance is still
    derived **per episode** against that episode's own AI suggestion (a mixed set yields a mix of
    ``HUMAN_CORRECTED`` / ``HUMAN_ENTERED``), and each conclusion attaches to that episode's own
    signature row for KB recurrence retrieval. One deviation from the single-episode form: an
    empty ticket / assignee field leaves those **untouched** rather than clearing them —
    mass-clearing unrelated documentation from a shared-outage form would be a foot-gun. Returns the
    number of episodes attributed (0 if the signature is unknown or nothing matches).
    """
    ct = cause_ticket.strip() if cause_ticket and cause_ticket.strip() else None
    rt = resolution_ticket.strip() if resolution_ticket and resolution_ticket.strip() else None
    asg = assignee.strip() if assignee and assignee.strip() else None
    count = 0
    for _lc, ep in open_episodes_for_signature(session, signature_id):
        set_attribution(
            session,
            ep.id,
            actor,
            causing_person=causing_person,
            reason_text=reason_text,
            triage_status=triage_status,
            cause_ticket=ct,
            resolution_ticket=rt,
            assignee=asg,
        )
        count += 1
    return count


# ── Build Incident actions (issue #171) ──────────────────────────────────────────────────────────
# The build-level twins of the episode actions above: they reuse the same Attribution /
# Classification rows (now nullable-keyed on incident_id) and the same confirm/correct provenance
# loop, so a build-level triage carries identical audit semantics to a test-level one.


def _latest_incident_classification(session: Session, incident_id: int) -> Classification | None:
    return session.scalar(
        select(Classification)
        .where(Classification.incident_id == incident_id)
        .order_by(Classification.created_at.desc(), Classification.id.desc())
        .limit(1)
    )


def _get_or_create_incident_attribution(session: Session, incident_id: int) -> Attribution:
    attr = session.scalar(select(Attribution).where(Attribution.incident_id == incident_id))
    if attr is None:
        attr = Attribution(incident_id=incident_id)
        session.add(attr)
    return attr


def acknowledge_incident(session: Session, incident_id: int, actor: str) -> bool:
    """Acknowledge a Build Incident. Returns False if the incident doesn't exist."""
    incident = session.get(BuildIncident, incident_id)
    if incident is None:
        return False
    incident.acknowledged = True
    incident.acknowledged_by = actor
    incident.acknowledged_at = _now()
    return True


def confirm_incident(session: Session, incident_id: int, actor: str) -> Attribution | None:
    """One-click **Confirm** of the AI suggestion for a Build Incident (tier ``AI_CONFIRMED``)."""
    incident = session.get(BuildIncident, incident_id)
    if incident is None:
        return None
    classification = _latest_incident_classification(session, incident_id)
    ai_cause = classification.suggested_contact if classification else None
    ai_reason = classification.llm_hypothesis if classification else None

    attr = _get_or_create_incident_attribution(session, incident_id)
    attr.causing_person = ai_cause
    attr.reason_text = ai_reason
    attr.cause_provenance = Provenance.AI_CONFIRMED
    attr.reason_provenance = Provenance.AI_CONFIRMED
    attr.original_ai_cause = ai_cause
    attr.original_ai_reason = ai_reason
    attr.validated_by = actor
    attr.validated_at = _now()
    attr.signature_id = incident.signature_id
    return attr


def set_incident_attribution(
    session: Session,
    incident_id: int,
    actor: str,
    *,
    causing_person: str | None = None,
    reason_text: str | None = None,
    triage_status: str | None = None,
    cause_ticket: str | None = None,
    resolution_ticket: str | None = None,
    assignee: str | None = None,
    problem_text: str | None = None,
) -> BuildIncident | None:
    """Human edit of a Build Incident's cause/reason/triage + documentation fields.

    Mirrors :func:`set_attribution` for the build-level surface: cause/reason are provenance-tracked
    conclusions on the reused Attribution row, ``triage_status`` / ``assignee`` / the two tickets /
    the ``problem_text`` documentation are set directly on the incident (``None`` leaves a field
    untouched, an empty string clears it). Returns None if the incident doesn't exist.
    """
    incident = session.get(BuildIncident, incident_id)
    if incident is None:
        return None
    classification = _latest_incident_classification(session, incident_id)
    ai_cause = classification.suggested_contact if classification else None
    ai_reason = classification.llm_hypothesis if classification else None

    attr = _get_or_create_incident_attribution(session, incident_id)
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
        incident.triage_status = triage_status
    if cause_ticket is not None:
        incident.cause_ticket = cause_ticket.strip() or None
    if resolution_ticket is not None:
        incident.resolution_ticket = resolution_ticket.strip() or None
    if assignee is not None:
        incident.assignee = assignee.strip() or None
    if problem_text is not None:
        incident.problem_text = problem_text.strip() or None

    if touched:
        attr.entered_by = actor
        attr.validated_by = actor
        attr.validated_at = _now()
        attr.signature_id = incident.signature_id
    return incident
