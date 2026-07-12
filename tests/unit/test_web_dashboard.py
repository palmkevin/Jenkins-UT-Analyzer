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


# ── triage error snippets + trace clamp/copy (issue #145) ──────────────────────

_TRACE_TMPL = (
    "Traceback (most recent call last):\n"
    '  File "/opt/ls/lx/release/permanent/tests/dev/ut_x/mod.py", line 12, in test_t\n'
    "    check()\n"
    "{exc}"
)


@pytest.fixture
def errors_client(session_factory):
    """One new + one acknowledged failing test, both with real error text."""
    with session_scope(session_factory) as s:
        r1 = make_run(
            s,
            1,
            {"alpha": "FAILED", "gamma": "FAILED"},
            errors={
                "alpha": ("test failure", _TRACE_TMPL.format(exc="AssertionError: 7 != 9")),
                "gamma": ("test failure", _TRACE_TMPL.format(exc="KeyError: 'MSH'")),
            },
        )
        apply_run(s, r1, baseline=None)
    client = TestClient(create_app(session_factory=session_factory), follow_redirects=False)
    ident_id = _identity_id(session_factory, "gamma")
    resp = client.post(f"/tests/{ident_id}/acknowledge", headers={"referer": "/"})
    assert resp.status_code == 303
    return client


def test_triage_tables_show_error_snippets(errors_client):
    page = errors_client.get("/").text
    new_idx = page.index('id="new"')
    still_idx = page.index('id="still_failing"')
    fixed_idx = page.index('id="recently_fixed"')
    # New bucket: alpha's exception line as a muted one-liner under the test name.
    assert 'class="error-snippet"' in page[new_idx:still_idx]
    assert "AssertionError: 7 != 9" in page[new_idx:still_idx]
    # Still-failing bucket: gamma's snippet (HTML-escaped quotes around MSH).
    assert 'class="error-snippet"' in page[still_idx:fixed_idx]
    assert "KeyError:" in page[still_idx:fixed_idx]


def test_test_record_trace_has_clamp_hook_and_copy_button(session_factory):
    """The full >15-line trace ships in the HTML (no-JS fallback) with clamp + copy hooks."""
    deep = "\n".join(f"    frame_{i}()" for i in range(20))
    stack = _TRACE_TMPL.format(exc=deep + "\nValueError: bottom of a deep stack")
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"alpha": "FAILED"}, errors={"alpha": ("test failure", stack)})
        apply_run(s, r1, baseline=None)
    client = TestClient(create_app(session_factory=session_factory), follow_redirects=False)
    page = client.get(f"/tests/{_identity_id(session_factory, 'alpha')}").text
    assert 'data-clamp="15"' in page
    assert 'data-copy-target="trace-' in page
    assert "Copy trace" in page
    assert "ValueError: bottom of a deep stack" in page  # full text present pre-clamp
    assert "/static/trace.js" in page  # the clamp/copy behaviour is wired on every page


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


def test_triage_track_filter_keeps_both_track_failure_and_renders_badges(session_factory):
    # Issue #84: "t_both" fails in both tracks (the normal case) — it must show under *either*
    # track filter, with one badge per failing track; "t_py39only" fails in permanent_py39 only.
    with session_scope(session_factory) as s:
        r1 = make_run(
            s,
            1,
            {"t_both": "FAILED", "t_py39only": "FAILED"},
            fail_tracks={"t_py39only": ("permanent_py39",)},
        )
        apply_run(s, r1, baseline=None)
    client = TestClient(create_app(session_factory=session_factory), follow_redirects=False)

    perm = client.get("/?track=permanent").text
    assert "t_both" in perm
    assert "t_py39only" not in perm
    assert "not yet acknowledged (1)" in perm

    py39 = client.get("/?track=permanent_py39").text
    assert "t_both" in py39 and "t_py39only" in py39
    assert "not yet acknowledged (2)" in py39

    # The row lists every failing track as a badge (dropdown options aside, the badge markup is
    # specific to the row rendering).
    assert '<span class="badge track">permanent</span>' in py39
    assert '<span class="badge track">permanent_py39</span>' in py39


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


