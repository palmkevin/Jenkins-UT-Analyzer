"""Ingest pipeline: fetch one build -> parse -> persist a run, its results and candidates, then
(for complete runs) drive the cross-run analysis (lifecycle + diff + classification).

Wires the Jenkins client + Oracle feed (real or fake) and the parsers. Idempotent on
``build_number``: a re-ingest replaces the run's results/shards/candidates rather than duplicating
them, and re-runs the analysis (which is itself idempotent per baseline+run).
"""

from __future__ import annotations

import json
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from uta.analyze.classify import classify_run
from uta.analyze.error_type import derive_error_type
from uta.analyze.flakiness import recompute_flaky_flags
from uta.analyze.hypothesize import hypothesize_run
from uta.analyze.lifecycle import apply_run
from uta.db import session_scope
from uta.delivery.email import EmailSender, maybe_notify
from uta.ingest.jenkins import JenkinsClient
from uta.ingest.svn_update import parse_change_sets
from uta.ingest.unittest_log import parse_unittest_log
from uta.ingest.ut_report import TestCaseResult, parse_test_report
from uta.ingest.wfapi import DEFAULT_UNITTEST_SUITES, find_unittest_stages, parse_wfapi
from uta.kb.store import record_signatures_for_run
from uta.llm import HypothesisProvider, NoopHypothesisProvider
from uta.models import (
    CodeChangeCandidate,
    DataChangeCandidate,
    Run,
    RunShard,
    TestIdentity,
    TestResult,
)
from uta.refdb.oracle import TrackingFeed

_PASSED = frozenset({"PASSED", "FIXED"})
_FAILED = frozenset({"FAILED", "REGRESSION"})


def _get_or_create_identity(
    session: Session, case: TestCaseResult, cache: dict[str, TestIdentity]
) -> TestIdentity:
    """Resolve the test-level identity for a case, creating it on first sight (idempotent)."""
    name = case.test_id  # className.name — the canonical v1 key
    ident = cache.get(name)
    if ident is None:
        ident = session.scalar(select(TestIdentity).where(TestIdentity.canonical_name == name))
        if ident is None:
            ident = TestIdentity(canonical_name=name)
            session.add(ident)
        cache[name] = ident
    # Keep the descriptive attributes fresh from the latest report.
    ident.suite = case.suite_name
    ident.class_name = case.class_name
    ident.method = case.name
    if case.owner_initials:
        ident.owner_initials = case.owner_initials
    return ident


