"""Build Incident feature (issue #171): streak lifecycle, enrichment, namespacing, ingest, email."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from tests.builders import make_build
from tests.fakes.email import RecordingEmailSender
from uta.analyze.incident import apply_build_incident
from uta.db import session_scope
from uta.ingest.pipeline import ingest_build
from uta.kb.retrieval import similar_cases
from uta.kb.signature import compute_hash, normalize, normalize_incident
from uta.kb.store import record_signatures_for_build
from uta.models import (
    Attribution,
    BuildIncident,
    Classification,
    CodeChangeCandidate,
    FailureSignature,
)
from uta.models.enums import IncidentKind, PredictedCause, Provenance, SignatureKind
from uta.web import actions

_LOG = "[ERROR] BUILD FAILURE\ncompilation failed in module lx\nexit 1"


# ── Streak lifecycle ──────────────────────────────────────────────────────────────────────────


def test_pipeline_failure_opens_incident_with_signature_and_classification(session_factory):
    with session_scope(session_factory) as s:
        b = make_build(s, 1, {})
        out = apply_build_incident(s, b, "FAILURE", failing_stage="Compile", failing_stage_log=_LOG)
        assert out.opened is True
        inc = out.incident
        assert inc.kind == IncidentKind.PIPELINE_FAILURE
        assert inc.is_open is True and inc.failing_stage == "Compile"
        assert inc.signature_id is not None
        sig = s.get(FailureSignature, inc.signature_id)
        assert sig.kind == SignatureKind.INCIDENT and sig.test_identity_id is None
        classification = s.scalar(
            select(Classification).where(Classification.incident_id == inc.id)
        )
        assert classification is not None


def test_streak_collapses_consecutive_non_green_into_one_incident(session_factory):
    with session_scope(session_factory) as s:
        b1 = make_build(s, 1, {})
        b2 = make_build(s, 2, {})
        apply_build_incident(s, b1, "FAILURE", failing_stage="Compile", failing_stage_log=_LOG)
        out2 = apply_build_incident(
            s, b2, "FAILURE", failing_stage="Compile", failing_stage_log=_LOG
        )
        assert out2.opened is False
        assert s.scalar(select(BuildIncident).where(BuildIncident.is_open.is_(True))) is not None
        assert s.scalar(select(BuildIncident)).build_count == 2
        assert s.query(BuildIncident).count() == 1


def test_mixed_kind_streak_stays_one_incident(session_factory):
    with session_scope(session_factory) as s:
        b1 = make_build(s, 1, {})
        b2 = make_build(s, 2, {})
        apply_build_incident(s, b1, "FAILURE", failing_stage="Compile", failing_stage_log=_LOG)
        apply_build_incident(s, b2, "ABORTED")
        assert s.query(BuildIncident).count() == 1
        inc = s.scalar(select(BuildIncident))
        assert inc.kind == IncidentKind.PIPELINE_FAILURE  # kind = whatever opened it
        assert inc.mixed_kinds == IncidentKind.ABORTED
        assert inc.build_count == 2


def test_recovery_on_success_closes_incident(session_factory):
    with session_scope(session_factory) as s:
        b1 = make_build(s, 1, {})
        b2 = make_build(s, 2, {})
        apply_build_incident(s, b1, "FAILURE", failing_stage="Compile", failing_stage_log=_LOG)
        out = apply_build_incident(s, b2, "SUCCESS")
        assert out.recovered is True
        inc = s.scalar(select(BuildIncident))
        assert inc.is_open is False
        assert inc.recovered_build_id == b2.id


def test_unstable_recovers_independent_of_completeness(session_factory):
    with session_scope(session_factory) as s:
        b1 = make_build(s, 1, {})
        b2 = make_build(s, 2, {})
        apply_build_incident(s, b1, "FAILURE", failing_stage="Compile", failing_stage_log=_LOG)
        out = apply_build_incident(s, b2, "UNSTABLE")
        assert out.recovered is True
        assert s.scalar(select(BuildIncident)).is_open is False


def test_reopen_after_recovery_bumps_flap_count(session_factory):
    with session_scope(session_factory) as s:
        b1, b2, b3 = (make_build(s, n, {}) for n in (1, 2, 3))
        apply_build_incident(s, b1, "FAILURE", failing_stage="Compile", failing_stage_log=_LOG)
        apply_build_incident(s, b2, "SUCCESS")
        out = apply_build_incident(
            s, b3, "FAILURE", failing_stage="Compile", failing_stage_log=_LOG
        )
        assert out.opened is True
        assert s.query(BuildIncident).count() == 2
        assert out.incident.reopen_count == 1


def test_not_built_and_no_open_incident_is_a_noop(session_factory):
    with session_scope(session_factory) as s:
        b = make_build(s, 1, {})
        out = apply_build_incident(s, b, "NOT_BUILT")
        assert out.opened is False and out.recovered is False
        assert s.query(BuildIncident).count() == 0


def test_success_with_no_open_incident_is_a_noop(session_factory):
    with session_scope(session_factory) as s:
        b = make_build(s, 1, {})
        apply_build_incident(s, b, "SUCCESS")
        assert s.query(BuildIncident).count() == 0


# ── FAILURE vs ABORTED enrichment ───────────────────────────────────────────────────────────────


def test_aborted_has_no_signature_no_classification(session_factory):
    with session_scope(session_factory) as s:
        b = make_build(s, 1, {})
        out = apply_build_incident(s, b, "ABORTED", failing_stage="Deploy")
        inc = out.incident
        assert inc.kind == IncidentKind.ABORTED
        assert inc.signature_id is None
        assert s.scalar(select(Classification).where(Classification.incident_id == inc.id)) is None


def test_classification_infrastructure_outranks_changes(session_factory):
    with session_scope(session_factory) as s:
        b = make_build(s, 1, {})
        log = "psql: connection refused\ncould not connect to database"
        out = apply_build_incident(s, b, "FAILURE", failing_stage="Deploy", failing_stage_log=log)
        c = s.scalar(select(Classification).where(Classification.incident_id == out.incident.id))
        assert c.predicted_cause == PredictedCause.INFRASTRUCTURE


def test_classification_code_change_with_sole_author(session_factory):
    with session_scope(session_factory) as s:
        b = make_build(s, 1, {})
        b.code_changes.append(
            CodeChangeCandidate(
                commit_id="r1",
                revision="r1",
                author="dev-dana",
                message="x",
                committed_at=datetime(2026, 6, 1, tzinfo=UTC),
            )
        )
        s.flush()
        out = apply_build_incident(s, b, "FAILURE", failing_stage="Compile", failing_stage_log=_LOG)
        c = s.scalar(select(Classification).where(Classification.incident_id == out.incident.id))
        assert c.predicted_cause == PredictedCause.CODE_CHANGE
        assert c.suggested_contact == "dev-dana"


# ── Signature namespacing ───────────────────────────────────────────────────────────────────────


def test_signature_kind_namespacing_no_cross_match(session_factory):
    """A test signature and an incident signature with identical text never cross-match."""
    text = "AssertionError: values differ: expected <NUM> got <NUM>"
    with session_scope(session_factory) as s:
        # A test-space signature (kind defaults to TEST).
        r = make_build(
            s,
            1,
            {"alpha": "FAILED"},
            errors={"alpha": ("boom", "AssertionError: values differ: expected 1 got 2")},
        )
        record_signatures_for_build(s, r)
        # An incident-space signature with the same normalized shape.
        b = make_build(s, 2, {})
        inc = apply_build_incident(
            s,
            b,
            "FAILURE",
            failing_stage="Compile",
            failing_stage_log="values differ: expected 1 got 2",
        ).incident
        s.flush()

        # Hashes are namespaced: identical text, different kind -> different hash.
        assert compute_hash("x", text, SignatureKind.TEST) != compute_hash(
            "x", text, SignatureKind.INCIDENT
        )
        # A TEST-space search never surfaces the incident signature and vice-versa.
        test_hits = similar_cases(s, text, cutoff=0.1, kind=SignatureKind.TEST)
        incident_hits = similar_cases(s, text, cutoff=0.1, kind=SignatureKind.INCIDENT)
        assert all(s.get(FailureSignature, h.signature_id).kind == "TEST" for h in test_hits)
        assert all(
            s.get(FailureSignature, h.signature_id).kind == "INCIDENT" for h in incident_hits
        )
        assert inc.signature_id in {h.signature_id for h in incident_hits}
        assert inc.signature_id not in {h.signature_id for h in test_hits}


def test_incident_signature_recurs_on_same_stage(session_factory):
    with session_scope(session_factory) as s:
        b1 = make_build(s, 1, {})
        inc1 = apply_build_incident(
            s, b1, "FAILURE", failing_stage="Compile", failing_stage_log=_LOG
        ).incident
        sig_id = inc1.signature_id
        apply_build_incident(s, make_build(s, 2, {}), "SUCCESS")
        b3 = make_build(s, 3, {})
        inc2 = apply_build_incident(
            s, b3, "FAILURE", failing_stage="Compile", failing_stage_log=_LOG
        ).incident
        assert inc2.signature_id == sig_id  # same normalized failing-stage log recurs
        assert s.get(FailureSignature, sig_id).occurrence_count == 2


def test_normalize_incident_masks_and_tails():
    sig = normalize_incident("row 12345 failed\nexit code 1\n")
    assert sig is not None and "<NUM>" in sig.text
    assert normalize_incident("   \n  ") is None


# ── Ingest gating + high-water mark + email ──────────────────────────────────────────────────────


class _IncidentJenkins:
    """A programmatic Jenkins fake: each build has a result and an optional failing stage/log."""

    def __init__(self, builds: dict[int, dict]) -> None:
        self._builds = builds

    def build_meta(self, build: int) -> dict:
        b = self._builds[build]
        return {
            "number": build,
            "result": b["result"],
            "url": f"http://ci/{build}",
            "timestamp": 1_700_000_000_000 + build * 3_600_000,
        }

    def test_report(self, build: int) -> dict:
        return {"suites": []}

    def change_sets(self, build: int) -> dict:
        return {"changeSets": self._builds[build].get("change_sets", [])}

    def wfapi(self, build: int) -> dict:
        b = self._builds[build]
        start = 1_700_000_000_000 + build * 3_600_000
        stages = [
            {
                "id": "300",
                "name": "devUTs: Execute - permanent",
                "status": "SUCCESS" if b["result"] != "ABORTED" else "ABORTED",
                "startTimeMillis": start,
                "durationMillis": 60_000,
            }
        ]
        if b.get("stage"):
            stages.append(
                {
                    "id": "500",
                    "name": b["stage"],
                    "status": "FAILED" if b["result"] == "FAILURE" else "ABORTED",
                    "startTimeMillis": start,
                    "durationMillis": 60_000,
                }
            )
        return {
            "id": str(build),
            "name": f"#{build}",
            "status": b["result"],
            "startTimeMillis": start,
            "durationMillis": 60_000,
            "stages": stages,
        }

    def stage_describe(self, build: int, node_id: str) -> dict:
        return {"id": str(node_id), "stageFlowNodes": []}

    def stage_log(self, build: int, node_id: str) -> dict:
        return {"nodeId": str(node_id), "text": self._builds[build].get("log", "")}

    def last_completed_build(self) -> int | None:
        return max(self._builds)


def _ingest(client, sf, number, **kw):
    return ingest_build(client, sf, number, expected_tracks=2, **kw)


def test_ingest_gating_flag_off_creates_no_incident(session_factory):
    client = _IncidentJenkins({1: {"result": "FAILURE", "stage": "Compile", "log": _LOG}})
    _ingest(client, session_factory, 1, ingest_build_incidents=False)
    with session_scope(session_factory) as s:
        assert s.query(BuildIncident).count() == 0


def test_ingest_gating_flag_on_creates_incident_even_when_incomplete(session_factory):
    client = _IncidentJenkins({1: {"result": "FAILURE", "stage": "Compile", "log": _LOG}})
    _ingest(client, session_factory, 1, ingest_build_incidents=True)
    with session_scope(session_factory) as s:
        inc = s.scalar(select(BuildIncident))
        assert inc is not None and inc.kind == IncidentKind.PIPELINE_FAILURE
        # The FAILURE build reports only one track -> incomplete, yet the incident still opened.
        from uta.models import Build

        assert s.scalar(select(Build.complete).where(Build.build_number == 1)) is False


def test_ingest_recovery_seen_after_failed_build(session_factory):
    client = _IncidentJenkins(
        {
            1: {"result": "FAILURE", "stage": "Compile", "log": _LOG},
            2: {"result": "SUCCESS"},
        }
    )
    _ingest(client, session_factory, 1, ingest_build_incidents=True)
    _ingest(client, session_factory, 2, ingest_build_incidents=True)
    with session_scope(session_factory) as s:
        inc = s.scalar(select(BuildIncident))
        assert inc.is_open is False and inc.recovered_build_id is not None


def test_incident_email_only_on_new_pipeline_failure(session_factory):
    client = _IncidentJenkins(
        {
            1: {"result": "FAILURE", "stage": "Compile", "log": _LOG},
            2: {"result": "FAILURE", "stage": "Compile", "log": _LOG},  # extend -> no email
            3: {"result": "SUCCESS"},  # recovery -> no email
            4: {"result": "ABORTED", "stage": "Deploy"},  # aborted -> no email
        }
    )
    sender = RecordingEmailSender()
    for n in (1, 2, 3, 4):
        _ingest(
            client,
            session_factory,
            n,
            ingest_build_incidents=True,
            email_sender=sender,
            email_recipients=("team@x",),
        )
    incident_alerts = [m for m in sender.sent if "incident opened" in m.subject]
    assert len(incident_alerts) == 1
    assert "#1" in incident_alerts[0].subject


# ── Incident triage actions + generalized episode fields ─────────────────────────────────────────


def test_incident_actions_acknowledge_confirm_attribute(session_factory):
    with session_scope(session_factory) as s:
        b = make_build(s, 1, {})
        b.code_changes.append(
            CodeChangeCandidate(
                commit_id="r1",
                revision="r1",
                author="dev-dana",
                message="x",
                committed_at=datetime(2026, 6, 1, tzinfo=UTC),
            )
        )
        s.flush()
        inc = apply_build_incident(
            s, b, "FAILURE", failing_stage="Compile", failing_stage_log=_LOG
        ).incident
        s.flush()

        assert actions.acknowledge_incident(s, inc.id, "kev") is True
        assert inc.acknowledged and inc.acknowledged_by == "kev"

        attr = actions.confirm_incident(s, inc.id, "kev")
        assert attr.cause_provenance == Provenance.AI_CONFIRMED
        assert attr.causing_person == "dev-dana"  # the suggested contact

        actions.set_incident_attribution(
            s,
            inc.id,
            "kev",
            causing_person="real-rita",
            reason_text="regression in signature",
            problem_text="compile broke",
            triage_status="ROOT_CAUSED",
            assignee="ann",
            cause_ticket="LX-1",
            resolution_ticket="LX-2",
        )
        assert inc.triage_status == "ROOT_CAUSED"
        assert inc.assignee == "ann"
        assert inc.cause_ticket == "LX-1" and inc.resolution_ticket == "LX-2"
        assert inc.problem_text == "compile broke"
        attr = s.scalar(select(Attribution).where(Attribution.incident_id == inc.id))
        assert attr.causing_person == "real-rita"
        assert attr.cause_provenance == Provenance.HUMAN_CORRECTED


def test_episode_generalized_ticket_and_assignee_fields(session_factory):
    from uta.analyze.lifecycle import apply_build
    from uta.models import FailureEpisode

    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"t": "FAILED"})
        apply_build(s, r1, baseline=None)
        ep = s.scalar(select(FailureEpisode))
        actions.set_attribution(
            s,
            ep.id,
            "bob",
            assignee="  ann  ",
            cause_ticket="LX-10",
            resolution_ticket="LX-11",
        )
        assert ep.assignee == "ann"
        assert ep.cause_ticket == "LX-10" and ep.resolution_ticket == "LX-11"
        # Empty clears; None leaves untouched.
        actions.set_attribution(s, ep.id, "bob", resolution_ticket="")
        assert ep.resolution_ticket is None
        assert ep.cause_ticket == "LX-10"


def test_normalize_still_test_namespaced_by_default():
    """The two-arg compute_hash (the historical test path) is unchanged (kind defaults to TEST)."""
    sig = normalize("boom", "AssertionError: x")
    assert sig is not None
    assert compute_hash("id", sig.text) == compute_hash("id", sig.text, SignatureKind.TEST)
