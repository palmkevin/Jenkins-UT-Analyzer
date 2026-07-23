"""Ingest pipeline: fetch one build -> parse -> persist a build, its results and candidates, then
(for complete builds) drive the cross-build analysis (lifecycle + diff + classification).

Wires the Jenkins client + Oracle feed (real or fake) and the parsers. Idempotent on
``build_number``: a re-ingest replaces the build's results/shards/candidates rather than duplicating
them, and re-builds the analysis (which is itself idempotent per baseline+build). The analysis pass
only runs when the build is (still) the newest complete build — a **historical** re-ingest persists
the build's data but never drives the lifecycle (issue #82).
"""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import timedelta

from sqlalchemy import insert, select
from sqlalchemy.orm import Session, sessionmaker

from uta.analyze.baseline import has_newer_complete_build, select_baseline
from uta.analyze.classify import classify_build
from uta.analyze.error_type import derive_error_type
from uta.analyze.flakiness import recompute_flaky_flags
from uta.analyze.hypothesize import hypothesize_build
from uta.analyze.lifecycle import apply_build
from uta.analyze.ownership import resolve_for_cases
from uta.db import session_scope
from uta.delivery.email import EmailMessage, EmailSender, build_regression_report, send_alert
from uta.ingest.jenkins import JenkinsClient
from uta.ingest.svn_update import parse_change_sets
from uta.ingest.unittest_log import parse_unittest_log
from uta.ingest.ut_report import TestCaseResult, parse_test_report
from uta.ingest.wfapi import (
    DEFAULT_UNITTEST_SUITES,
    FINISHED_STAGE_STATUSES,
    LogStage,
    find_log_step_node,
    find_unittest_stages,
    parse_wfapi,
)
from uta.kb.store import record_signatures_for_build
from uta.llm import HypothesisProvider, NoopHypothesisProvider
from uta.models import (
    Build,
    BuildShard,
    CodeChangeCandidate,
    DataChangeCandidate,
    TestIdentity,
    TestResult,
)
from uta.refdb.oracle import TrackingFeed
from uta.refdb.svn import SvnBlameClient

_PASSED = frozenset({"PASSED", "FIXED"})
_FAILED = frozenset({"FAILED", "REGRESSION"})

logger = logging.getLogger(__name__)


def _dedupe_cases(cases: list[TestCaseResult]) -> list[TestCaseResult]:
    """Collapse duplicate ``(test_id, track)`` results to one, keeping the first occurrence.

    A result is keyed ``(build, test, track)`` (``uq_build_test_track``), so two cases sharing a
    ``(test_id, track)`` would violate that constraint and roll back the whole ingest. This happens
    because the unittest **console-log** stages are not disjoint from the devUTs nose2 surface:
    nose2 also collects some of the modules those stages run (e.g. ``itf.highlevel.tests.iricell``,
    ``ls.smb.tests.transform.lx.cases``), so the same test is reported by both sources in one build.

    The JUnit report is the **authoritative** surface (callers list its cases first), so first-wins
    keeps the JUnit result and lets the console-log stages contribute only tests JUnit didn't cover.
    """
    seen: set[tuple[str, str]] = set()
    deduped: list[TestCaseResult] = []
    dropped: list[tuple[str, str]] = []
    for case in cases:
        key = (case.test_id, case.track)
        if key in seen:
            dropped.append(key)
            continue
        seen.add(key)
        deduped.append(case)
    if dropped:
        logger.info(
            "dropped %d duplicate (test_id, track) result(s) before persist: %s",
            len(dropped),
            ", ".join(f"{t}@{k}" for t, k in dropped[:10]),
        )
    return deduped


# Upper bound on concurrent Jenkins calls per build: the 4 base endpoints plus one per unittest
# console-log stage (5 suites x 2 tracks by default) — comfortably under this cap.
_FETCH_MAX_WORKERS = 16