def test_attribute_by_signature_route_attributes_matching_tests(session_factory):
    from uta.kb.store import record_signatures_for_run
    from uta.web import actions

    with session_scope(session_factory) as s:
        r1 = make_run(
            s,
            1,
            {"alpha": "FAILED", "beta": "FAILED", "gamma": "FAILED"},
            errors={
                "alpha": ("boom", "Traceback"),
                "beta": ("boom", "Traceback"),
                "gamma": ("different", "Traceback"),
            },
        )
        apply_run(s, r1, baseline=None)
        record_signatures_for_run(s, r1)
        sig_id = actions._episode_signature_id(
            s, get_identity(s, "alpha").lifecycle.current_episode
        )
        alpha_ident_id = get_identity(s, "alpha").id

    client = TestClient(create_app(session_factory=session_factory), follow_redirects=False)
    client.cookies.set("uta_actor", "erin")
    resp = client.post(
        f"/signatures/{sig_id}/attribute",
        data={
            "causing_person": "frank",
            "reason_text": "shared outage",
            "triage_status": "ROOT_CAUSED",
            "jira_ticket": "LX-42",
        },
        headers={"referer": f"/tests/{alpha_ident_id}"},
    )
    # Post/Redirect/Get: bounce back to the page the form was submitted from.
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/tests/{alpha_ident_id}"
    with session_scope(session_factory) as s:
        for name in ("alpha", "beta"):
            ep = get_identity(s, name).lifecycle.current_episode
            assert ep.triage_status == "ROOT_CAUSED"
            assert ep.jira_ticket == "LX-42"
            assert ep.attribution.causing_person == "frank"
            assert ep.attribution.reason_text == "shared outage"
            assert ep.attribution.validated_by == "erin"
        gamma_ep = get_identity(s, "gamma").lifecycle.current_episode
        assert gamma_ep.triage_status == "UNTRIAGED"
        assert gamma_ep.attribution is None


def test_signature_wide_attribute_button_renders_only_for_shared_signatures(session_factory):
    from uta.kb.store import record_signatures_for_run

    with session_scope(session_factory) as s:
        r1 = make_run(
            s,
            1,
            {"alpha": "FAILED", "beta": "FAILED", "gamma": "FAILED"},
            errors={
                "alpha": ("boom", "Traceback"),
                "beta": ("boom", "Traceback"),
                "gamma": ("different", "Traceback"),
            },
        )
        apply_run(s, r1, baseline=None)
        record_signatures_for_run(s, r1)
    client = TestClient(create_app(session_factory=session_factory), follow_redirects=False)

    # alpha's signature also afflicts beta → the second submit button offers the bulk apply.
    alpha_page = client.get(f"/tests/{_identity_id(session_factory, 'alpha')}").text
    assert "Apply to all 2 affected tests with this signature" in alpha_page
    assert 'formaction="/signatures/' in alpha_page
    # gamma's failure is unique → per-episode Save only.
    gamma_page = client.get(f"/tests/{_identity_id(session_factory, 'gamma')}").text
    assert "affected tests with this signature" not in gamma_page
    assert 'formaction="/signatures/' not in gamma_page


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


@pytest.fixture
def both_buckets_page(session_factory):
    """Triage page with both bulk tables rendered: alpha acknowledged (still failing), beta new."""
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"alpha": "FAILED", "beta": "FAILED"})
        apply_run(s, r1, baseline=None)
    client = TestClient(create_app(session_factory=session_factory), follow_redirects=False)
    alpha_id = _identity_id(session_factory, "alpha")
    resp = client.post(f"/tests/{alpha_id}/acknowledge", headers={"referer": "/"})
    assert resp.status_code == 303
    return client.get("/").text


def test_bulk_selection_hooks_present_in_both_tables(both_buckets_page):
    """The JS contract (issue #76): select-all header checkbox and per-row data hooks, per table."""
    page = both_buckets_page
    for form_id in ("bulk-ack-new", "bulk-attr-still"):
        assert f'data-bulk-select-all="{form_id}"' in page
        assert f'data-bulk-item="{form_id}"' in page
    # The behaviour script itself is wired into the page.
    assert '<script src="/static/bulk-select.js" defer></script>' in page