def ingest_build(
    client: JenkinsClient,
    session_factory: sessionmaker[Session],
    build: int,
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
    hypothesis_provider: HypothesisProvider | None = None,
    kb_top_k: int = 5,
    kb_similarity_cutoff: float = 0.3,
    ingest_unittest_logs: bool = False,
    unittest_suites: frozenset[str] | set[str] | None = None,
) -> int:
    """Fetch, parse and persist one build, then analyse it. Returns the run's build_number.

    Persists the run, its per-(test, track) results (with derived error type), per-shard timing and
    the change-signal candidates (SVN revisions; ``ut_ref`` changes when a ``feed`` is supplied),
    and records a normalized **failure signature** per failing result (the KB recurrence key, §4).
    For a
    **complete** run it then drives the lifecycle/episodes, the baseline diff, the deterministic
    classification of new regressions, refreshes the oscillation **flaky** flags (§3), and — when an
    ``email_sender`` is supplied — sends the regression-only alert (§5). When a real
    ``hypothesis_provider`` is supplied it also fills the LLM root-cause hypothesis per new episode
    (§4); the default Noop provider makes that a no-op. Idempotent on re-ingest; back-fill passes no
    sender and no provider, so history is never re-mailed or re-hypothesised.

    When ``ingest_unittest_logs`` is set, the deferred **unittest console-log** UT stages (``LXS``,
    ``SMB Pricing``/``Transform``, ``ITF Highlevel``, ``Uniface deploy unit tests`` by default — see
    ``unittest_suites``) are also fetched via ``wfapi/log`` and parsed into the same per-(test,
    track) results, so they share the JUnit tests' identity/lifecycle/classification path. Off by
    default, so the devUTs-only ingest is unchanged unless the caller opts in.
    """
    meta = client.build_meta(build)
    wfapi_payload = client.wfapi(build)
    timing = parse_wfapi(wfapi_payload)
    report = parse_test_report(client.test_report(build))
    change_sets = parse_change_sets(client.change_sets(build))
    win_start, win_end = timing.window

    cases: list[TestCaseResult] = list(report.cases)
    if ingest_unittest_logs:
        suites = DEFAULT_UNITTEST_SUITES if unittest_suites is None else unittest_suites
        for stage in find_unittest_stages(wfapi_payload, suites):
            log = client.stage_log(build, stage.node_id)
            cases.extend(parse_unittest_log(log, track=stage.track, suite_name=stage.suite))

    with session_scope(session_factory) as session:
        run = session.scalar(select(Run).where(Run.build_number == build))
        if run is None:
            run = Run(build_number=build)
            session.add(run)
        else:
            run.results.clear()  # idempotent re-ingest
            run.shards.clear()
            run.code_changes.clear()
            run.data_changes.clear()
            session.flush()  # delete old rows before re-inserting (unique constraint)

        run.status = meta.get("result") or timing.status
        run.url = meta.get("url", "")
        run.started_at = win_start
        run.finished_at = win_end
        run.complete = timing.is_complete(expected_shards)
        run.total_passed = sum(1 for c in cases if c.status in _PASSED)
        run.total_failed = sum(1 for c in cases if c.status in _FAILED)
        run.total_skipped = sum(1 for c in cases if c.status == "SKIPPED")

        for shard in timing.shards.values():
            run.shards.append(
                RunShard(
                    track=shard.track,
                    status=shard.status,
                    started_at=shard.start,
                    finished_at=shard.end,
                )
            )

        identities: dict[str, TestIdentity] = {}
        for case in cases:
            ident = _get_or_create_identity(session, case, identities)
            run.results.append(
                TestResult(
                    identity=ident,
                    track=case.track,
                    status=case.status,
                    duration=case.duration,
                    file_path=case.file_path,
                    line=case.line,
                    owner_initials=case.owner_initials,
                    error_type=derive_error_type(
                        case.status, case.error_details, case.error_stack_trace
                    ),
                    error_details=case.error_details,
                    error_stack_trace=case.error_stack_trace,
                )
            )

        for change in change_sets.changes:
            run.code_changes.append(
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
                run.data_changes.append(
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

        # KB: a normalized failure signature per failing result (recurrence key, §4). Recorded for
        # any run (the signatures are facts about the failures), idempotent on re-ingest.
        record_signatures_for_run(session, run)

        if run.complete:
            analysis = apply_run(session, run)
            classify_run(session, run, analysis.opened_episodes)
            hypothesize_run(
                session,
                run,
                analysis.opened_episodes,
                hypothesis_provider or NoopHypothesisProvider(),
                top_k=kb_top_k,
                cutoff=kb_similarity_cutoff,
            )
            recompute_flaky_flags(session, window_days=flaky_window_days, threshold=flaky_threshold)
            maybe_notify(
                session,
                run,
                email_sender,
                email_recipients,
                recovery_notice=email_recovery_notice,
            )

    return build


def data_change_window(
    timing_window: tuple,
    lookback: timedelta = timedelta(hours=12),
    tolerance: timedelta = timedelta(minutes=5),
) -> tuple:
    """The UTC window for candidate data changes: a lookback before the run through its end.

    Data changes precede the nightly run (confirmed empirically on #1702 — the run's own window had
    no tracked changes), so we look back from the run start. The ``tolerance`` margin (B1) widens
    both ends to absorb residual clock skew between the Jenkins and Oracle ``ut_ref`` clocks.
    ``lookback`` is a provisional default, tuned on real data later.
    """
    start, end = timing_window
    return start - lookback - tolerance, end + tolerance