def _fetch_stage_log(client: JenkinsClient, build: int, stage: LogStage) -> tuple[LogStage, dict]:
    """One stage's describe->log pair (the log's node id depends on the describe call)."""
    describe = client.stage_describe(build, stage.node_id)
    step_id = find_log_step_node(describe) or stage.node_id
    return stage, client.stage_log(build, step_id)


_IDENTITY_CHUNK = 1000


def _resolve_identities(session: Session, cases: list[TestCaseResult]) -> dict[str, TestIdentity]:
    """Preload/create every case's identity in bulk (was one SELECT per case — the N+1 hot spot).

    Existing identities are fetched with a chunked ``canonical_name IN (...)`` query; the missing
    ones are created and added to the dict, then flushed once so their ids exist before results
    reference them. Descriptive attributes (suite/class/method/zephyr_owner/zephyr_test_cases) are
    refreshed from the latest case, exactly as the per-case path did. ``main_developer`` is *not*
    set here — it comes from SVN blame, resolved separately (issue #114).
    """
    names = {case.test_id for case in cases}
    identities: dict[str, TestIdentity] = {}
    name_list = list(names)
    for start in range(0, len(name_list), _IDENTITY_CHUNK):
        chunk = name_list[start : start + _IDENTITY_CHUNK]
        for ident in session.scalars(
            select(TestIdentity).where(TestIdentity.canonical_name.in_(chunk))
        ).all():
            identities[ident.canonical_name] = ident
    for name in names:
        if name not in identities:
            ident = TestIdentity(canonical_name=name)
            session.add(ident)
            identities[name] = ident

    # Refresh descriptive attributes from the latest case for each name (last case wins, matching
    # the loop-order the per-case path applied).
    for case in cases:
        ident = identities[case.test_id]
        ident.suite = case.suite_name
        ident.class_name = case.class_name
        ident.method = case.name
        if case.zephyr_owner:
            ident.zephyr_owner = case.zephyr_owner
        if case.zephyr_ids:
            ident.zephyr_test_cases = ",".join(case.zephyr_ids)

    session.flush()  # new identities need ids before the bulk TestResult insert references them
    return identities


