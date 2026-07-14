"""Read-side view builders for the dashboard (triage queue, per-test record, run summary).

Every function takes a live session and returns **plain detached dicts** so Jinja templates never
touch a closed session (the Slice-0 pattern). Nothing here mutates state — the buckets are a pure
**projection** of lifecycle state + the orthogonal acknowledgement attribute, so no separate
bookkeeping exists to drift.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Collection, Sequence
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from math import ceil
from urllib.parse import urlencode

from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session, joinedload

from uta.analyze.baseline import compute_diff, identity_status_maps, select_baseline
from uta.analyze.flakiness import compute_stats
from uta.analyze.flakiness import history as _test_history
from uta.analyze.flakiness import leaderboard_candidates as _leaderboard_candidates
from uta.analyze.relevance import rank_candidates
from uta.control.heartbeat import read_heartbeat
from uta.ingest.ut_report import FAILED_STATUSES
from uta.kb.retrieval import similar_cases
from uta.kb.signature import display_message
from uta.models import (
    Classification,
    FailureEpisode,
    FailureSignature,
    Run,
    TestIdentity,
    TestLifecycle,
    TestResult,
)
from uta.models.enums import LifecycleState
from uta.web import charts
from uta.web.actions import _error_key, open_episodes_for_signature

# Default max rows a dashboard section renders before it is capped behind a "Load all N Tests" link.
# Mirrors ``Settings.ui_row_limit``; kept here so the view layer has a sane default when called
# directly (tests, CLI). A limit of 0 disables the cap.
DEFAULT_ROW_LIMIT = 100

# Max tests a run-page diff bucket lists inline before capping behind a "Show all N" link
# (issue #151). Deliberately tighter than DEFAULT_ROW_LIMIT — each bucket renders as a single
# comma-separated link stream, not a table, so a bad night's hundreds of regressions would
# otherwise swamp the page.
DIFF_ROW_LIMIT = 20

# Max characters of the one-line error snippet a triage row shows (issue #145) — long enough for a
# typical exception line, short enough that a row stays a row.
_SNIPPET_MAX_CHARS = 160


def _error_snippet(
    error_type: str | None, error_details: str | None, error_stack_trace: str | None
) -> str | None:
    """One display line summarising a failure for the triage tables (issue #145).

    Prefers the traceback's closing exception line (``AssertionError: …``) via
    :func:`display_message` — the JUnit ``errorDetails`` field is usually the constant
    "test failure" — falling back to the first non-blank line of the details, then to the derived
    error type. Truncated to :data:`_SNIPPET_MAX_CHARS` with an ellipsis.
    """
    message = display_message(error_details, error_stack_trace)
    first = next((ln.strip() for ln in (message or "").splitlines() if ln.strip()), "")
    if len(first) > _SNIPPET_MAX_CHARS:
        first = first[: _SNIPPET_MAX_CHARS - 1].rstrip() + "…"
    return first or error_type or None


def _now() -> datetime:
    return datetime.now(UTC)


def _cap(rows: Sequence, section: str, *, limit: int, expand: Collection[str]) -> list:
    """Truncate a section's rows to ``limit`` unless the caller asked to ``expand`` it.

    Returns a plain list (a slice, so the original is untouched). ``limit <= 0`` disables the cap.
    Callers keep the pre-cap length around as the section total so the template can render the
    "Load all N Tests" hint (issue #19 — long lists were rendered in full and hurt responsiveness).
    """
    rows = list(rows)
    if limit <= 0 or section in expand or len(rows) <= limit:
        return rows
    return rows[:limit]


def _aware(dt: datetime | None) -> datetime | None:
    """Coerce to aware-UTC. SQLite (offline tests) drops tzinfo; Postgres keeps it — normalize so
    comparisons against :func:`_now` never mix naive and aware datetimes."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _page_window(total: int, *, limit: int, page: int) -> tuple[int, int, int | None]:
    """Clamp a 1-based ``page`` against ``total`` rows → ``(page, pages, offset)``.

    ``limit <= 0`` disables pagination (one all-rows page, ``offset=None``); an out-of-range page
    clamps to the nearest valid one so a stale link never 500s or renders an empty table.
    """
    if limit <= 0:
        return 1, 1, None
    pages = max(1, ceil(total / limit))
    page = min(max(1, page), pages)
    return page, pages, (page - 1) * limit


def _run_ref(session: Session, run_id: int | None) -> dict | None:
    """A minimal {id, build, url} reference to a run (episodes hold only the FK)."""
    if run_id is None:
        return None
    run = session.get(Run, run_id)
    if run is None:
        return None
    return {"id": run.id, "build": run.build_number, "url": run.url}


def _run_refs(session: Session, run_ids: Collection[int]) -> dict[int, dict]:
    """Batch variant of :func:`_run_ref` — one query for many ids (triage N+1 fix, issue #52)."""
    ids = {i for i in run_ids if i is not None}
    if not ids:
        return {}
    rows = session.execute(select(Run.id, Run.build_number, Run.url).where(Run.id.in_(ids))).all()
    return {run_id: {"id": run_id, "build": build, "url": url} for run_id, build, url in rows}


def latest_run(session: Session) -> dict | None:
    """The most recent run we hold, as ``{build, url, started_at}`` (or ``None`` on an empty store).

    Newest-first by ``started_at`` then ``id`` — the same ordering :func:`job_runs` uses, so the
    Triage header and the Runs list never disagree about which build is latest.
    """
    run = session.scalar(select(Run).order_by(Run.started_at.desc(), Run.id.desc()).limit(1))
    if run is None:
        return None
    return {"build": run.build_number, "url": run.url, "started_at": run.started_at}


def _failure_infos(
    session: Session, episodes: Collection[FailureEpisode]
) -> dict[int, dict | None]:
    """Batch variant of the failure-detail lookup, projected down to
    ``{tracks, signature_id, error_type, error_details, error_stack_trace}``.

    Used by the triage queue to filter/display by track, to surface the "acknowledge all with
    this signature" bulk action, and to render the per-row error snippet (issue #145) — one query
    for every episode's characterising failure instead of one per row.

    ``tracks`` carries **every** failing track of the ``(identity, run)`` pair — a test normally
    runs in both tracks, so failing in both is the common case, and collapsing to one row's track
    made the exact track filter hide genuinely failing tests (issue #84). ``signature_id`` is the
    first failing row's (track order): the normalizer strips the track prefix, so both tracks'
    failures hash to the same signature in practice — and the bulk action matches on the
    signature's error *text*, not its id, so any one of the pair's signatures anchors it equally.
    The error fields come from the first row carrying any error text (same anchor rule) — the
    signature normalizer likewise treats both tracks' error text as the same failure.
    """
    pairs = {
        (ep.test_identity_id, ep.last_failing_run_id or ep.first_failure_run_id) for ep in episodes
    }
    pairs.discard((None, None))
    if not pairs:
        return {}
    rows = session.execute(
        select(
            TestResult.test_identity_id,
            TestResult.run_id,
            TestResult.track,
            TestResult.signature_id,
            TestResult.error_type,
            TestResult.error_details,
            TestResult.error_stack_trace,
        )
        .where(
            tuple_(TestResult.test_identity_id, TestResult.run_id).in_(pairs),
            TestResult.status.in_(FAILED_STATUSES),
        )
        .order_by(TestResult.track, TestResult.id)
    ).all()
    by_pair: dict[tuple[int, int], dict] = {}
    for identity_id, run_id, track, signature_id, error_type, details, stack in rows:
        info = by_pair.setdefault(
            (identity_id, run_id),
            {
                "tracks": [],
                "signature_id": None,
                "error_type": None,
                "error_details": None,
                "error_stack_trace": None,
            },
        )
        info["tracks"].append(track)
        if info["signature_id"] is None:
            info["signature_id"] = signature_id
        if info["error_type"] is None:
            info["error_type"] = error_type
        if (
            info["error_details"] is None
            and info["error_stack_trace"] is None
            and (details or stack)
        ):
            info["error_details"] = details
            info["error_stack_trace"] = stack
    return {
        ep.id: by_pair.get((ep.test_identity_id, ep.last_failing_run_id or ep.first_failure_run_id))
        for ep in episodes
    }


def _signature_ack_counts(
    session: Session, signature_ids: Collection[int | None]
) -> dict[int, int]:
    """Blast radius per signature for the "Ack all w/ signature (N)" button (issue #152).

    Signatures are **per-test** (identity is part of the hash), so grouping by ``signature_id``
    would always count 1 — the real cross-test grouping key is the exception type + message with
    the stack-frame lines stripped (:func:`uta.web.actions._error_key`), the same computation
    :func:`uta.web.actions.acknowledge_by_signature` performs at commit time. Callers pass the New
    bucket's (unacknowledged, failing) rows' signature ids — the same scope the bulk action
    targets — so each signature's count *is* the number of tests one click would acknowledge.
    One batched query for the normalized texts, grouping in Python: the queue projection stays
    O(1) queries in the number of rows (issue #52).
    """
    ids = [i for i in signature_ids if i is not None]
    if not ids:
        return {}
    keys = {
        sig_id: _error_key(text)
        for sig_id, text in session.execute(
            select(FailureSignature.id, FailureSignature.normalized_text).where(
                FailureSignature.id.in_(set(ids))
            )
        )
    }
    counts = Counter(keys[i] for i in ids if i in keys)
    return {sig_id: counts[key] for sig_id, key in keys.items()}


def _latest_classification(session: Session, episode_id: int) -> Classification | None:
    """The current prediction for an episode (rows are append-only; newest wins)."""
    return session.scalar(
        select(Classification)
        .where(Classification.episode_id == episode_id)
        .order_by(Classification.created_at.desc(), Classification.id.desc())
        .limit(1)
    )


def _latest_classifications(
    session: Session, episode_ids: Collection[int]
) -> dict[int, Classification]:
    """The current (newest) classification per episode, in **one query** for many episodes.

    Rows are read oldest-first and written into the map, so the last write per episode is the
    newest row — the same "newest wins" rule as :func:`_latest_classification`. Classifications
    per episode are few (one per analysing run), so reading them all beats N per-episode queries.
    """
    ids = {i for i in episode_ids if i is not None}
    if not ids:
        return {}
    latest: dict[int, Classification] = {}
    for classification in session.scalars(
        select(Classification)
        .where(Classification.episode_id.in_(ids))
        .order_by(Classification.created_at, Classification.id)
    ):
        latest[classification.episode_id] = classification
    return latest


def _days_between(start: datetime | None, end: datetime | None) -> int | None:
    start, end = _aware(start), _aware(end)
    if start is None or end is None:
        return None
    return max(0, (end - start).days)


def _duration_seconds(start: datetime | None, end: datetime | None) -> float | None:
    start, end = _aware(start), _aware(end)
    if start is None or end is None:
        return None
    return max(0.0, (end - start).total_seconds())


def _row(
    lc: TestLifecycle,
    *,
    classifications: dict[int, Classification],
    run_refs: dict[int, dict],
    failure_infos: dict[int, dict | None],
) -> dict:
    """Shared row projection for the triage buckets — identity + current episode + prediction.

    A pure projection over **prefetched** data: the lifecycle arrives with its identity, current
    episode and attribution eager-loaded, and the classification/run/failure lookups are batch
    maps — so building a row issues no queries (the page is O(1) queries in the number of rows,
    issue #52).
    """
    ident = lc.identity
    ep = lc.current_episode
    classification = classifications.get(ep.id) if ep is not None else None
    attribution = ep.attribution if ep is not None else None
    first_failure = run_refs.get(ep.first_failure_run_id) if ep is not None else None
    fixed_in = run_refs.get(ep.fixed_in_run_id) if ep is not None else None
    failure_info = failure_infos.get(ep.id) if ep is not None else None
    return {
        "identity_id": ident.id,
        "test_id": ident.canonical_name,
        "suite": ident.suite,
        "owner": ident.main_developer,
        # Pivot links (issue #157): the row's plain facts double as filters on the queue itself.
        "owner_url": pivot_url("owner", ident.main_developer),
        "cause_url": pivot_url("cause", classification.predicted_cause if classification else None),
        "state": lc.state,
        "flaky": lc.flaky,
        "reopen_count": lc.reopen_count,
        "acknowledged": lc.acknowledged,
        "acknowledged_by": lc.acknowledged_by,
        "acknowledged_at": lc.acknowledged_at,
        "episode_id": ep.id if ep is not None else None,
        "first_failure": first_failure,
        "first_failure_at": ep.first_failure_at if ep is not None else None,
        "fixed_in": fixed_in,
        "fixed_at": ep.fixed_at if ep is not None else None,
        "age_runs": ep.age_runs if ep is not None else None,
        "age_days": _days_between(ep.first_failure_at, _now()) if ep is not None else None,
        "triage_status": ep.triage_status if ep is not None else None,
        "predicted_cause": classification.predicted_cause if classification else None,
        "causing_person": attribution.causing_person if attribution else None,
        "reason_text": attribution.reason_text if attribution else None,
        "tracks": failure_info["tracks"] if failure_info else [],
        "signature_id": failure_info["signature_id"] if failure_info else None,
        "error_type": failure_info["error_type"] if failure_info else None,
        "error_snippet": _error_snippet(
            failure_info["error_type"],
            failure_info["error_details"],
            failure_info["error_stack_trace"],
        )
        if failure_info
        else None,
    }


def _matches_filters(row: dict, filters: dict[str, str]) -> bool:
    """Whether a projected triage row passes the query-param filter set.

    Text filters (``owner``/``suite``) are case-insensitive substring matches; ``track`` matches
    when **any** failing track equals it (a test failing in both tracks must show under either
    filter — issue #84); ``cause``/``triage_status`` are exact; ``flaky`` is a truthy toggle. An
    absent or empty filter value never excludes a row.
    """
    owner = filters.get("owner", "").strip().lower()
    if owner and owner not in (row["owner"] or "").lower():
        return False
    suite = filters.get("suite", "").strip().lower()
    if suite and suite not in (row["suite"] or "").lower():
        return False
    track = filters.get("track", "").strip()
    if track and track not in row["tracks"]:
        return False
    cause = filters.get("cause", "").strip()
    if cause and row["predicted_cause"] != cause:
        return False
    triage_status = filters.get("triage_status", "").strip()
    if triage_status and row["triage_status"] != triage_status:
        return False
    if filters.get("flaky") and not row["flaky"]:
        return False
    return True


_SORT_KEYS = {
    "name": lambda r: (r["test_id"] or "").lower(),
    "owner": lambda r: (r["owner"] or "").lower(),
}


def _sort_rows(rows: list[dict], sort: str | None, *, age_key) -> None:
    """Sort a bucket in place: ``name``/``owner`` ascending, else the bucket's own age order."""
    key = _SORT_KEYS.get(sort or "")
    if key is not None:
        rows.sort(key=key)
    else:
        rows.sort(key=age_key, reverse=True)


# Chip display names for the triage filter params (issue #77). ``flaky`` is special-cased —
# it's a toggle, so its chip is a fixed phrase rather than "key: value".
_CHIP_LABELS = {
    "owner": "owner",
    "suite": "suite",
    "track": "track",
    "cause": "cause",
    "triage_status": "status",
}


def triage_url(filters: dict[str, str], sort: str | None, expand: Collection[str] = ()) -> str:
    """The triage-queue URL encoding the given filter set + sort + expanded sections — the
    shareable state."""
    params = {k: v for k, v in filters.items() if v}
    if sort:
        params["sort"] = sort
    if expand:
        params["expand"] = ",".join(expand)
    query = urlencode(params, safe=",")
    return f"/?{query}" if query else "/"


def pivot_url(key: str, value: str | None) -> str | None:
    """The triage-queue URL filtered on just this **one** value (issue #157) — the pivot behind a
    clickable owner / suite / predicted-cause fact.

    Single-filter by design: clicking an owner anywhere means "show me everything of this owner",
    not "add this owner to my current view" — so the URL never inherits the page's other filters.
    ``None`` for an empty value, so templates fall back to the plain-text placeholder.
    """
    if not value:
        return None
    return triage_url({key: str(value)}, None)


def triage_filter_chips(
    filters: dict[str, str], sort: str | None = None, expand: Collection[str] = ()
) -> list[dict]:
    """Active-filter chips for the triage queue (issue #77) — pure URL construction.

    One chip per active filter: a ``label`` ("owner: KP", "flaky only") and a ``remove_url``
    re-requesting the page with that one filter dropped and everything else (including ``sort``
    and the ``expand``-ed sections, issue #151) kept, so state stays entirely in the URL.
    """
    chips = []
    for key, name in _CHIP_LABELS.items():
        value = (filters.get(key) or "").strip()
        if not value:
            continue
        remaining = {k: v for k, v in filters.items() if k != key}
        chips.append(
            {
                "key": key,
                "label": f"{name}: {value}",
                "remove_url": triage_url(remaining, sort, expand),
            }
        )
    if filters.get("flaky"):
        remaining = {k: v for k, v in filters.items() if k != "flaky"}
        chips.append(
            {
                "key": "flaky",
                "label": "flaky only",
                "remove_url": triage_url(remaining, sort, expand),
            }
        )
    return chips


def triage_sort_links(
    filters: dict[str, str], sort: str | None = None, expand: Collection[str] = ()
) -> dict[str, dict]:
    """Column-header sort links for the triage queue (issue #77).

    For each server-supported sort (``name``/``owner``) returns ``{"active": bool, "url": str}``:
    clicking an inactive header applies that sort, clicking the active one toggles back to the
    default age order. Filters and the ``expand``-ed sections (issue #151) are preserved either
    way.
    """
    return {
        key: {
            "active": (sort or "") == key,
            "url": triage_url(filters, None if (sort or "") == key else key, expand),
        }
        for key in _SORT_KEYS
    }


# The triage queue's three capped buckets — the section keys ``?expand=`` accepts (issue #19).
_TRIAGE_SECTIONS = ("new", "still_failing", "recently_fixed")


def triage_expand_urls(
    filters: dict[str, str], sort: str | None = None, expand: Collection[str] = ()
) -> dict[str, str]:
    """Per-section "Load all N Tests" URLs for the triage queue's capped buckets (issue #19).

    Each URL re-requests the page with that section added to the already-expanded set while
    keeping every active filter and the sort — the same state-stays-in-the-URL contract as the
    chips and header sort links (issue #77) — and jumps back to the section's anchor.
    """
    urls = {}
    for section in _TRIAGE_SECTIONS:
        expanded = list(expand)
        if section not in expanded:
            expanded.append(section)
        urls[section] = triage_url(filters, sort, expand=expanded) + f"#{section}"
    return urls


# The run page's four capped diff buckets — the section keys its ``?expand=`` accepts (issue #151).
_RUN_DIFF_SECTIONS = ("regressions", "newly_fixed", "still_failing", "removed")


def run_expand_urls(
    build: int, params: dict[str, str], expand: Collection[str] = ()
) -> dict[str, str]:
    """Per-bucket "Show all N" URLs for the run page's capped diff lists (issue #151).

    Each URL re-requests the run page with that bucket added to the already-expanded set while
    the rest of the query string (``failures_only``, results pagination) survives — the same
    state-stays-in-the-URL contract as the triage queue's expand links (issue #132) — and jumps
    back to the ``#diff`` anchor.
    """
    base = {k: v for k, v in params.items() if k != "expand" and v}
    urls = {}
    for section in _RUN_DIFF_SECTIONS:
        expanded = list(expand)
        if section not in expanded:
            expanded.append(section)
        query = urlencode({**base, "expand": ",".join(expanded)}, safe=",")
        urls[section] = f"/runs/{build}?{query}#diff"
    return urls


def triage_filter_options(session: Session) -> dict:
    """Distinct owner/suite values in play, for the triage filter bar's dropdowns.

    Suites come from identities that currently have a lifecycle row (irrelevant identities never
    show up in any bucket); owners likewise. Cheap, small-cardinality scans.
    """
    owners = sorted(
        {
            o
            for o in session.scalars(
                select(TestIdentity.main_developer)
                .join(TestLifecycle, TestLifecycle.test_identity_id == TestIdentity.id)
                .distinct()
            ).all()
            if o
        }
    )
    suites = sorted(
        {
            s
            for s in session.scalars(
                select(TestIdentity.suite)
                .join(TestLifecycle, TestLifecycle.test_identity_id == TestIdentity.id)
                .distinct()
            ).all()
            if s
        }
    )
    return {"owners": owners, "suites": suites}


def new_failing_count(session: Session) -> int:
    """The number of unacknowledged NEW failing tests — the triage queue's "new" bucket size.

    The same predicate :func:`triage_queue` uses for its first bucket (``FAILING`` and not
    acknowledged), as a single COUNT so the navbar badge (issue #79) can show it on every page
    without building the whole queue projection.
    """
    return session.scalar(
        select(func.count())
        .select_from(TestLifecycle)
        .where(
            TestLifecycle.state == LifecycleState.FAILING,
            TestLifecycle.acknowledged.is_(False),
        )
    )


def triage_queue(
    session: Session,
    *,
    recently_fixed_days: int = 7,
    limit: int = DEFAULT_ROW_LIMIT,
    expand: Collection[str] = (),
    filters: dict[str, str] | None = None,
    sort: str | None = None,
) -> dict:
    """The three-bucket triage queue: new-unacknowledged / still-failing(+removed) / recently-fixed.

    Buckets are a projection of lifecycle ``state`` and the orthogonal ``acknowledged`` attribute:

    1. **New** — ``FAILING`` and not acknowledged (newest-first); the action queue.
    2. **Still failing** — ``FAILING`` and acknowledged, plus ``REMOVED`` tests with an open
       episode surfaced with a Removed flag (disappeared ≠ fixed).
    3. **Recently fixed** — ``FIXED`` within the configured window (default 7 days).

    ``filters`` (issue #63) narrows every bucket by owner/suite/track/predicted cause/triage
    status/flaky before capping — query params, so the view stays server-rendered and bookmarkable.
    ``sort`` reorders each bucket by ``name``/``owner``; any other value (including ``None``) keeps
    each bucket's natural age-based order.

    Each bucket is capped at ``limit`` rows for rendering (long lists hurt UI responsiveness —
    issue #19); ``counts`` reflects the full, post-filter, pre-cap size, and a section named in
    ``expand`` renders in full. ``truncated`` reports, per bucket, whether rows were dropped.

    Query count is **O(1) in the number of rows** (issue #52): one eager-loaded lifecycle scan
    (identity + current episode + attribution), one batched latest-classification lookup, one
    batched run-ref lookup, one batched failure-info (track/signature) lookup, and one batched
    signature-text lookup for the New rows' ack blast radius (issue #152).
    """
    filters = filters or {}
    lifecycles = (
        session.scalars(
            select(TestLifecycle).options(
                joinedload(TestLifecycle.identity),
                joinedload(TestLifecycle.current_episode).joinedload(FailureEpisode.attribution),
            )
        )
        .unique()
        .all()
    )

    # Pass 1 — bucket selection only; projection is deferred until the batch maps exist.
    selected: list[tuple[str, TestLifecycle]] = []
    cutoff = _now() - timedelta(days=recently_fixed_days)
    for lc in lifecycles:
        ep = lc.current_episode
        if lc.state == LifecycleState.FAILING:
            selected.append(("still_failing" if lc.acknowledged else "new", lc))
        elif lc.state == LifecycleState.REMOVED and ep is not None and ep.is_open:
            selected.append(("removed", lc))
        elif lc.state == LifecycleState.FIXED and ep is not None and ep.fixed_at is not None:
            if _aware(ep.fixed_at) >= cutoff:
                selected.append(("recently_fixed", lc))

    # Pass 2 — batch-fetch everything the rows reference, then project (no per-row queries).
    episodes = [lc.current_episode for _, lc in selected if lc.current_episode is not None]
    classifications = _latest_classifications(session, [ep.id for ep in episodes])
    run_refs = _run_refs(
        session,
        [ep.first_failure_run_id for ep in episodes] + [ep.fixed_in_run_id for ep in episodes],
    )
    failure_infos = _failure_infos(session, episodes)
    # Blast radius for the New rows' "Ack all w/ signature (N)" button (issue #152) — grouped over
    # the *whole* pre-filter, pre-cap New bucket, because the bulk action acknowledges every
    # matching test regardless of the current view's filters or row cap.
    signature_ack_counts = _signature_ack_counts(
        session,
        [
            (failure_infos.get(lc.current_episode.id) or {}).get("signature_id")
            for bucket, lc in selected
            if bucket == "new" and lc.current_episode is not None
        ],
    )

    new: list[dict] = []
    still_failing: list[dict] = []
    recently_fixed: list[dict] = []
    for bucket, lc in selected:
        row = _row(
            lc, classifications=classifications, run_refs=run_refs, failure_infos=failure_infos
        )
        if not _matches_filters(row, filters):
            continue
        if bucket == "new":
            row["signature_ack_count"] = signature_ack_counts.get(row["signature_id"], 0)
            new.append(row)
        elif bucket == "still_failing":
            still_failing.append(row)
        elif bucket == "removed":
            row["removed"] = True
            still_failing.append(row)
        else:
            recently_fixed.append(row)

    _sort_rows(
        new, sort, age_key=lambda r: (r["first_failure_at"] is not None, r["first_failure_at"])
    )
    _sort_rows(still_failing, sort, age_key=lambda r: (r.get("removed", False), r["age_days"] or 0))
    _sort_rows(recently_fixed, sort, age_key=lambda r: (r["fixed_at"] is not None, r["fixed_at"]))

    counts = {
        "new": len(new),
        "still_failing": len(still_failing),
        "recently_fixed": len(recently_fixed),
    }
    new = _cap(new, "new", limit=limit, expand=expand)
    still_failing = _cap(still_failing, "still_failing", limit=limit, expand=expand)
    recently_fixed = _cap(recently_fixed, "recently_fixed", limit=limit, expand=expand)

    return {
        "new": new,
        "still_failing": still_failing,
        "recently_fixed": recently_fixed,
        "counts": counts,
        "truncated": {
            "new": len(new) < counts["new"],
            "still_failing": len(still_failing) < counts["still_failing"],
            "recently_fixed": len(recently_fixed) < counts["recently_fixed"],
        },
    }


def _episode_failure_detail(session: Session, ep: FailureEpisode) -> dict | None:
    """The error detail for a single episode — the latest failing result *within* that episode.

    Scoped to the episode's last-failing run (falling back to its first-failure run when the
    episode has no recorded last-failing run yet), so each episode card shows the failure that
    characterises it. Mirrors the fields :func:`_latest_failing_result` surfaced for the (now
    removed) single "Latest failure" section.
    """
    run_id = ep.last_failing_run_id or ep.first_failure_run_id
    if run_id is None:
        return None
    result = session.scalar(
        select(TestResult)
        .where(
            TestResult.test_identity_id == ep.test_identity_id,
            TestResult.run_id == run_id,
            TestResult.status.in_(FAILED_STATUSES),
        )
        .order_by(TestResult.id.desc())
        .limit(1)
    )
    if result is None:
        return None
    return {
        "track": result.track,
        "status": result.status,
        "error_type": result.error_type,
        "error_details": result.error_details,
        "error_stack_trace": result.error_stack_trace,
        "file_path": result.file_path,
        "line": result.line,
        "run": _run_ref(session, result.run_id),
    }


def _fmt_num(value) -> str:
    """Compact number rendering for evidence values (``3.0`` -> ``3``, ``0.5`` -> ``0.5``)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return str(value)
    return f"{value:g}"


def _top_match_line(top: dict) -> str:
    """One readable line for the classifier's strongest match of a kind (see ``_top_evidence``)."""
    line = str(top.get("candidate") or "—")
    if top.get("author"):
        line += f" by {top['author']}"
    if top.get("score") is not None:
        line += f" (score {_fmt_num(top['score'])})"
    reasons = top.get("reasons") or []
    if isinstance(reasons, list) and reasons:
        line += " — " + "; ".join(str(r) for r in reasons)
    return line


def _evidence_items(evidence) -> list[tuple[str, str]]:
    """Flatten the classifier's evidence JSON into readable (label, value) rows for the record.

    Whitelists the user-meaningful keys of the shape :func:`uta.analyze.classify.classify_episode`
    persists (candidate counts, relevance matches, the tie-break, the confidence inputs) and drops
    internal noise (``baseline_run_id`` is a store PK, not a build number). Degenerate payloads —
    a bare string or list instead of the expected dict — are still surfaced as a single row rather
    than silently hidden.
    """
    if not evidence:
        return []
    if not isinstance(evidence, dict):
        if isinstance(evidence, list):
            return [("Evidence", "; ".join(str(v) for v in evidence))]
        return [("Evidence", str(evidence))]
    relevance = evidence.get("relevance")
    if not isinstance(relevance, dict):
        relevance = {}
    items: list[tuple[str, str]] = []
    if "infra_error" in evidence:
        items.append(("Infrastructure error", "yes" if evidence["infra_error"] else "no"))
    for kind, label in (("code", "Code changes in window"), ("data", "Data changes in window")):
        if f"{kind}_candidates" not in evidence:
            continue
        count = evidence[f"{kind}_candidates"] or 0
        if not count:
            items.append((label, "none"))
            continue
        value = f"{_fmt_num(count)} candidate{'s' if count != 1 else ''}"
        matched = relevance.get(f"{kind}_matched")
        if matched is not None:
            value += f" · {_fmt_num(matched)} matched this test"
        items.append((label, value))
    for key, label in (("top_code", "Top code match"), ("top_data", "Top data match")):
        top = relevance.get(key)
        if isinstance(top, dict):
            items.append((label, _top_match_line(top)))
    tie = relevance.get("tie_break")
    if tie:
        items.append(
            ("Tie-break", f"both kinds matched — the top {tie} candidate led by a full tier")
        )
    conf = evidence.get("confidence")
    if isinstance(conf, dict):
        bits = []
        if conf.get("win_score") is not None and conf.get("lose_score") is not None:
            bits.append(
                f"relevance score {_fmt_num(conf['win_score'])} vs {_fmt_num(conf['lose_score'])}"
            )
        if conf.get("kb_provenance_weight") is not None:
            bits.append(f"KB provenance weight {_fmt_num(conf['kb_provenance_weight'])}")
        if bits:
            items.append(("Confidence inputs", " · ".join(bits)))
    return items


def _episode_dict(session: Session, ep: FailureEpisode) -> dict:
    classification = _latest_classification(session, ep.id)
    attribution = ep.attribution
    evidence = None
    if classification and classification.evidence:
        try:
            evidence = json.loads(classification.evidence)
        except (ValueError, TypeError):
            evidence = None
    return {
        "id": ep.id,
        "episode_number": ep.episode_number,
        "is_open": ep.is_open,
        "first_failure": _run_ref(session, ep.first_failure_run_id),
        "first_failure_at": ep.first_failure_at,
        "last_failing": _run_ref(session, ep.last_failing_run_id),
        "last_failing_at": ep.last_failing_at,
        "fixed_in": _run_ref(session, ep.fixed_in_run_id),
        "fixed_at": ep.fixed_at,
        "age_runs": ep.age_runs,
        "age_days": _days_between(ep.first_failure_at, ep.fixed_at or _now()),
        "triage_status": ep.triage_status,
        "jira_ticket": ep.jira_ticket,
        "predicted_cause": classification.predicted_cause if classification else None,
        "confidence": classification.confidence if classification else None,
        "llm_hypothesis": classification.llm_hypothesis if classification else None,
        "suggested_contact": classification.suggested_contact if classification else None,
        "evidence": evidence,
        "evidence_items": _evidence_items(evidence),
        "causing_person": attribution.causing_person if attribution else None,
        "reason_text": attribution.reason_text if attribution else None,
        "cause_provenance": attribution.cause_provenance if attribution else None,
        "reason_provenance": attribution.reason_provenance if attribution else None,
        "original_ai_cause": attribution.original_ai_cause if attribution else None,
        "original_ai_reason": attribution.original_ai_reason if attribution else None,
        "validated_by": attribution.validated_by if attribution else None,
        "validated_at": attribution.validated_at if attribution else None,
        "failure": _episode_failure_detail(session, ep),
    }


def _latest_failing_result(session: Session, identity_id: int) -> TestResult | None:
    """The most recent failing result for a test — its error text/stack/location and links."""
    return session.scalar(
        select(TestResult)
        .join(Run, Run.id == TestResult.run_id)
        .where(
            TestResult.test_identity_id == identity_id,
            TestResult.status.in_(FAILED_STATUSES),
        )
        .order_by(Run.started_at.desc(), TestResult.id.desc())
        .limit(1)
    )


def _candidates_for_run(
    session: Session, run_id: int | None, ident: TestIdentity, latest: TestResult | None
) -> dict:
    """Candidate code/data changes in the run's window, **ranked by relevance to this test**.

    Ranking (issue #50) scores each candidate against the test's failure in the candidate run
    (falling back to the latest failing result): changed SVN paths vs the test's module and
    stack-frame paths, changed ``ut_ref`` entities vs the error text. Each row carries its match
    ``reasons`` so the record can show *why* a candidate ranks first; unmatched candidates stay
    chronological below the matched ones.
    """
    if run_id is None:
        return {"code": [], "data": []}
    run = session.get(Run, run_id)
    if run is None:
        return {"code": [], "data": []}
    failure = (
        session.scalar(
            select(TestResult)
            .where(
                TestResult.run_id == run.id,
                TestResult.test_identity_id == ident.id,
                TestResult.status.in_(FAILED_STATUSES),
            )
            .order_by(TestResult.id)
            .limit(1)
        )
        or latest
    )
    ranked = rank_candidates(
        run.code_changes,
        run.data_changes,
        file_path=failure.file_path if failure else None,
        error_details=failure.error_details if failure else None,
        error_stack_trace=failure.error_stack_trace if failure else None,
        class_name=ident.class_name,
    )
    code = [
        {
            "revision": c.revision,
            "author": c.author,
            "message": c.message,
            "committed_at": c.committed_at,
            "score": c.score,
            "reasons": list(c.reasons),
        }
        for c in ranked.code
    ]
    data = [
        {
            "entity": d.entity,
            "pk": d.pk,
            "change_type": d.change_type,
            "component": d.component,
            "author": d.author,
            "changed_at": d.changed_at,
            "score": d.score,
            "reasons": list(d.reasons),
        }
        for d in ranked.data
    ]
    return {"code": code, "data": data}


def _recurrence(
    session: Session, latest: TestResult | None, *, k: int, cutoff: float
) -> dict | None:
    """KB recurrence for the latest failure: exact occurrence stats + similar past cases."""
    if latest is None or latest.signature_id is None:
        return None
    sig = session.get(FailureSignature, latest.signature_id)
    if sig is None:
        return None
    similar = similar_cases(
        session, sig.normalized_text, k=k, cutoff=cutoff, exclude_signature_id=sig.id
    )
    return {
        "signature_id": sig.id,
        # Open failing tests currently sharing this signature's error text — >1 lights up the
        # signature-wide bulk actions ("apply to all N affected tests", issue #106).
        "open_affected": len(open_episodes_for_signature(session, sig.id)),
        "occurrence_count": sig.occurrence_count,
        "exception_type": sig.exception_type,
        "first_seen": _run_ref(session, sig.first_seen_run_id),
        "first_seen_at": sig.first_seen_at,
        "last_seen": _run_ref(session, sig.last_seen_run_id),
        "last_seen_at": sig.last_seen_at,
        "similar": [asdict(c) for c in similar],
    }


def test_record(
    session: Session,
    identity_id: int,
    *,
    flaky_window_days: int = 30,
    flaky_threshold: float = 0.3,
    kb_top_k: int = 5,
    kb_cutoff: float = 0.3,
) -> dict | None:
    """The per-test record: identity, lifecycle, every episode, evidence and context links."""
    ident = session.get(TestIdentity, identity_id)
    if ident is None:
        return None
    lc = ident.lifecycle
    episodes = sorted(ident.episodes, key=lambda e: e.episode_number, reverse=True)
    current_ep = lc.current_episode if lc is not None else None
    latest = _latest_failing_result(session, identity_id)
    candidates = _candidates_for_run(
        session, current_ep.first_failure_run_id if current_ep is not None else None, ident, latest
    )
    flakiness = asdict(
        compute_stats(
            session, identity_id, window_days=flaky_window_days, threshold=flaky_threshold
        )
    )
    recurrence = _recurrence(session, latest, k=kb_top_k, cutoff=kb_cutoff)
    history = _test_history(session, identity_id, window_days=flaky_window_days)
    return {
        "identity_id": ident.id,
        "test_id": ident.canonical_name,
        "suite": ident.suite,
        "class_name": ident.class_name,
        "method": ident.method,
        "owner": ident.main_developer,
        "owner_url": pivot_url("owner", ident.main_developer),
        "zephyr_owner": ident.zephyr_owner,
        "zephyr_test_cases": [z for z in (ident.zephyr_test_cases or "").split(",") if z],
        "lifecycle": None
        if lc is None
        else {
            "state": lc.state,
            "flaky": lc.flaky,
            "reopen_count": lc.reopen_count,
            "acknowledged": lc.acknowledged,
            "acknowledged_by": lc.acknowledged_by,
            "acknowledged_at": lc.acknowledged_at,
            "all_time_first_failure": _run_ref(session, lc.all_time_first_failure_run_id),
            "all_time_first_failure_at": lc.all_time_first_failure_at,
            "last_failing": _run_ref(session, lc.last_failing_run_id),
            "last_failing_at": lc.last_failing_at,
            "current_episode_id": lc.current_episode_id,
        },
        "episodes": [_episode_dict(session, e) for e in episodes],
        "candidates": candidates,
        "flakiness": flakiness,
        "spark": charts.sparkline(history),
        "recurrence": recurrence,
    }


def flaky_leaderboard(
    session: Session,
    *,
    window_days: int = 30,
    threshold: float = 0.3,
    limit: int = 50,
) -> dict:
    """The flaky-leaderboard view: most-unstable tests ranked by oscillation.

    ``total`` is the *true* count of unstable tests in the window (independent of ``limit``), so it
    stays honest when there are more candidates than the display cap.
    """
    candidates = _leaderboard_candidates(session, window_days=window_days, threshold=threshold)
    rows = candidates[:limit]
    for row in rows:
        hist = _test_history(session, row["identity_id"], window_days=window_days)
        row["spark"] = charts.sparkline(hist)
        row["owner_url"] = pivot_url("owner", row["owner"])
    return {"rows": rows, "total": len(candidates), "window_days": window_days}


def kb_search(
    session: Session,
    query: str,
    *,
    k: int = 20,
    cutoff: float = 0.3,
) -> dict:
    """The knowledge-base search: free-text → most-similar past failure signatures.

    Matches against the normalized signature text (the same space the KB keys on), provenance-
    weighted so confirmed/corrected human knowledge surfaces among near-equal matches.
    """
    query = (query or "").strip()
    if not query:
        return {"query": "", "results": []}
    results = [asdict(c) for c in similar_cases(session, query, k=k, cutoff=cutoff)]
    return {"query": query, "results": results}


def test_search(session: Session, query: str, *, limit: int = 20) -> list[dict]:
    """Global "jump to test by name" search (issue #63): canonical-name substring → identities.

    Matches suite/class/method too (all folded into ``canonical_name``), case-insensitively.
    Returns plain rows for the navbar search box: a unique match lets the route redirect straight
    to the test record, several matches render as a short pick-list. ``limit <= 0`` disables the
    cap (same semantics as :func:`_cap` / :func:`_page_window`).
    """
    query = (query or "").strip()
    if not query:
        return []
    stmt = (
        select(TestIdentity)
        .where(TestIdentity.canonical_name.ilike(f"%{query}%"))
        .order_by(TestIdentity.canonical_name)
    )
    if limit > 0:
        stmt = stmt.limit(limit)
    idents = session.scalars(stmt).all()
    return [
        {
            "identity_id": i.id,
            "test_id": i.canonical_name,
            "suite": i.suite,
            "owner": i.main_developer,
            "suite_url": pivot_url("suite", i.suite),
            "owner_url": pivot_url("owner", i.main_developer),
        }
        for i in idents
    ]


def run_summary(
    session: Session,
    build: int,
    *,
    limit: int = DEFAULT_ROW_LIMIT,
    page: int = 1,
    failures_only: bool = False,
    expand: Collection[str] = (),
) -> dict | None:
    """The run summary: build/timing/totals, per-shard timing, baseline + diff, and results.

    The results table is the ~25k-row surface behind issues #19/#52: it is **paginated in SQL**
    (``limit`` rows per page, LIMIT/OFFSET) — never loaded whole, replacing the all-or-nothing
    ``?expand=`` link. ``results_total`` is a COUNT; ``page``/``pages`` drive the pager controls.
    ``limit <= 0`` disables pagination (the operator's explicit no-cap choice).

    ``failures_only`` (issue #63) restricts the results (and their count/pagination) to non-passing
    statuses — paging through ~25k rows to find the handful of failures is the current reality.

    Each diff bucket is ``{"rows": [...], "total": N}``, capped at :data:`DIFF_ROW_LIMIT` rows
    unless its key (see :data:`_RUN_DIFF_SECTIONS`) is in ``expand`` — a bad night's regressions
    would otherwise render as an unbounded link stream (issue #151).
    """
    run = session.scalar(select(Run).where(Run.build_number == build))
    if run is None:
        return None

    baseline = (
        session.get(Run, run.baseline_run_id)
        if run.baseline_run_id is not None
        else select_baseline(session, run)
    )
    diff = compute_diff(session, run, baseline)

    # Resolve identity ids in the diff to linkable names.
    ids = set(diff.regressions + diff.newly_fixed + diff.still_failing + diff.removed)
    names = {
        i.id: i.canonical_name
        for i in session.scalars(select(TestIdentity).where(TestIdentity.id.in_(ids))).all()
    }

    def _diff_bucket(section: str, identity_ids: list[int]) -> dict:
        visible = _cap(identity_ids, section, limit=DIFF_ROW_LIMIT, expand=expand)
        return {
            "rows": [{"identity_id": i, "test_id": names.get(i, str(i))} for i in visible],
            "total": len(identity_ids),
        }

    result_filters = [TestResult.run_id == run.id]
    if failures_only:
        result_filters.append(TestResult.status.in_(FAILED_STATUSES))
    results_total = session.scalar(
        select(func.count()).select_from(TestResult).where(*result_filters)
    )
    page, pages, offset = _page_window(results_total, limit=limit, page=page)
    # Only the visible page is fetched, with the identity name joined in (no per-row lazy load).
    results_query = (
        select(TestResult, TestIdentity.canonical_name, TestIdentity.main_developer)
        .join(TestIdentity, TestIdentity.id == TestResult.test_identity_id)
        .where(*result_filters)
        .order_by(TestResult.status, TestResult.test_identity_id, TestResult.track, TestResult.id)
    )
    if offset is not None:
        results_query = results_query.limit(limit).offset(offset)
    visible_results = session.execute(results_query).all()

    return {
        "build": run.build_number,
        "status": run.status,
        "url": run.url,
        "complete": run.complete,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "totals": {
            "passed": run.total_passed,
            "failed": run.total_failed,
            "skipped": run.total_skipped,
        },
        "shards": [
            {
                "track": s.track,
                "status": s.status,
                "started_at": s.started_at,
                "finished_at": s.finished_at,
            }
            for s in sorted(run.shards, key=lambda s: s.track)
        ],
        "baseline": _run_ref(session, baseline.id) if baseline is not None else None,
        "diff": {
            "regressions": _diff_bucket("regressions", diff.regressions),
            "newly_fixed": _diff_bucket("newly_fixed", diff.newly_fixed),
            "still_failing": _diff_bucket("still_failing", diff.still_failing),
            "removed": _diff_bucket("removed", diff.removed),
        },
        "results": [
            {
                "test_id": canonical_name,
                "identity_id": r.test_identity_id,
                "track": r.track,
                "status": r.status,
                "duration": r.duration,
                "owner": main_developer,
                "owner_url": pivot_url("owner", main_developer),
                "file_path": r.file_path,
                "line": r.line,
            }
            for r, canonical_name, main_developer in visible_results
        ],
        "results_total": results_total,
        "page": page,
        "pages": pages,
        "page_size": limit,
        "failures_only": failures_only,
    }


def job_runs(
    session: Session,
    *,
    poll_interval_seconds: int | None = None,
    limit: int = DEFAULT_ROW_LIMIT,
    page: int = 1,
) -> dict:
    """The 'Job runs' page (issue #37): ingested runs, newest-first, with status, timing, test
    totals and the regression / newly-fixed counts of its diff vs baseline.

    Each run's counts are its diff against its baseline — the most recent *complete* run before it,
    the same baseline the run summary uses (so the two pages never disagree). The list is
    **paginated in SQL** (issue #52), and the per-run work is batched: one query fetches the page's
    runs, one fetches the off-page baselines, and one grouped scan builds every needed
    ``(identity_id, status)`` map — a constant query count per page instead of one scan per run.

    The poller block carries the last tick time and the projected next tick (last + interval) for
    the header banner. The run-health timeline (issue #60) spans the runs on the rendered page.
    """
    total = session.scalar(select(func.count()).select_from(Run))
    page, pages, offset = _page_window(total, limit=limit, page=page)
    runs_query = select(Run).order_by(Run.started_at.desc(), Run.id.desc())
    if offset is not None:
        runs_query = runs_query.limit(limit).offset(offset)
    runs = session.scalars(runs_query).all()

    # Resolve each run's baseline: the recorded id when the analysis stamped one, else the
    # most-recent-complete-run rule (rare: the store's first run, or a run analysed pre-stamping).
    by_id: dict[int, Run] = {run.id: run for run in runs}
    missing = {
        run.baseline_run_id
        for run in runs
        if run.baseline_run_id is not None and run.baseline_run_id not in by_id
    }
    if missing:
        for baseline in session.scalars(select(Run).where(Run.id.in_(missing))).all():
            by_id[baseline.id] = baseline
    baselines: dict[int, Run | None] = {}
    for run in runs:
        if run.baseline_run_id is not None:
            baselines[run.id] = by_id.get(run.baseline_run_id)
        else:
            baselines[run.id] = select_baseline(session, run)

    # One grouped scan builds every status map the page needs (runs + their baselines).
    needed_ids = {run.id for run in runs} | {b.id for b in baselines.values() if b is not None}
    status_maps = identity_status_maps(session, needed_ids)

    rows: list[dict] = []
    for run in runs:
        baseline = baselines[run.id]
        diff = compute_diff(
            session,
            run,
            baseline,
            current=status_maps[run.id],
            baseline_status=status_maps[baseline.id] if baseline is not None else {},
        )
        rows.append(
            {
                "build": run.build_number,
                "status": run.status,
                "url": run.url,
                "complete": run.complete,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "duration_seconds": _duration_seconds(run.started_at, run.finished_at),
                "totals": {
                    "passed": run.total_passed,
                    "failed": run.total_failed,
                    "skipped": run.total_skipped,
                    "total": run.total_passed + run.total_failed + run.total_skipped,
                },
                "regressions": len(diff.regressions),
                "newly_fixed": len(diff.newly_fixed),
            }
        )

    hb = read_heartbeat(session)
    last_poll_at = hb.last_poll_at if hb else None
    next_poll_at = None
    if last_poll_at is not None and poll_interval_seconds:
        next_poll_at = _aware(last_poll_at) + timedelta(seconds=poll_interval_seconds)

    timeline = charts.run_health_timeline(
        [
            {"build": r["build"], "failed": r["totals"]["failed"], "regressions": r["regressions"]}
            for r in reversed(rows)  # rows are newest-first; the chart reads left-to-right in time
        ]
    )

    return {
        "runs": rows,
        "timeline": timeline,
        "total": total,
        "page": page,
        "pages": pages,
        "page_size": limit,
        "poller": {
            "last_poll_at": last_poll_at,
            "next_poll_at": next_poll_at,
            "poll_interval_seconds": poll_interval_seconds,
        },
    }
