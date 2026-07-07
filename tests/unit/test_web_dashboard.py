"""HTTP-level tests of the dashboard routes (FastAPI TestClient, injected SQLite session factory).

Covers the triage-queue / per-test-record / run-summary pages, the Phase-1 identity cookie, and the
Post/Redirect/Get actions actually mutating state through the app (not just the service functions).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from tests.builders import get_identity, make_run
from uta.analyze.lifecycle import apply_run
from uta.db import Base, make_session_factory, session_scope
from uta.models import CodeChangeCandidate, Run, TestLifecycle
from uta.web.app import create_app


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


@pytest.fixture
def seeded(session_factory):
    """One failing test ("alpha") with an open episode, plus a passing one ("beta")."""
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"alpha": "FAILED", "beta": "PASSED"})
        apply_run(s, r1, baseline=None)
    return session_factory


@pytest.fixture
def client(seeded):
    return TestClient(create_app(session_factory=seeded), follow_redirects=False)


def _identity_id(session_factory, name) -> int:
    with session_scope(session_factory) as s:
        return get_identity(s, name).id


def test_triage_landing_lists_new_failure(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Daily triage queue" in resp.text
    assert "alpha" in resp.text
    assert "test-user" in resp.text  # default actor in the header


def test_identity_cookie_sets_actor(client):
    resp = client.post("/identity", data={"actor": "morgan"}, headers={"referer": "/"})
    assert resp.status_code == 303
    assert client.cookies.get("uta_actor") == "morgan"
    # The new actor is reflected in the header.
    assert "morgan" in client.get("/").text


def test_acknowledge_moves_test_out_of_new_bucket(client, seeded):
    ident_id = _identity_id(seeded, "alpha")
    client.cookies.set("uta_actor", "dana")
    resp = client.post(f"/tests/{ident_id}/acknowledge", headers={"referer": "/"})
    assert resp.status_code == 303
    with session_scope(seeded) as s:
        lc = s.scalar(select(TestLifecycle).where(TestLifecycle.test_identity_id == ident_id))
        assert lc.acknowledged is True
        assert lc.acknowledged_by == "dana"


def test_test_record_page_renders(client, seeded):
    ident_id = _identity_id(seeded, "alpha")
    resp = client.get(f"/tests/{ident_id}")
    assert resp.status_code == 200
    assert "alpha" in resp.text
    assert "Failure episodes" in resp.text


def test_attribute_form_persists_reason(client, seeded):
    ident_id = _identity_id(seeded, "alpha")
    with session_scope(seeded) as s:
        lc = s.scalar(select(TestLifecycle).where(TestLifecycle.test_identity_id == ident_id))
        ep_id = lc.current_episode_id
    client.cookies.set("uta_actor", "erin")
    resp = client.post(
        f"/episodes/{ep_id}/attribute",
        data={
            "causing_person": "frank",
            "reason_text": "flaky fixture",
            "triage_status": "INVESTIGATING",
        },
        headers={"referer": f"/tests/{ident_id}"},
    )
    assert resp.status_code == 303
    page = client.get(f"/tests/{ident_id}").text
    assert "frank" in page and "flaky fixture" in page


def test_jira_ticket_persists_and_links(client, seeded):
    ident_id = _identity_id(seeded, "alpha")
    with session_scope(seeded) as s:
        lc = s.scalar(select(TestLifecycle).where(TestLifecycle.test_identity_id == ident_id))
        ep_id = lc.current_episode_id
    client.cookies.set("uta_actor", "erin")
    resp = client.post(
        f"/episodes/{ep_id}/attribute",
        data={"jira_ticket": "ABC-123"},
        headers={"referer": f"/tests/{ident_id}"},
    )
    assert resp.status_code == 303
    page = client.get(f"/tests/{ident_id}").text
    assert "https://labsolution.atlassian.net/browse/ABC-123" in page
    # An empty submission clears it (editable both ways).
    client.post(
        f"/episodes/{ep_id}/attribute",
        data={"jira_ticket": ""},
        headers={"referer": f"/tests/{ident_id}"},
    )
    assert "browse/ABC-123" not in client.get(f"/tests/{ident_id}").text


def test_detail_sections_are_collapsible_and_reordered(client, seeded):
    ident_id = _identity_id(seeded, "alpha")
    page = client.get(f"/tests/{ident_id}").text
    # Native collapsibles, with the important sections expanded by default.
    assert '<details class="card" open>' in page  # Lifecycle
    assert '<details class="episodes" open>' in page  # Failure episodes
    # The standalone "Latest failure" section is gone; failure detail lives inside episodes.
    assert "Latest failure" not in page
    assert "Failure detail" in page
    # Lifecycle comes before Failure episodes, which precede the flakiness/KB sections.
    assert page.index("Lifecycle") < page.index("Failure episodes")


def test_current_open_episode_failure_detail_is_expanded(client, seeded):
    """The failure block is expanded (open) only for the current+open episode."""
    ident_id = _identity_id(seeded, "alpha")
    page = client.get(f"/tests/{ident_id}").text
    # The Failure detail block for the current+open episode is rendered open.
    summary_idx = page.index("Failure detail")
    # Walk back to the opening <details ...> tag of that block.
    open_tag_start = page.rindex("<details", 0, summary_idx)
    open_tag = page[open_tag_start:summary_idx]
    assert " open>" in open_tag


def test_svn_revision_links_to_fisheye(client, seeded):
    ident_id = _identity_id(seeded, "alpha")
    with session_scope(seeded) as s:
        run = s.scalar(select(Run).where(Run.build_number == 1))
        s.add(
            CodeChangeCandidate(
                run_id=run.id, commit_id="135180", revision="135180", committed_at=run.started_at
            )
        )
    page = client.get(f"/tests/{ident_id}").text
    assert "https://fisheye.labsolution.lu/changelog/LS_TRUNK?cs=135180" in page


def test_run_summary_page_shows_diff_and_results(client):
    resp = client.get("/runs/1")
    assert resp.status_code == 200
    assert "Run #1" in resp.text
    assert "Diff vs baseline" in resp.text
    assert "alpha" in resp.text


def test_unknown_test_record_is_graceful(client):
    resp = client.get("/tests/99999")
    assert resp.status_code == 200
    assert "No record" in resp.text


# ── long-list capping (issue #19) ──────────────────────────────────────────────


@pytest.fixture
def many_failures_client(session_factory, monkeypatch):
    """A store with 150 new failing tests, and the UI capped at 100 rows per section."""
    monkeypatch.setenv("UI_ROW_LIMIT", "100")
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {f"t{i:04d}": "FAILED" for i in range(150)})
        apply_run(s, r1, baseline=None)
    return TestClient(create_app(session_factory=session_factory), follow_redirects=False)


def test_triage_caps_at_limit_and_shows_load_all_hint(many_failures_client):
    page = many_failures_client.get("/").text
    # The count reflects all 150, but the hint offers to load the rest.
    assert "not yet acknowledged (150)" in page
    assert "Load all 150 Tests" in page
    # Only the first 100 rows are rendered (each links to /tests/<id>).
    assert page.count('href="/tests/') == 100


def test_triage_expand_renders_every_row(many_failures_client):
    page = many_failures_client.get("/?expand=new").text
    assert page.count('href="/tests/') == 150
    # Fully expanded → no residual hint.
    assert "Load all 150 Tests" not in page


# ── run-results pagination (issue #52) ─────────────────────────────────────────


def test_run_results_paginate_server_side(many_failures_client):
    # 150 tests × 2 tracks = 300 result rows at a 100-row page size → 3 pages. Each rendered
    # result row opens with its status cell (<td class="FAILED">) — the diff section above the
    # table links tests too, so count row cells, not links.
    page1 = many_failures_client.get("/runs/1").text
    assert "Results (300)" in page1
    assert page1.count('<td class="FAILED">') == 100
    assert "Page 1 of 3 (300 rows)" in page1
    assert 'href="?page=2#results"' in page1  # Next
    assert "Load all" not in page1  # the all-or-nothing expand link is gone

    page2 = many_failures_client.get("/runs/1?page=2").text
    assert "Page 2 of 3 (300 rows)" in page2
    assert page2.count('<td class="FAILED">') == 100
    assert 'href="?page=1#results"' in page2  # Previous
    assert 'href="?page=3#results"' in page2  # Next


def test_run_results_page_out_of_range_is_graceful(many_failures_client):
    resp = many_failures_client.get("/runs/1?page=999")
    assert resp.status_code == 200
    assert "Page 3 of 3 (300 rows)" in resp.text


def test_runs_list_paginates_server_side(session_factory, monkeypatch):
    monkeypatch.setenv("UI_ROW_LIMIT", "2")
    with session_scope(session_factory) as s:
        for build in (1, 2, 3):
            apply_run(s, make_run(s, build, {"t": "PASSED"}), baseline=None)
    client = TestClient(create_app(session_factory=session_factory), follow_redirects=False)

    page1 = client.get("/runs").text
    assert "Page 1 of 2 (3 rows)" in page1
    assert 'href="/runs/3"' in page1 and 'href="/runs/2"' in page1  # newest first
    assert 'href="/runs/1"' not in page1
    page2 = client.get("/runs?page=2").text
    assert 'href="/runs/1"' in page2


# ── triage filters/sort + bulk actions (issue #63) ─────────────────────────────


@pytest.fixture
def multi_owner_client(session_factory):
    """Two new failing tests with distinct owners/suites, for filter-bar assertions."""
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"alpha": "FAILED", "beta": "FAILED"})
        apply_run(s, r1, baseline=None)
        get_identity(s, "alpha").owner_initials = "AB"
        get_identity(s, "alpha").suite = "ut_pricing"
        get_identity(s, "beta").owner_initials = "CD"
        get_identity(s, "beta").suite = "ut_billing"
    return TestClient(create_app(session_factory=session_factory), follow_redirects=False)


def test_triage_owner_filter_reduces_buckets(multi_owner_client):
    page = multi_owner_client.get("/?owner=AB").text
    assert "alpha" in page
    assert "beta" not in page
    assert "not yet acknowledged (1)" in page


def test_triage_filter_bar_options_render(multi_owner_client):
    page = multi_owner_client.get("/").text
    assert 'id="filter-owner"' in page
    assert "ut_pricing" in page  # datalist option
    assert "ut_billing" in page


def test_triage_filter_survives_acknowledge_round_trip(multi_owner_client, session_factory):
    ident_id = _identity_id(session_factory, "alpha")
    resp = multi_owner_client.post(
        f"/tests/{ident_id}/acknowledge", headers={"referer": "/?owner=AB"}
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/?owner=AB"


def test_bulk_acknowledge_multiple_new_tests(multi_owner_client, session_factory):
    alpha_id = _identity_id(session_factory, "alpha")
    beta_id = _identity_id(session_factory, "beta")
    multi_owner_client.cookies.set("uta_actor", "dana")
    resp = multi_owner_client.post(
        "/tests/bulk/acknowledge",
        data={"identity_ids": [str(alpha_id), str(beta_id)]},
        headers={"referer": "/"},
    )
    assert resp.status_code == 303
    with session_scope(session_factory) as s:
        for ident_id in (alpha_id, beta_id):
            lc = s.scalar(select(TestLifecycle).where(TestLifecycle.test_identity_id == ident_id))
            assert lc.acknowledged is True
            assert lc.acknowledged_by == "dana"


def test_acknowledge_by_signature_route_acks_matching_tests(session_factory):
    from uta.kb.store import record_signatures_for_run

    with session_scope(session_factory) as s:
        r1 = make_run(
            s,
            1,
            {"alpha": "FAILED", "beta": "FAILED"},
            errors={"alpha": ("boom", "Traceback"), "beta": ("boom", "Traceback")},
        )
        apply_run(s, r1, baseline=None)
        record_signatures_for_run(s, r1)
        from uta.web import actions

        sig_id = actions._episode_signature_id(
            s, get_identity(s, "alpha").lifecycle.current_episode
        )

    client = TestClient(create_app(session_factory=session_factory), follow_redirects=False)
    client.cookies.set("uta_actor", "erin")
    resp = client.post(f"/signatures/{sig_id}/acknowledge", headers={"referer": "/"})
    assert resp.status_code == 303
    with session_scope(session_factory) as s:
        for name in ("alpha", "beta"):
            lc = get_identity(s, name).lifecycle
            assert lc.acknowledged is True
            assert lc.acknowledged_by == "erin"


def test_bulk_attribute_sets_triage_status_for_selected(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"alpha": "FAILED", "beta": "FAILED"})
        apply_run(s, r1, baseline=None)
        ep_ids = [
            get_identity(s, "alpha").lifecycle.current_episode_id,
            get_identity(s, "beta").lifecycle.current_episode_id,
        ]

    client = TestClient(create_app(session_factory=session_factory), follow_redirects=False)
    resp = client.post(
        "/episodes/bulk/attribute",
        data={"episode_ids": [str(i) for i in ep_ids], "triage_status": "INVESTIGATING"},
        headers={"referer": "/"},
    )
    assert resp.status_code == 303
    with session_scope(session_factory) as s:
        for name in ("alpha", "beta"):
            ep = get_identity(s, name).lifecycle.current_episode
            assert ep.triage_status == "INVESTIGATING"


# ── instant, self-describing filters (issue #77) ────────────────────────────


def test_triage_filter_controls_auto_submit(multi_owner_client):
    page = multi_owner_client.get("/").text
    # The three selects + the flaky toggle resubmit the GET form on change.
    assert page.count('onchange="this.form.submit()"') == 4


def test_triage_active_filter_chips_render_with_remove_links(multi_owner_client):
    page = multi_owner_client.get("/?owner=AB&flaky=1").text
    assert "owner: AB" in page
    assert "flaky only" in page
    assert 'href="/?flaky=1"' in page  # ✕ on the owner chip keeps the flaky filter
    assert 'href="/?owner=AB"' in page  # ✕ on the flaky chip keeps the owner filter


def test_triage_no_chips_without_filters(multi_owner_client):
    assert "active-filters" not in multi_owner_client.get("/").text


def test_triage_sort_header_links_and_active_marker(multi_owner_client):
    page = multi_owner_client.get("/?owner=AB").text
    assert 'href="/?owner=AB&amp;sort=name"' in page  # Test header applies name sort
    assert 'href="/?owner=AB&amp;sort=owner"' in page  # Owner header applies owner sort
    assert "▲" not in page  # no marker while the age default is active

    sorted_page = multi_owner_client.get("/?owner=AB&sort=name").text
    assert "▲" in sorted_page
    # The active header toggles back to the age default, keeping the filter.
    assert 'href="/?owner=AB"' in sorted_page


def test_triage_sort_persists_through_filter_form(multi_owner_client):
    page = multi_owner_client.get("/?sort=owner").text
    assert '<input type="hidden" name="sort" value="owner">' in page


def test_search_redirects_on_unique_match(multi_owner_client, session_factory):
    ident_id = _identity_id(session_factory, "alpha")
    resp = multi_owner_client.get("/search?q=alpha")
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/tests/{ident_id}"


def test_search_lists_multiple_matches(session_factory):
    with session_scope(session_factory) as s:
        get_identity(s, "ut_a.TestClass.test_alpha_one")
        get_identity(s, "ut_a.TestClass.test_alpha_two")
    client = TestClient(create_app(session_factory=session_factory), follow_redirects=False)
    resp = client.get("/search?q=alpha")
    assert resp.status_code == 200
    assert "test_alpha_one" in resp.text
    assert "test_alpha_two" in resp.text


def test_search_navbar_box_present(client):
    assert 'action="/search"' in client.get("/").text


def test_theme_toggle_present_and_defaults_from_system_preference(client):
    body = client.get("/").text
    assert 'id="theme-toggle"' in body
    # Applied in <head>, before first paint, from localStorage or prefers-color-scheme.
    assert "prefers-color-scheme: dark" in body
    assert 'setAttribute("data-bs-theme", theme)' in body


# ── run-results failures-only filter (issue #63) ────────────────────────────


def test_run_failures_only_filters_results_and_pagination(session_factory, monkeypatch):
    monkeypatch.setenv("UI_ROW_LIMIT", "100")
    with session_scope(session_factory) as s:
        statuses = {f"f{i:04d}": "FAILED" for i in range(120)} | {
            f"p{i:04d}": "PASSED" for i in range(30)
        }
        r1 = make_run(s, 1, statuses)
        apply_run(s, r1, baseline=None)
    client = TestClient(create_app(session_factory=session_factory), follow_redirects=False)

    all_page = client.get("/runs/1").text
    assert "Results (300)" in all_page  # 150 tests x 2 tracks

    failing_page = client.get("/runs/1?failures_only=1").text
    assert "Results (240)" in failing_page  # 120 failing tests x 2 tracks
    assert failing_page.count('<td class="FAILED">') == 100
    assert "checked" in failing_page
    assert 'href="?page=2&amp;failures_only=1#results"' in failing_page