def ingest_build(
    client: JenkinsClient,
    session_factory: sessionmaker[Session],
    number: int,
    *,
    expected_shards: int = 2,
    feed: TrackingFeed | None = None,
    data_change_lookback: timedelta = timedelta(hours=12),
    data_change_tolerance: timedelta = timedelta(minutes=5),
    flaky_window_days: int = 30,
    flaky_threshold: float = 0.3,
    email_sender: EmailSender | None = None,
    email_recipients: tuple[str, ...] = (),
    email_recovery_notice: bool = False,
    app_base_url: str = "",
    hypothesis_provider: HypothesisProvider | None = None,
    kb_top_k: int = 5,
    kb_similarity_cutoff: float = 0.3,
    ingest_unittest_logs: bool = False,
    unittest_suites: frozenset[str] | set[str] | None = None,
    recompute_flaky: bool = True,
    svn_blame_client: SvnBlameClient | None = None,
) -> int:
    """Fetch, parse and persist one build, then analyse it. Returns the build's build_number.

    Persists the build, its per-(test, track) results (with derived error type), per-shard timing
    and
    the change-signal candidates (SVN revisions; ``ut_ref`` changes when a ``feed`` is supplied),
    and records a normalized **failure signature** per failing result (the KB recurrence key).
    For a
    **complete** build it then drives the lifecycle/episodes, the baseline diff, the deterministic
    classification of new regressions, refreshes the oscillation **flaky** flags, and — when an
    ``email_sender`` is supplied — sends the regression-only alert **after the transaction
    commits** (a send failure is logged and dropped, never failing the ingest). When a real
    ``hypothesis_provider`` is supplied it also fills the LLM root-cause hypothesis per new episode;
    the default Noop provider makes that a no-op. Idempotent on re-ingest; back-fill passes no
    sender and no provider, so history is never re-mailed or re-hypothesised.

    The lifecycle/classification/notify pass only runs when the build is (still) the **newest**
    complete build. Re-ingesting an older build — the quarantine-recovery path (issue #82) — keeps
    the build, its results and its KB signatures, but skips the analysis: its diff describes old
    facts, and applying it would corrupt the current lifecycle/episode state.

    When ``ingest_unittest_logs`` is set, the deferred **unittest console-log** UT stages (``LXS``,
    ``SMB Pricing``/``Transform``, ``ITF Highlevel``, ``Uniface deploy unit tests`` by default — see
    ``unittest_suites``) are also fetched via ``wfapi/log`` and parsed into the same per-(test,
    track) results, so they share the JUnit tests' identity/lifecycle/classification path. Off by
    default, so the devUTs-only ingest is unchanged unless the caller opts in. A selected stage
    that didn't run to the end (its wfapi status is not a finished one) marks the build incomplete,
    mirroring the devUTs shard guard; a suite stage absent from the payload has no effect.
    """
    t_total = time.perf_counter()

    # The 4 base endpoints are mutually independent, and each unittest stage's describe/log pair is
    # independent of the others and of the base fetches — dispatched concurrently on a thread pool
    # (the client is a sync httpx.Client behind the JenkinsClient Protocol/fake seam). Stage tasks
    # need wfapi's result to know which stages exist, so they're submitted once that one future
    # resolves rather than waiting on all 4 base calls.
    t = time.perf_counter()
    with ThreadPoolExecutor(max_workers=_FETCH_MAX_WORKERS) as pool:
        meta_f = pool.submit(client.build_meta, number)
        wfapi_f = pool.submit(client.wfapi, number)
        report_f = pool.submit(client.test_report, number)
        change_sets_f = pool.submit(client.change_sets, number)

        wfapi_payload = wfapi_f.result()

        stage_futures: list[Future[tuple[LogStage, dict]]] = []
        log_stages: list[LogStage] = []
        if ingest_unittest_logs:
            suites = DEFAULT_UNITTEST_SUITES if unittest_suites is None else unittest_suites
            log_stages = find_unittest_stages(wfapi_payload, suites)
            stage_futures = [
                pool.submit(_fetch_stage_log, client, number, stage) for stage in log_stages
            ]

        meta = meta_f.result()
        report_payload = report_f.result()
        change_sets_payload = change_sets_f.result()
        stage_logs: list[tuple[LogStage, dict]] = [f.result() for f in stage_futures]
    t_fetch = time.perf_counter() - t

    t = time.perf_counter()
    timing = parse_wfapi(wfapi_payload)
    report = parse_test_report(report_payload)
    change_sets = parse_change_sets(change_sets_payload)
    win_start, win_end = timing.window

    cases: list[TestCaseResult] = list(report.cases)
    for stage, log in stage_logs:
        cases.extend(parse_unittest_log(log, track=stage.track, suite_name=stage.suite))

    # The two ingest sources overlap on a few tests (nose2 also collects some console-log modules),
    # so collapse duplicate (test_id, track) results before persist — JUnit (listed first) wins.
    cases = _dedupe_cases(cases)
    t_parse = time.perf_counter() - t

    t_persist = t_signatures = t_lifecycle = t_classify = t_flaky = 0.0
    pending_alert: EmailMessage | None = None
    with session_scope(session_factory) as session:
        t = time.perf_counter()
        build = session.scalar(select(Build).where(Build.build_number == number))
        stale_signature_ids: set[int] = set()
        if build is None:
            build = Build(build_number=number)
            session.add(build)
        else:
            # Capture the signatures the old results linked to BEFORE the idempotent delete: a
            # signature whose failure vanished from the re-ingested content gains no new link, so
            # the KB store must still recompute it (else its aggregates stay permanently stale).
            stale_signature_ids = set(
                session.scalars(
                    select(TestResult.signature_id.distinct()).where(
                        TestResult.build_id == build.id, TestResult.signature_id.is_not(None)
                    )
                )
            )
            build.results.clear()  # idempotent re-ingest
            build.shards.clear()
            build.code_changes.clear()
            build.data_changes.clear()
            session.flush()  # delete old rows before re-inserting (unique constraint)

        build.status = meta.get("result") or timing.status
        build.url = meta.get("url", "")
        build.started_at = win_start
        build.finished_at = win_end
        # Completeness spans both ingest sources: the devUTs JUnit shards (via is_complete) *and*
        # every selected unittest console-log stage. A stage cut short (ABORTED, NOT_EXECUTED, …)
        # yields a truncated log that parses to a partial case list — marking the build complete
        # would invent phantom removed/newly-fixed transitions and poison the next baseline,
        # exactly the issue-#83 failure mode the shard guard prevents. A suite stage absent from
        # the wfapi payload never affects completeness (job configuration varies over history);
        # the truncated results are still persisted below — analysis is gated on build.complete.
        build.complete = timing.is_complete(expected_shards) and all(
            stage.status in FINISHED_STAGE_STATUSES for stage in log_stages
        )
        build.total_passed = sum(1 for c in cases if c.status in _PASSED)
        build.total_failed = sum(1 for c in cases if c.status in _FAILED)
        build.total_skipped = sum(1 for c in cases if c.status == "SKIPPED")

        for shard in timing.shards.values():
            build.shards.append(
                BuildShard(
                    track=shard.track,
                    status=shard.status,
                    started_at=shard.start,
                    finished_at=shard.end,
                )
            )

        # Resolve every identity in bulk, then flush so build.id + identity ids exist for the Core
        # bulk insert of results (25k+ rows/build — far cheaper than per-row ORM appends).
        identities = _resolve_identities(session, cases)
        session.flush()  # build.id must exist before result rows reference it
        result_rows = [
            {
                "build_id": build.id,
                "test_identity_id": identities[case.test_id].id,
                "track": case.track,
                "status": case.status,
                "duration": case.duration,
                "file_path": case.file_path,
                "line": case.line,
                "zephyr_owner": case.zephyr_owner,
                "error_type": derive_error_type(
                    case.status, case.error_details, case.error_stack_trace
                ),
                "error_details": case.error_details,
                "error_stack_trace": case.error_stack_trace,
            }
            for case in cases
        ]
        if result_rows:
            session.execute(insert(TestResult), result_rows)

        # Owner = the test's main developer, from SVN blame (issue #114). Gated: only when a blame
        # client is wired (SVN_BLAME_ENABLED) — off for the offline gate, local dev and the demo.
        # Scoped to this build's failing tests (only failures carry a source path); identities keep
        # their resolved owner across builds, so this fills newly-seen tests incrementally.
        if svn_blame_client is not None:
            resolve_for_cases(identities, cases, svn_blame_client)

        for change in change_sets.changes:
            build.code_changes.append(
                CodeChangeCandidate(
                    commit_id=change.commit_id,
                    revision=change.commit_id,
                    author=change.author,
                    message=change.message,
                    committed_at=change.when,
                    paths=json.dumps(
                        [{"editType": p.edit_type, "file": p.file} for p in change.paths]
                    ),
                )
            )

        if feed is not None:
            lo, hi = data_change_window(
                timing.window, lookback=data_change_lookback, tolerance=data_change_tolerance
            )
            for dc in feed.changes_in_window(lo, hi):
                build.data_changes.append(
                    DataChangeCandidate(
                        lx_table_code=dc.entity,
                        pk_lst=dc.pk,
                        change_type=dc.change_type,
                        component_name=dc.component,
                        author=dc.user_code,
                        session_log_id=None
                        if dc.session_log_id is None
                        else str(dc.session_log_id),
                        changed_at=dc.cre_utc,
                    )
                )

        session.flush()  # candidates + results must be visible to the KB store and classifier
        t_persist = time.perf_counter() - t

        # KB: a normalized failure signature per failing result (recurrence key). Recorded for
        # any build (the signatures are facts about the failures), idempotent on re-ingest.
        t = time.perf_counter()
        record_signatures_for_build(session, build, stale_signature_ids=stale_signature_ids)
        t_signatures = time.perf_counter() - t

        if build.complete:
            # Lifecycle only ever advances forward: a **historical** re-ingest — a build older
            # than the newest complete build, reachable via the control panel's range ingest (the
            # quarantine-recovery path, issue #82) — must not drive the state machine. Its diff
            # describes old facts while apply_build mutates the *current* lifecycle/episode rows
            # (phantom reopened episodes, cleared acknowledgements, live episodes "fixed" in the
            # past). The build, its results and its KB signatures are persisted above regardless;
            # only the analysis pass (and the classify/hypothesize/notify steps that consume its
            # opened episodes) is skipped.
            historical = has_newer_complete_build(session, build)
            if historical:
                # Stamp the display baseline so the build page still shows this build's diff.
                baseline = select_baseline(session, build)
                build.baseline_build_id = baseline.id if baseline is not None else None
                logger.info(
                    "build #%d is older than the newest complete build — historical re-ingest, "
                    "lifecycle/classification skipped (build, results and signatures persisted)",
                    build,
                )
            else:
                t = time.perf_counter()
                analysis = apply_build(session, build)
                t_lifecycle = time.perf_counter() - t

                t = time.perf_counter()
                classify_build(session, build, analysis.opened_episodes)
                hypothesize_build(
                    session,
                    build,
                    analysis.opened_episodes,
                    hypothesis_provider or NoopHypothesisProvider(),
                    top_k=kb_top_k,
                    cutoff=kb_similarity_cutoff,
                )
                t_classify = time.perf_counter() - t

            if recompute_flaky:
                t = time.perf_counter()
                recompute_flaky_flags(
                    session, window_days=flaky_window_days, threshold=flaky_threshold
                )
                t_flaky = time.perf_counter() - t
            # Compose (not send) the regression alert here — it needs the session — and carry it
            # past the commit below. Sending inside the transaction let an SMTP outage roll back
            # a healthy ingest, and a post-send commit failure re-mailed the identical alert on
            # the poller's retry (issue #81). A historical re-ingest never alerts: its diff
            # describes old facts (issue #82).
            if not historical and email_sender is not None and email_recipients:
                pending_alert = build_regression_report(
                    session,
                    build,
                    email_recipients,
                    recovery_notice=email_recovery_notice,
                    app_base_url=app_base_url,
                )

    # The alert goes out only once the build is durably committed, and a send failure is swallowed
    # (logged) by ``send_alert`` — mail can never fail the ingest. At-most-once per build: a commit
    # failure raises out of the ``with`` above before anything is sent (the poller's retry
    # recomputes and sends once), the poller never re-ingests below its high-water mark, and the
    # re-ingest paths (CLI back-fill, on-demand job) pass no sender by contract.
    if pending_alert is not None and email_sender is not None:
        send_alert(email_sender, pending_alert)

    total = time.perf_counter() - t_total
    logger.info(
        "build #%d ingested in %.1fs (fetch=%.1f parse=%.1f persist=%.1f signatures=%.1f "
        "lifecycle=%.1f classify=%.1f flaky=%.1f)",
        build,
        total,
        t_fetch,
        t_parse,
        t_persist,
        t_signatures,
        t_lifecycle,
        t_classify,
        t_flaky,
    )
    return build


def data_change_window(
    timing_window: tuple,
    lookback: timedelta = timedelta(hours=12),
    tolerance: timedelta = timedelta(minutes=5),
) -> tuple:
    """The UTC window for candidate data changes: a lookback before the build through its end.

    Data changes precede the nightly build (confirmed empirically on #1702 — the build's own
    window had
    no tracked changes), so we look back from the build start. The ``tolerance`` margin (B1) widens
    both ends to absorb residual clock skew between the Jenkins and Oracle ``ut_ref`` clocks.
    ``lookback`` is a provisional default, tuned on real data later.
    """
    start, end = timing_window
    return start - lookback - tolerance, end + tolerance
