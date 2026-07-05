"""Read-side view builders for the dashboard (triage queue, per-test record, run summary).

Every function takes a live session and returns **plain detached dicts** so Jinja templates never
touch a closed session (the Slice-0 pattern). Nothing here mutates state — the buckets are a pure
**projection** of lifecycle state + the orthogonal acknowledgement attribute, so no separate
bookkeeping exists to drift.
"""

from __future__ import annotations

import json
from collections.abc import Collection, Sequence
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from uta.analyze.baseline import compute_diff, identity_status_map, select_baseline
from uta.analyze.flakiness import compute_stats
from uta.analyze.flakiness import leaderboard_candidates as _leaderboard_candidates
from uta.control.heartbeat import read_heartbeat
from uta.ingest.ut_report import FAILED_STATUSES
from uta.kb.retrieval import similar_cases
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

# Default max rows a dashboard section renders before it is capped behind a "Load all N Tests" link.
# Mirrors ``Settings.ui_row_limit``; kept here so the view layer has a sane default when called
# directly (tests, CLI). A limit of 0 disables the cap.
DEFAULT_ROW_LIMIT = 100


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


def _run_ref(session: Session, run_id: int | None) -> dict | None:
    """A minimal {id, build, url} reference to a run (episodes hold only the FK)."""
    if run_id is None:
        return None
    run = session.get(Run, run_id)
    if run is None:
        return None
    return {"id": run.id, "build": run.build_number, "url": run.url}


def _latest_classification(session: Session, episode_id: int) -> Classification | None:
    """The current prediction for an episode (rows are append-only; newest wins)."""
    return session.scalar(
        select(Classification)
        .where(Classification.episode_id == episode_id)
        .order_by(Classification.created_at.desc(), Classification.id.desc())
        .limit(1)
    )


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


def _row(session: Session, lc: TestLifecycle) -> dict:
    """Shared row projection for the triage buckets — identity + current episode + prediction."""
    ident = lc.identity
    ep = lc.current_episode
    classification = _latest_classification(session, ep.id) if ep is not None else None
    attribution = ep.attribution if ep is not None else None
    first_failure = _run_ref(session, ep.first_failure_run_id) if ep is not None else None
    fixed_in = _run_ref(session, ep.fixed_in_run_id) if ep is not None else None
    return {
        "identity_id": ident.id,
        "test_id": ident.canonical_name,
        "owner": ident.owner_initials,
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
    }


def triage_queue(
    session: Session,
    *,
    recently_fixed_days: int = 7,
    limit: int = DEFAULT_ROW_LIMIT,
    expand: Collection[str] = (),
) -> dict:
    """The three-bucket triage queue: new-unacknowledged / still-failing(+removed) / recently-fixed.

    Buckets are a projection of lifecycle ``state`` and the orthogonal ``acknowledged`` attribute:

    1. **New** — ``FAILING`` and not acknowledged (newest-first); the action queue.
    2. **Still failing** — ``FAILING`` and acknowledged, plus ``REMOVED`` tests with an open
       episode surfaced with a Removed flag (disappeared ≠ fixed).
    3. **Recently fixed** — ``FIXED`` within the configured window (default 7 days).

    Each bucket is capped at ``limit`` rows for rendering (long lists hurt UI responsiveness —
    issue #19); ``counts`` stays the full, pre-cap size, and a section named in ``expand`` renders
    in full. ``truncated`` reports, per bucket, whether rows were dropped.
    """
    lifecycles = session.scalars(
        select(TestLifecycle).join(TestIdentity, TestLifecycle.identity)
    ).all()

    new: list[dict] = []
    still_failing: list[dict] = []
    recently_fixed: list[dict] = []
    cutoff = _now() - timedelta(days=recently_fixed_days)

    for lc in lifecycles:
        ep = lc.current_episode
        if lc.state == LifecycleState.FAILING:
            row = _row(session, lc)
            (still_failing if lc.acknowledged else new).append(row)
        elif lc.state == LifecycleState.REMOVED and ep is not None and ep.is_open:
            row = _row(session, lc)
            row["removed"] = True
            still_failing.append(row)
        elif lc.state == LifecycleState.FIXED and ep is not None and ep.fixed_at is not None:
            if _aware(ep.fixed_at) >= cutoff:
                recently_fixed.append(_row(session, lc))

    new.sort(key=lambda r: (r["first_failure_at"] is not None, r["first_failure_at"]), reverse=True)
    still_failing.sort(key=lambda r: (r.get("removed", False), r["age_days"] or 0), reverse=True)
    recently_fixed.sort(key=lambda r: (r["fixed_at"] is not None, r["fixed_at"]), reverse=True)

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
        "llm_hypothesis": classification.llm_hypothesis if classification else None,
        "suggested_contact": classification.suggested_contact if classification else None,
        "evidence": evidence,
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


