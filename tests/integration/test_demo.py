"""End-to-end integration tests over the synthetic demo dataset.

These drive the *real* ingest -> analysis -> web stack on the fabricated history (no external
system), so they double as the smoke test for the online-hosted demo: if these pass, the deployed
app renders a populated, coherent dashboard. They run in the default offline suite (no ``live``
marker), so CI executes them on every PR.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from uta.demo.app import build_demo_session_factory, create_demo_app
from uta.demo.dataset import FIRST_BUILD
from uta.models import TestIdentity
from uta.web import views

_MEMORY = "sqlite+pysqlite:///:memory:"


@pytest.fixture(scope="module")
def session_factory():
    """One seeded in-memory store shared across the read-only assertions (seeding is slow)."""
    return build_demo_session_factory(_MEMORY)


@pytest.fixture(scope="module")
def queue(session_factory):
    return views.triage_queue(session_factory(), recently_fixed_days=7, limit=200)


def test_every_triage_bucket_is_populated(queue):
    counts = queue["counts"]
    assert counts["new"] >= 1
    assert counts["still_failing"] >= 1
    assert counts["recently_fixed"] >= 1


def test_all_four_predicted_causes_are_represented(queue):
    causes = {
        row["predicted_cause"]
        for bucket in ("new", "still_failing", "recently_fixed")
        for row in queue[bucket]
    }
    assert {"CODE_CHANGE", "DATA_CHANGE", "INFRASTRUCTURE", "UNKNOWN"} <= causes


def test_removed_test_is_flagged_in_still_failing(queue):
    assert any(row.get("removed") for row in queue["still_failing"])


def test_track_divergent_failure_shows_under_its_track_only(session_factory, queue):
    """Issue #84: rows carry every failing track, and the track filter matches any of them —
    the py39-only failure appears under ?track=permanent_py39 but not ?track=permanent, while
    the both-track failures show under either."""
    py39_only = "ut_core.co_compat.TestClass.test_type_union_annotation"
    rows = {r["test_id"]: r for r in queue["new"]}
    assert rows[py39_only]["tracks"] == ["permanent_py39"]
    both = "ut_billing.bi_round.TestClass.test_invoice_rounding"
    assert rows[both]["tracks"] == ["permanent", "permanent_py39"]

    def new_names(track: str) -> set[str]:
        filtered = views.triage_queue(
            session_factory(), recently_fixed_days=7, limit=200, filters={"track": track}
        )
        return {r["test_id"] for r in filtered["new"]}

    assert py39_only not in new_names("permanent")
    assert py39_only in new_names("permanent_py39")
    assert both in new_names("permanent") and both in new_names("permanent_py39")


def test_acknowledged_and_attributed_failure_is_present(queue):
    tz = next(
        r
        for r in queue["still_failing"]
        if r["test_id"] == "ut_core.co_time.TestClass.test_timezone_convert"
    )
    assert tz["acknowledged"] is True
    assert tz["causing_person"] == "THA"
    assert tz["predicted_cause"] == "DATA_CHANGE"


def test_suggested_contact_populated_from_sole_change_author(session_factory):
    # #49: a CODE_CHANGE episode whose window holds a single-author commit carries that author as
    # the suggested contact, so the live demo shows the one-click-Confirm surface populated.
    session = session_factory()
    ident = session.scalar(
        select(TestIdentity).where(
            TestIdentity.canonical_name == "ut_interface.if_hl7.TestClass.test_parse_message"
        )
    )
    record = views.test_record(session, ident.id)
    ep = record["episodes"][0]  # newest episode — opened by the build-613 regression
    assert ep["predicted_cause"] == "CODE_CHANGE"
    assert ep["suggested_contact"] == "R. Devlin"


def test_data_change_contact_suggested_and_human_corrected(session_factory):
    # The DATA_CHANGE episode suggests the V_TRACKING USRCODE ("MEL"); the seeded human attribution
    # ("THA") then reads as a correction — the demo shows the HUMAN_CORRECTED provenance tier.
    session = session_factory()
    ident = session.scalar(
        select(TestIdentity).where(
            TestIdentity.canonical_name == "ut_core.co_time.TestClass.test_timezone_convert"
        )
    )
    record = views.test_record(session, ident.id)
    ep = record["episodes"][0]
    assert ep["predicted_cause"] == "DATA_CHANGE"
    assert ep["suggested_contact"] == "MEL"
    assert ep["causing_person"] == "THA"
    assert ep["cause_provenance"] == "HUMAN_CORRECTED"
    assert ep["original_ai_cause"] == "MEL"


def test_flaky_leaderboard_has_a_flaky_test(session_factory):
    board = views.flaky_leaderboard(session_factory(), window_days=30, threshold=0.3)
    flaky = [r for r in board["rows"] if r["flaky"]]
    assert flaky, "expected at least one flaky test on the leaderboard"
    assert any(r["test_id"].endswith("test_pdf_render") for r in flaky)


def test_recurrence_and_similar_cases(session_factory):
    session = session_factory()
    ident = session.scalar(
        select(TestIdentity).where(
            TestIdentity.canonical_name == "ut_core.co_time.TestClass.test_timezone_convert"
        )
    )
    record = views.test_record(session, ident.id)
    recurrence = record["recurrence"]
    assert recurrence is not None
    assert recurrence["occurrence_count"] > 1  # the same failure recurs across builds
    assert recurrence["similar"], "expected fuzzy-similar past cases"


def test_divergent_top_ranked_candidates_in_the_same_run(session_factory):
    """Two failures of the same run history lead with visibly different top candidates (#50):
    the invoice-rounding failure's is the commit touching its own module (path overlap), the
    timezone failure's is the LORDER data change its error text names (entity mention)."""
    session = session_factory()

    def record_of(name: str) -> dict:
        ident = session.scalar(select(TestIdentity).where(TestIdentity.canonical_name == name))
        return views.test_record(session, ident.id)

    inv = record_of("ut_billing.bi_round.TestClass.test_invoice_rounding")
    top_code = inv["candidates"]["code"][0]
    assert top_code["score"] > 0
    assert any("bi_round.py" in r for r in top_code["reasons"])
    # Both candidate kinds were in its window, but only the commit matches -> tie-break to CODE.
    assert inv["candidates"]["data"], "expected data candidates in the same window"
    assert all(d["score"] == 0 for d in inv["candidates"]["data"])
    assert inv["episodes"][0]["predicted_cause"] == "CODE_CHANGE"
    assert inv["episodes"][0]["evidence"]["relevance"]["tie_break"] == "code"

    tz = record_of("ut_core.co_time.TestClass.test_timezone_convert")
    top_data = tz["candidates"]["data"][0]
    assert top_data["entity"] == "LORDER"
    assert any("LORDER" in r and "mentioned" in r for r in top_data["reasons"])
    # The other entity in the same window didn't match and ranks below.
    assert tz["candidates"]["data"][1]["score"] == 0


def test_score_magnitude_tie_break_resolves_to_code(session_factory):
    """Both candidate kinds match test_discount_tiers, but the tier-3 module match outscores the
    tier-2 component mention — the margin-aware tie-break (issue #73) resolves it to CODE_CHANGE
    (previously UNKNOWN) with a visible mid-range confidence, and the seed's one-click Confirm
    stamps AI_CONFIRMED so the accuracy metric has a confirmed verdict."""
    session = session_factory()
    ident = session.scalar(
        select(TestIdentity).where(
            TestIdentity.canonical_name == "ut_pricing.pr_engine.TestClass.test_discount_tiers"
        )
    )
    record = views.test_record(session, ident.id)
    ep = record["episodes"][0]
    evidence = ep["evidence"]
    assert evidence["code_candidates"] and evidence["data_candidates"]
    assert evidence["relevance"]["top_code"]["score"] == 3.0
    assert evidence["relevance"]["top_data"]["score"] == 2.0
    assert ep["predicted_cause"] == "CODE_CHANGE"
    assert evidence["relevance"]["tie_break"] == "code"
    assert ep["confidence"] == pytest.approx(0.63)
    # The seeded Confirm accepted the suggested contact (the build-612 commit's sole author).
    assert ep["causing_person"] == "P. Nowak"
    assert ep["cause_provenance"] == "AI_CONFIRMED"


def test_every_new_classification_carries_a_confidence(session_factory, queue):
    """#73's acceptance: confidence is populated (non-None) for every newly classified episode."""
    session = session_factory()
    for bucket in ("new", "still_failing", "recently_fixed"):
        for row in queue[bucket]:
            if row["predicted_cause"] is None:
                continue
            record = views.test_record(session, row["identity_id"])
            classified = [e for e in record["episodes"] if e["predicted_cause"]]
            assert classified and all(e["confidence"] is not None for e in classified), row[
                "test_id"
            ]


def test_control_panel_shows_ai_accuracy(session_factory):
    """The demo seeds one confirmed (discount-tiers) and one corrected (timezone) AI cause, so the
    control panel's accuracy metric renders populated (issue #73)."""
    from uta.config import Settings
    from uta.web import control

    panel = control.control_panel(session_factory(), Settings())
    acc = panel["ai_accuracy"]
    assert acc["has_data"] is True
    assert acc["all_time"]["cause"]["confirmed"] == 1
    assert acc["all_time"]["cause"]["corrected"] == 1
    assert acc["all_time"]["cause"]["precision"] == pytest.approx(0.5)


def test_pdf_render_ties_stay_unknown_without_relevance(session_factory):
    """The flaky test's build-612 episode saw both candidate kinds but neither matches it, so
    the tie deliberately stays UNKNOWN (contrast with the invoice-rounding tie-break above)."""
    session = session_factory()
    ident = session.scalar(
        select(TestIdentity).where(
            TestIdentity.canonical_name == "ut_reporting.rp_pdf.TestClass.test_pdf_render"
        )
    )
    record = views.test_record(session, ident.id)
    both_kinds = [
        e
        for e in record["episodes"]
        if e["evidence"] and e["evidence"]["code_candidates"] and e["evidence"]["data_candidates"]
    ]
    assert both_kinds, "expected an episode opened in a build carrying both candidate kinds"
    assert all(e["predicted_cause"] == "UNKNOWN" for e in both_kinds)
    assert all(e["evidence"]["relevance"]["tie_break"] is None for e in both_kinds)


def test_run_summary_has_baseline_and_diff(session_factory):
    # Build 612 (index 11) opens the invoice-rounding regression.
    run = views.run_summary(session_factory(), FIRST_BUILD + 11, limit=500)
    assert run is not None
    assert run["complete"] is True
    assert run["baseline"] is not None
    assert run["baseline"]["build"] == FIRST_BUILD + 10
    reg = {r["test_id"] for r in run["diff"]["regressions"]["rows"]}
    assert "ut_billing.bi_round.TestClass.test_invoice_rounding" in reg


def test_demo_app_serves_all_views():
    client = TestClient(create_demo_app(_MEMORY))
    health = client.get("/health")
    assert health.status_code == 200
    # The seeded heartbeat is fresh, so the demo reports a healthy poller.
    assert health.json()["status"] == "ok"
    assert health.json()["poller"] == "ok"
    for path in ("/", "/flaky", "/kb", f"/runs/{FIRST_BUILD + 11}"):
        resp = client.get(path)
        assert resp.status_code == 200, path
        assert resp.text  # non-empty HTML
    assert "test_" in client.get("/").text  # the triage queue lists tests


def test_demo_health_stays_ok_past_the_staleness_window():
    """Issue #125: the demo runs no poller, so the heartbeat seeded for /control would cross the
    staleness window (poll_interval × stale_after_intervals, ~21 min with defaults) and flip
    /health to 503 — Render's healthCheckPath would then restart the service, wiping the ephemeral
    store mid-session. Every /health probe re-stamps the heartbeat first, so the demo stays 200 no
    matter how old the process is, while /control still renders a populated heartbeat."""
    from datetime import UTC, datetime, timedelta

    from uta.config import Settings
    from uta.control.health import check_health
    from uta.control.heartbeat import read_heartbeat
    from uta.db import session_scope
    from uta.web import control

    factory = build_demo_session_factory(_MEMORY)
    client = TestClient(create_demo_app(session_factory=factory))

    # Age the seeded heartbeat far beyond the window — a demo process that has lived for hours.
    aged = datetime.now(UTC) - timedelta(hours=6)
    with session_scope(factory) as session:
        hb = read_heartbeat(session)
        hb.last_poll_at = aged
        hb.last_success_at = aged
    # Sanity: a bare check_health sees exactly the stale fault that used to 503 the demo.
    assert check_health(factory, Settings()).poller == "stale"

    # The demo app itself stays healthy: the probe re-stamps the heartbeat before evaluating it.
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["poller"] == "ok"

    # The /control panel still shows a populated heartbeat — now fresh, seeded details intact.
    panel = control.control_panel(factory(), Settings())
    assert panel["poller"]["has_run"] is True
    assert panel["poller"]["last_processed_count"] == 1
    assert panel["poller"]["last_success_at"].replace(tzinfo=UTC) > aged  # SQLite reads back naive
    assert client.get("/control").status_code == 200


def test_shared_outage_pair_offers_signature_wide_attribution(session_factory):
    """The demo's shop-window for issue #106: the SMTP-outage pair is seeded new & untriaged with
    identical error text, so each test's record page renders the "apply to all N affected tests"
    signature-wide attribution control (N=2)."""
    from uta.web.app import create_app

    session = session_factory()
    client = TestClient(create_app(session_factory=session_factory))
    for method in ("test_email_dispatch", "test_sms_dispatch"):
        ident_id = session.scalar(
            select(TestIdentity.id).where(
                TestIdentity.canonical_name == f"ut_notify.nt_dispatch.TestClass.{method}"
            )
        )
        record = views.test_record(session, ident_id)
        assert record["recurrence"]["open_affected"] == 2
        page = client.get(f"/tests/{ident_id}").text
        assert "Apply to all 2 affected tests with this signature" in page
        assert f'formaction="/signatures/{record["recurrence"]["signature_id"]}/attribute"' in page


def test_shared_outage_pair_shows_ack_blast_radius(session_factory, queue):
    """Issue #152: the SMTP-outage pair's New rows carry the signature-wide ack blast radius, so
    the live demo renders "Ack all w/ signature (2)" on exactly those two rows — every other New
    row's signature matches only itself, so it shows no bulk-ack button at all."""
    from uta.web.app import create_app

    pair = {
        f"ut_notify.nt_dispatch.TestClass.{m}" for m in ("test_email_dispatch", "test_sms_dispatch")
    }
    for row in queue["new"]:
        expected = 2 if row["test_id"] in pair else 1
        assert row["signature_ack_count"] == expected, row["test_id"]

    page = TestClient(create_app(session_factory=session_factory)).get("/").text
    assert page.count("Ack all w/ signature (2)") == 2  # one per row of the pair, nothing else
    assert page.count("Ack all w/ signature") == 2


def test_reseeding_the_same_store_converges():
    """Issue #122: re-running ``uta seed-demo`` against a persistent store must converge, not
    crash — the control-state rows used to be blindly ``add``ed, so a second seed died with a
    duplicate-PK IntegrityError (and the auto-PK demo ingest jobs would have duplicated)."""
    from datetime import UTC, datetime

    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    from uta.db import Base, make_session_factory
    from uta.demo.seed import seed_demo_data
    from uta.models import BuildQuarantine, IngestJob, PollerHeartbeat, SettingOverride

    anchor = datetime(2026, 7, 1, 3, 30, tzinfo=UTC)  # fixed so both stores seed identically

    def fresh_factory():
        engine = create_engine(
            _MEMORY, connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
        )
        Base.metadata.create_all(engine)
        return make_session_factory(engine)

    def control_state(factory):
        session = factory()
        return (
            [
                (h.id, h.last_poll_at, h.last_success_at, h.last_processed, h.last_error)
                for h in session.scalars(select(PollerHeartbeat))
            ],
            [
                (q.build_number, q.attempts, q.last_error, q.quarantined_at)
                for q in session.scalars(select(BuildQuarantine))
            ],
            sorted(
                (o.key, o.value, o.updated_by) for o in session.scalars(select(SettingOverride))
            ),
            [
                (j.build_start, j.build_end, j.status, j.builds_done, j.error, j.requested_by)
                for j in session.scalars(select(IngestJob).order_by(IngestJob.build_start))
            ],
        )

    twice = fresh_factory()
    seed_demo_data(twice, anchor=anchor)
    seed_demo_data(twice, anchor=anchor)  # must not raise

    once = fresh_factory()
    seed_demo_data(once, anchor=anchor)

    heartbeats, quarantines, overrides, jobs = control_state(twice)
    assert len(heartbeats) == 1
    assert len(quarantines) == 1
    assert len(overrides) == 2
    assert len(jobs) == 2
    assert (heartbeats, quarantines, overrides, jobs) == control_state(once)


def test_triage_rows_carry_error_snippets(queue):
    """Issue #145: every failing row in the New bucket shows its one-line exception snippet, and
    the still-failing timezone test shows the message the deep-trace clamp example builds on."""
    for row in queue["new"]:
        assert row["error_snippet"], row["test_id"]
    snippets = {r["test_id"]: r["error_snippet"] for r in queue["new"]}
    assert (
        snippets["ut_billing.bi_round.TestClass.test_invoice_rounding"]
        == "AssertionError: values differ: expected 100 got 101"
    )
    tz = next(
        r
        for r in queue["still_failing"]
        if r["test_id"] == "ut_core.co_time.TestClass.test_timezone_convert"
    )
    assert tz["error_snippet"] == "AssertionError: values differ for LORDER: expected 2 got 1"


def test_timezone_record_exercises_the_trace_clamp(session_factory):
    """Issue #145: the seeded deep trace exceeds the 15-line clamp so the live demo's record
    page demonstrates the "Show full trace" toggle (clamping is client-side; full text ships)."""
    session = session_factory()
    ident_id = session.scalar(
        select(TestIdentity.id).where(
            TestIdentity.canonical_name == "ut_core.co_time.TestClass.test_timezone_convert"
        )
    )
    record = views.test_record(session, ident_id)
    current = record["episodes"][0]
    trace = current["failure"]["error_stack_trace"]
    assert len(trace.splitlines()) > 15
    # The padding frames are library frames — the signature (and the KB similarity family built
    # on it) must stay based on the in-tree frame + exception line only.
    assert "site-packages" in trace


def test_demo_app_test_record_route():
    from uta.web.app import create_app

    factory = build_demo_session_factory(_MEMORY)
    ident_id = factory().scalar(
        select(TestIdentity.id).where(
            TestIdentity.canonical_name == "ut_core.co_time.TestClass.test_timezone_convert"
        )
    )
    client = TestClient(create_app(session_factory=factory))
    resp = client.get(f"/tests/{ident_id}")
    assert resp.status_code == 200
    assert "timezone" in resp.text.lower()