def test_bulk_buttons_render_disabled_with_count_hooks(both_buckets_page):
    """Bulk buttons ship disabled (zero selected) and carry the live-count label hooks."""
    import re

    for form_id, label in (
        ("bulk-ack-new", "Acknowledge selected"),
        ("bulk-attr-still", "Apply to selected"),
    ):
        m = re.search(rf'<button[^>]*data-bulk-button="{form_id}"[^>]*>', both_buckets_page)
        assert m, f"no bulk button for {form_id}"
        assert "disabled" in m.group(0)
        assert f'data-bulk-label="{label}"' in m.group(0)


def test_bulk_select_js_is_served(session_factory):
    client = TestClient(create_app(session_factory=session_factory))
    resp = client.get("/static/bulk-select.js")
    assert resp.status_code == 200
    assert "data-bulk-select-all" in resp.text
    assert "indeterminate" in resp.text


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


# ── orientation polish: active nav, triage badge, relative times (issue #79) ──


def test_nav_marks_each_section_active(client):
    for href in ("/runs", "/flaky", "/kb", "/control"):
        page = client.get(href).text
        assert f'class="nav-link active" aria-current="page" href="{href}"' in page
        # Triage (and only the current section) is not marked.
        assert 'aria-current="page" href="/">Triage' not in page


def test_nav_triage_active_on_queue_and_test_record(client, seeded):
    assert 'class="nav-link active" aria-current="page" href="/">Triage' in client.get("/").text
    ident_id = _identity_id(seeded, "alpha")
    page = client.get(f"/tests/{ident_id}").text
    assert 'class="nav-link active" aria-current="page" href="/">Triage' in page
    assert 'aria-current="page" href="/runs"' not in page


def test_nav_search_page_highlights_nothing(client):
    page = client.get("/search?q=zzz-no-such-test").text
    assert "nav-link active" not in page
    assert "aria-current" not in page


def test_nav_section_boundaries():
    from uta.web.app import nav_section

    assert nav_section("/") == "triage"
    assert nav_section("/tests/42") == "triage"
    assert nav_section("/runs") == "runs"
    assert nav_section("/runs/1702") == "runs"
    assert nav_section("/search") is None


def test_triage_badge_shows_new_count_on_every_page(client):
    # One unacknowledged new failing test ("alpha") → a red 1 on the Triage nav link everywhere.
    for path in ("/", "/runs", "/flaky", "/kb", "/control"):
        page = client.get(path).text
        assert "text-bg-danger" in page
        assert ">1</span>" in page


def test_triage_badge_ignores_queue_filters(multi_owner_client):
    # The badge is the live global count, not the filtered view's.
    page = multi_owner_client.get("/?owner=AB").text
    assert ">2</span>" in page


def test_triage_badge_hidden_at_zero(client, seeded):
    ident_id = _identity_id(seeded, "alpha")
    client.post(f"/tests/{ident_id}/acknowledge", headers={"referer": "/"})
    page = client.get("/").text
    assert "text-bg-danger" not in page


def test_triage_and_test_record_times_render_relative_with_absolute_title(session_factory):
    # Triage "First failed" column and the test-record lifecycle/episode times use |reltime.
    from datetime import UTC, datetime, timedelta

    started = datetime.now(UTC) - timedelta(hours=3, minutes=1)
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"alpha": "FAILED"}, started_at=started)
        apply_run(s, r1, baseline=None)
    client = TestClient(create_app(session_factory=session_factory), follow_redirects=False)
    queue = client.get("/").text
    assert "3 h ago</span>" in queue
    assert f'<span title="{started.strftime("%Y-%m-%d %H:%M")}' in queue  # absolute on hover
    record = client.get(f"/tests/{_identity_id(session_factory, 'alpha')}").text
    assert "3 h ago</span>" in record
    assert f'<span title="{started.strftime("%Y-%m-%d %H:%M")}' in record


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