def _candidates_for_run(session: Session, run_id: int | None) -> dict:
    """Candidate code/data changes in the run's window, presented chronologically."""
    if run_id is None:
        return {"code": [], "data": []}
    run = session.get(Run, run_id)
    if run is None:
        return {"code": [], "data": []}
    code = [
        {
            "revision": c.revision or c.commit_id,
            "author": c.author,
            "message": c.message,
            "committed_at": c.committed_at,
        }
        for c in sorted(run.code_changes, key=lambda c: c.committed_at)
    ]
    data = [
        {
            "entity": d.lx_table_code,
            "pk": d.pk_lst,
            "change_type": d.change_type,
            "component": d.component_name,
            "author": d.author,
            "changed_at": d.changed_at,
        }
        for d in sorted(run.data_changes, key=lambda d: d.changed_at)
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
        session, current_ep.first_failure_run_id if current_ep is not None else None
    )
    flakiness = asdict(
        compute_stats(
            session, identity_id, window_days=flaky_window_days, threshold=flaky_threshold
        )
    )
    recurrence = _recurrence(session, latest, k=kb_top_k, cutoff=kb_cutoff)
    return {
        "identity_id": ident.id,
        "test_id": ident.canonical_name,
        "suite": ident.suite,
        "class_name": ident.class_name,
        "method": ident.method,
        "owner": ident.owner_initials,
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
    return {"rows": candidates[:limit], "total": len(candidates), "window_days": window_days}


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


def run_summary(
    session: Session,
    build: int,
    *,
    limit: int = DEFAULT_ROW_LIMIT,
    expand: Collection[str] = (),
) -> dict | None:
    """The run summary: build/timing/totals, per-shard timing, baseline + diff, and results.

    The results table is the ~25k-row surface behind issue #19: it is capped at ``limit`` rows
    (unless ``"results"`` is in ``expand``) *before* projection, so the expensive per-row work is
    skipped too. ``results_total`` carries the full count for the "Load all N Tests" hint.
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

    def _diff_rows(identity_ids: list[int]) -> list[dict]:
        return [{"identity_id": i, "test_id": names.get(i, str(i))} for i in identity_ids]

    results = session.scalars(
        select(TestResult)
        .where(TestResult.run_id == run.id)
        .order_by(TestResult.status, TestResult.test_identity_id)
    ).all()
    results_total = len(results)
    # Cap before projecting — the per-row identity name is a lazy load, so this skips the work too.
    visible_results = _cap(results, "results", limit=limit, expand=expand)

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
            "regressions": _diff_rows(diff.regressions),
            "newly_fixed": _diff_rows(diff.newly_fixed),
            "still_failing": _diff_rows(diff.still_failing),
            "removed": _diff_rows(diff.removed),
        },
        "results": [
            {
                "test_id": r.identity.canonical_name,
                "identity_id": r.test_identity_id,
                "track": r.track,
                "status": r.status,
                "duration": r.duration,
                "owner": r.owner_initials,
                "file_path": r.file_path,
                "line": r.line,
            }
            for r in visible_results
        ],
        "results_total": results_total,
    }


def job_runs(session: Session, *, poll_interval_seconds: int | None = None) -> dict:
    """The 'Job runs' page (issue #37): every ingested run, newest-first, with status, timing,
    test totals and the regression / newly-fixed counts of its diff vs baseline.

    Each run's counts are its diff against its baseline — the most recent *complete* run before it,
    the same baseline the run summary uses (so the two pages never disagree). Status maps are cached
    and reused across runs (a run's baseline is typically the run just before it), so the page costs
    roughly one lightweight ``(identity_id, status)`` scan per run rather than two.

    The poller block carries the last tick time and the projected next tick (last + interval) for
    the header banner.
    """
    runs = session.scalars(select(Run).order_by(Run.started_at.desc())).all()

    status_cache: dict[int, dict[int, str]] = {}

    def _status_map(run: Run) -> dict[int, str]:
        if run.id not in status_cache:
            status_cache[run.id] = identity_status_map(session, run)
        return status_cache[run.id]

    rows: list[dict] = []
    for run in runs:
        baseline = (
            session.get(Run, run.baseline_run_id)
            if run.baseline_run_id is not None
            else select_baseline(session, run)
        )
        diff = compute_diff(
            session,
            run,
            baseline,
            current=_status_map(run),
            baseline_status=_status_map(baseline) if baseline is not None else {},
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

    return {
        "runs": rows,
        "poller": {
            "last_poll_at": last_poll_at,
            "next_poll_at": next_poll_at,
            "poll_interval_seconds": poll_interval_seconds,
        },
    }
