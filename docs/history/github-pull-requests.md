# GitHub pull-request archive

Frozen record of the GitHub pull requests as of the migration to Bitbucket Cloud.
Only `main` was carried over to Bitbucket, so the per-PR branch tips live on in the
read-only GitHub mirror; the *content* of every merged PR is in `main`'s history.

108 merged, 2 closed-unmerged, 110 total.

## Index

| # | State | Branch | Title |
| --- | --- | --- | --- |
| [1](#pr-1) | Merged | `claude/plan-review-f2up64` | docs: refine PLAN.md per review notes |
| [2](#pr-2) | Merged | `slice-0-spike` | Slice 0: end-to-end spike — ingest run #1702, prove formats + clock m… |
| [3](#pr-3) | Merged | `milestone-1-schema` | Milestone 1: full Information-model schema + Alembic migrations |
| [4](#pr-4) | Closed | `claude/next-step-execution-vb4mjx` | Milestone 1: full Information model, Alembic migrations, pg_trgm |
| [5](#pr-5) | Merged | `claude/whats-next-4uox26` | Milestone 2: baseline diff, lifecycle/episodes, classification, poller |
| [6](#pr-6) | Merged | `claude/whats-next-kqyy4y` | Milestone 3: dashboard — triage queue, per-test record, run summary |
| [7](#pr-7) | Merged | `claude/whats-next-f1z36u` | Milestone 4: flakiness, knowledge base, regression email |
| [8](#pr-8) | Merged | `claude/whats-next-aqxd7c` | Milestone 5: LLM root-cause hypothesis (provider + RAG over KB top-k) |
| [9](#pr-9) | Merged | `claude/whats-next-9o6h7y` | Post-v1: ingest the unittest console-log UT stages |
| [10](#pr-10) | Merged | `fix/live-deploy-ingest-dedup-and-poller` | fix: unblock live ingest (JUnit/console-log dedup) + real poller & migrate race |
| [11](#pr-11) | Merged | `feat/backfill-jira-collapsible-detail` | feat: cold-start backfill window, Jira ticket on episodes, collapsibl… |
| [12](#pr-12) | Merged | `perf/ingest-batching-bulk-insert` | perf(ingest): batch per-test N+1s, bulk-insert results, defer flaky r… |
| [13](#pr-13) | Merged | `docs/concept-overview` | docs: concept/architecture overview (HTML) + maintainer agent |
| [14](#pr-14) | Merged | `chore/gh-cli-enablement` | chore(devcontainer): activate gh CLI; close branch-protection + first-PR items |
| [18](#pr-18) | Merged | `docs/15-adopt-issues-workflow` | chore(workflow): migrate task tracking to GitHub Issues; retire PROGRESS.md |
| [21](#pr-21) | Merged | `fix/19-ui-row-cap` | feat(dashboard): cap long test lists with "Load all N Tests" (default 50) |
| [22](#pr-22) | Merged | `fix/20-poller-tolerate-404` | fix(poller): tolerate 404 on a build detail endpoint instead of crashing |
| [24](#pr-24) | Merged | `claude/jenkins-ut-analyzer-23-68bgr8` | feat(dashboard): restyle UI with vendored Bootstrap 5 |
| [26](#pr-26) | Merged | `claude/jenkins-ut-analyzer-25-d426vf` | feat(demo): synthetic dataset + ephemeral demo app + Render hosting |
| [27](#pr-27) | Merged | `claude/jenkins-ut-analyzer-25-d426vf` | fix(render): drop redundant sh -c wrapper from dockerCommand |
| [28](#pr-28) | Merged | `claude/jenkins-ut-analyzer-25-d426vf` | docs: fix retired PROGRESS.md link + note the live demo URL |
| [29](#pr-29) | Merged | `claude/jenkins-ut-analyzer-16-1wjyz4` | feat(dashboard): in-app control panel — runtime tuning + on-demand ingest |
| [30](#pr-30) | Merged | `claude/local-cloud-permissions-jicn4m` | Run the devcontainer prompt-free; make development devcontainer-only |
| [33](#pr-33) | Merged | `claude/section-symbol-references-5uoo97` | docs: retire planning MD files, fold reference into OVERVIEW, drop §N refs |
| [39](#pr-39) | Merged | `chore/38-vscode-run-configs` | chore: add VS Code run configs for rebuild/restart and debug |
| [40](#pr-40) | Merged | `chore/31-parallel-worktrees` | chore(infra): parallel in-container git worktrees for local dev |
| [41](#pr-41) | Merged | `feat/36-episode-failure-details` | feat(dashboard): show failure detail per episode, expand current+open |
| [42](#pr-42) | Merged | `feat/35-timestamp-display` | feat(dashboard): timestamps to seconds precision, wrappable |
| [43](#pr-43) | Merged | `feat/34-flaky-leaderboard-total` | feat(flakiness): show true total on flaky leaderboard |
| [45](#pr-45) | Merged | `docs/44-extension-bypass-note` | docs: note baked bypassPermissions is CLI-only; VS Code extension needs its own toggle |
| [47](#pr-47) | Merged | `claude/jenkins-ut-analyzer-46-ebxjwh` | Add ZEPHYR test case extraction, storage and deep-links (#46) |
| [48](#pr-48) | Merged | `feat/37-job-runs-page` | feat(dashboard): add "Job runs" page listing all ingested runs |
| [56](#pr-56) | Merged | `claude/issue-54-cpywtg` | Enable TLS verification for the Jenkins client by default |
| [57](#pr-57) | Merged | `claude/issue-49-yyfgpi` | feat(analysis): populate suggested_contact from change-candidate authors (#49) |
| [58](#pr-58) | Merged | `claude/issue-51-n8dp9i` | feat(infra): harden the poller — retries, quarantine, real /health, ops alerts, job recovery |
| [59](#pr-59) | Merged | `claude/issue-52-shqdvi` | perf: add data retention/pruning and fix dashboard scale (#52) |
| [60](#pr-60) | Merged | `claude/issue-53-g1czhi` | feat(dashboard): add run-health timeline and per-test flakiness sparklines |
| [61](#pr-61) | Merged | `claude/issue-56-k8d53f` | fix(ingest): stop defaulting unrecognized unittest outcomes to PASSED |
| [62](#pr-62) | Merged | `claude/issue-50-lb6ajh` | feat(analysis): rank change candidates per failing test and feed details to the LLM prompt (#50) |
| [64](#pr-64) | Merged | `claude/issue-63-ntsjpv` | feat(dashboard): triage filters/sort, global search, and bulk actions |
| [66](#pr-66) | Merged | `claude/jenkins-ut-analyzer-65-hmkst8` | Parallelize Jenkins fetch phase to reduce ingest latency (issue #65) |
| [67](#pr-67) | Merged | `claude/issue-17-spec-rework-z4s2k1` | Add flag-gated Keycloak OIDC auth (AUTH_ENABLED, off by default) |
| [69](#pr-69) | Merged | `claude/theme-selector-button-l5ssts` | feat(dashboard): add light/dark theme toggle to the navbar |
| [70](#pr-70) | Merged | `claude/theme-selector-button-l5ssts` | Add light/dark theme toggle to the dashboard |
| [71](#pr-71) | Merged | `claude/app-config-docs-b5aug6` | docs: add Configuration chapter to OVERVIEW.html |
| [74](#pr-74) | Merged | `claude/issue-73-93s75p` | feat(analysis): close the learning loop — AI-accuracy metric, score-aware tie-break, classification confidence |
| [90](#pr-90) | Merged | `fix/80-poller-scheduler-paused` | fix(poller): drop next_run_time=None so the interval job actually fires |
| [91](#pr-91) | Merged | `fix/81-email-outside-ingest-txn` | fix(ingest): send the regression alert after the ingest transaction commits |
| [92](#pr-92) | Merged | `fix/82-lifecycle-out-of-order-reingest` | fix(analysis): never drive the lifecycle from a historical re-ingest |
| [93](#pr-93) | Merged | `fix/83-shard-status-completeness` | fix(ingest): require every UT shard to finish before marking a run complete |
| [94](#pr-94) | Merged | `fix/84-triage-track-filter` | fix(dashboard): match the triage track filter against every failing track |
| [95](#pr-95) | Merged | `fix/85-unittest-log-fail-block` | fix(ingest): let a FAIL/ERROR block override a garbled status-line outcome |
| [96](#pr-96) | Merged | `fix/86-infra-regex-word-boundaries` | fix(analysis): anchor INFRA regex tokens so substring hits can't fake an infra fault |
| [97](#pr-97) | Merged | `fix/87-oracle-dst-fold` | fix(ingest): make ut_ref CREDATIM window bounds and row conversion DST-fold-safe |
| [98](#pr-98) | Merged | `fix/88-csrf-protection` | fix(dashboard): reject cross-site unsafe-method requests app-wide (CSRF) |
| [99](#pr-99) | Merged | `fix/89-demo-control-lockdown` | fix(demo): lock down control-panel mutations in the public demo (403) |
| [100](#pr-100) | Merged | `feat/75-flash-feedback` | feat(dashboard): flash feedback for every mutating action |
| [101](#pr-101) | Merged | `feat/76-bulk-selection` | feat(dashboard): bulk-selection ergonomics on the triage queue |
| [102](#pr-102) | Merged | `feat/77-instant-filters` | feat(dashboard): instant, self-describing triage filters |
| [103](#pr-103) | Merged | `feat/78-htmx-job-polling` | feat(dashboard): auto-refresh ingest jobs via vendored HTMX polling |
| [104](#pr-104) | Merged | `feat/79-orientation-polish` | feat(dashboard): active nav state, triage-count badge, relative timestamps |
| [105](#pr-105) | Merged | `docs/overview-sync-review-fixes` | docs: sync OVERVIEW.html with the review-fix batch |
| [107](#pr-107) | Merged | `claude/app-value-proposals-kvr42p` | feat(dashboard): signature-level bulk attribution |
| [109](#pr-109) | Closed | `claude/issue-73-93s75p` | feat(analysis): close the learning loop — AI accuracy, score-aware tie-break, confidence |
| [110](#pr-110) | Merged | `claude/app-value-proposals-kvr42p` | feat(email): dashboard deep links in alert emails |
| [111](#pr-111) | Merged | `feat/72-last-ingested-run-triage` | feat(dashboard): show last ingested run on Triage screen |
| [113](#pr-113) | Merged | `docs/112-auth-config-guide` | docs: auth/Keycloak config guide + broaden docs-overview-maintainer to own config docs |
| [128](#pr-128) | Merged | `fix/115-log-stage-completeness` | fix(ingest): unfinished unittest console-log stage marks run incomplete |
| [129](#pr-129) | Merged | `fix/118-recovery-notice-transition` | fix(email): send recovery notice only on the red-to-green transition |
| [130](#pr-130) | Merged | `fix/117-removed-reappear` | fix(analysis): close open episode when a REMOVED test reappears passing |
| [131](#pr-131) | Merged | `fix/119-oracle-null-columns` | fix(ingest): stop stringifying NULL V_TRACKING columns to "None" (#119) |
| [133](#pr-133) | Merged | `fix/124-shard-correlated-track` | fix(flakiness): require same-track consistency for shard_correlated |
| [134](#pr-134) | Merged | `fix/123-search-limit-zero` | fix(dashboard): make test_search honor limit<=0 as "no cap" (#123) |
| [135](#pr-135) | Merged | `fix/122-idempotent-seed` | fix(demo): make control-state seeding idempotent on re-seed |
| [136](#pr-136) | Merged | `fix/120-smtp-auth` | fix(email): wire SMTP credentials into SmtpEmailSender with STARTTLS + login |
| [137](#pr-137) | Merged | `fix/121-guard-ops-alert` | fix(infra): make send_ops_alert best-effort so SMTP outages can't break /health or the tick record |
| [138](#pr-138) | Merged | `fix/127-health-never-succeeded` | fix(infra): make /health report a never-succeeded poller stale (#127) |
| [139](#pr-139) | Merged | `fix/126-retrieval-provenance` | fix(kb): rank and label similar cases by the strongest of both provenance columns |
| [140](#pr-140) | Merged | `fix/125-demo-health-staleness` | fix(demo): re-stamp seeded heartbeat on /health so the demo never goes stale |
| [141](#pr-141) | Merged | `fix/116-orphaned-signature-aggregates` | fix(kb): recompute orphaned signature aggregates on re-ingest |
| [142](#pr-142) | Merged | `fix/132-expand-preserves-filters` | fix(dashboard): make triage "Load all" expand links preserve filters and sort |
| [146](#pr-146) | Merged | `feat/143-keep-your-place-nav` | feat(dashboard): keep-your-place navigation — back-links + episode anchors |
| [147](#pr-147) | Merged | `fix/144-status-not-color-alone` | fix(dashboard): pass/fail readable without color + explicit UTC timestamps |
| [148](#pr-148) | Merged | `feat/145-triage-error-snippet` | feat(dashboard): error snippets in triage queue + trace clamp/copy on test record |
| [149](#pr-149) | Merged | `docs/overview-triage-error-snippet` | docs: reflect triage-queue error snippets + trace clamp in OVERVIEW.html |
| [153](#pr-153) | Merged | `fix/151-url-state-run-diff` | fix(dashboard): preserve ?expand= across filter/sort; cap run-diff lists with counts |
| [154](#pr-154) | Merged | `fix/150-triage-action-trust` | fix(dashboard): trustworthy triage actions — ack anchors, truthful bulk flash, disable-on-submit, toast flashes |
| [155](#pr-155) | Merged | `feat/152-signature-blast-radius` | feat(dashboard): show blast-radius count on "Ack all w/ signature (N)" |
| [156](#pr-156) | Merged | `docs/overview-signature-ack-consistency` | docs: align web-card signature-ack wording with the (N) blast-radius button |
| [160](#pr-160) | Merged | `claude/in-app-user-docs-900ywx` | Add in-app Help page (workflow, statuses, LLM feedback loop) |
| [162](#pr-162) | Merged | `feat/159-classification-evidence` | feat(dashboard): render classification evidence — "Why this prediction" on the test record |
| [163](#pr-163) | Merged | `feat/157-pivot-links` | feat(dashboard): linkify owner/suite/cause, clickable failed count, cross-referring search empty states |
| [164](#pr-164) | Merged | `docs/help-page-catchup-157-159` | docs(help): document the evidence panel, pivot links, failed-count deep-link and search cross-referral |
| [165](#pr-165) | Merged | `feat/114-owner-main-developer` | Owner = main developer (SVN blame), not the ZEPHYR test-case author (#114) |
| [167](#pr-167) | Merged | `fix/166-svn-cli-in-image` | Install subversion in the Docker image so owner blame works (#166) |
| [169](#pr-169) | Merged | `feat/168-owner-still-failing-and-record` | feat(dashboard): show Owner in the still-failing bucket and as a pivot link on the record page |
| [170](#pr-170) | Merged | `docs/112-config-docs-guardrail` | docs: give docs-overview-maintainer a third surface — the config reference |
| [173](#pr-173) | Merged | `claude/add-skills-to-repo-yp1pti` | Add domain-modeling skills, initialize CONTEXT.md, and rename Run → Build |
| [175](#pr-175) | Merged | `claude/shards-vs-track-language-of47v6` | Rename shard → track: one term for the parallel lanes |
| [176](#pr-176) | Merged | `claude/rename-build-permanent-pipeline-a2inys` | Correct "nightly build" language: the analyzed pipeline is the Permanent Pipeline (per commit) |
| [179](#pr-179) | Merged | `claude/grill-with-docs-synonym-eome9r` | Accept "Jenkins run"/"pipeline run" as prose synonyms for Build |
| [180](#pr-180) | Merged | `claude/grill-with-docs-lfalg8` | perf: build-boundary data-change window; re-derive retention estimate |
| [182](#pr-182) | Merged | `claude/jenkins-ut-analyzer-docs-qh7gxd` | feat: add Build Incident triage for pipeline-level build failures |
| [183](#pr-183) | Merged | `claude/jenkins-ut-analyzer-docs-qh7gxd` | docs(adr): record ADR-0005 for the Build Incident entity |
| [186](#pr-186) | Merged | `claude/grill-with-docs-ticket-1t5cg3` | docs: record ADR-0006 + CONTEXT.md terms for the #172 split (overrunning builds) |
| [187](#pr-187) | Merged | `claude/issue-184-injebd` | feat: visualize overrunning in-progress pipelines |
| [188](#pr-188) | Merged | `claude/grill-with-docs-181-gt716z` | Multi-channel alerting: Microsoft Teams webhook channel |
| [190](#pr-190) | Merged | `claude/grill-with-docs-189-wgr4eo` | feat: search the triage queue by failure detail |
| [192](#pr-192) | Merged | `chore/191-remove-suite-filter` | chore(dashboard): remove the triage queue's Suite filter |
| [193](#pr-193) | Merged | `claude/global-test-search-enhancements-pgajmz` | Add failure-episode status and sorting to global test search |

## Pull requests

<a id="pr-1"></a>

### #1 — docs: refine PLAN.md per review notes

- **State:** Merged
- **Branch:** `claude/plan-review-f2up64` → `main`
- **Opened:** 2026-06-26 · **Merged:** 2026-06-26
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/1

> - Reframe cause attribution: v1 commits to time-window candidate
>   filtering (human attributes); relevance ranking + confidence score
>   deferred to a KB-fed enhancement
> - Add clock/timezone discipline (UTC-on-ingest, recorded source clock,
>   tolerance margin) for data-change windowing
> - Flakiness: treat incomplete/absent runs as gaps, not state transitions
> - Promote UT-report/SVN-output parsing to a blocking first milestone
> - Mark automatic alias suggestion as post-v1; manual merge ships in v1
>
> Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
> Claude-Session: https://claude.ai/code/session_01Y4absVHK2aPjYgXQw1RRuU


<a id="pr-2"></a>

### #2 — Slice 0: end-to-end spike — ingest run #1702, prove formats + clock m…

- **State:** Merged
- **Branch:** `slice-0-spike` → `main`
- **Opened:** 2026-06-27 · **Merged:** 2026-06-27
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/2

> …odel
>
> Stands up the load-bearing layer against real build #1702 data:
>
> - clock.py: Jenkins-UTC + ut_ref Europe/Luxembourg (DST-aware) normalization, with naive<->aware guards. Empirically verified live (naive-local 15:46 -> 13:46Z).
> - Parsers (golden-tested vs anonymized fixtures): ut_report (devUTs JUnit, per-(test,track), file/line + ZEPHYR owner), svn_update (changeSets), wfapi (per-shard timing + completeness + run window).
> - External boundaries behind interfaces + offline fakes: jenkins (HttpJenkinsClient), refdb/oracle (OracleTrackingFeed, MODDATA never selected), llm (no-op stub).
> - Ingest pipeline (idempotent), minimal schema (Run / TestResult keyed by run,test,track), read-only web view, Typer CLI (init-db / backfill).
> - Two-tier tests: 30 offline (pytest -m "not live", the merge gate) + 3 live (local only). ruff clean.
> - Container/CI: Dockerfile (single image), docker-compose (web/poller/db), GitHub Actions (ruff + offline suite + Postgres service).
> - Docs: CLAUDE.md operating contract, docs/PROGRESS.md durable checklist.
>
> Live-verified: docker compose up + `uta backfill 1702` -> 25,592 results (counts match source), run window UTC-normalized, /runs/1702 renders, V_TRACKING lookback returns 436 candidates with tz proven.


<a id="pr-3"></a>

### #3 — Milestone 1: full Information-model schema + Alembic migrations

- **State:** Merged
- **Branch:** `milestone-1-schema` → `main`
- **Opened:** 2026-06-27 · **Merged:** 2026-06-27
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/3

> Replace the minimal Slice-0 schema with the complete Information model (PLAN.md §"Information model") behind Alembic migrations.
>
> Schema (src/uta/models/, one module per concern):
> - Run + RunShard (per-shard timing/completeness, totals, baseline flag)
> - TestIdentity (test-level; alias_of self-ref for rename history)
> - TestResult keyed (run, identity, track); track is an attribute
> - TestLifecycle (state + flaky + reopen_count + acknowledgement)
> - FailureEpisode (one per fail→fix cycle; current_episode via use_alter)
> - Attribution (cause/reason + provenance tier + original-AI value + validator)
> - Classification (cause / nullable confidence / LLM hypothesis)
> - CodeChangeCandidate + DataChangeCandidate (run-windowed signals; MODDATA never stored)
> - FailureSignature (normalized text + hash + pg_trgm GIN index)
>
> Migrations & startup:
> - Alembic env.py wired to Base.metadata + DATABASE_URL (12-factor)
> - Initial migration creates all 11 tables, CREATE EXTENSION pg_trgm, the gin_trgm_ops GIN index, and the lifecycle↔episode circular FK
> - assert_pg_trgm() startup guard (web lifespan + uta migrate/backfill)
> - `uta migrate` (alembic upgrade head) replaces create_all; init-db aliases it
>
> Decisions (documented in models): actor is a string field on every human action (no users table; Phase-2 Keycloak swaps the value); failure history is test_results across runs (no separate table); candidate signals are run-windowed, not per-test, in v1.
>
> Pipeline now populates identities/shards/totals against the new schema.
>
> Tests: test_models.py (SQLite — relationships, constraints, defaults, alias, failure-history, cascade) + test_migrations.py (real Postgres, skip-if-absent so the offline gate stays green; runs in CI via services: Postgres). Verified against real Postgres: upgrade/downgrade round-trips clean, no alembic drift, pg_trgm + GIN + similarity() live. Offline suite: 42 passed; ruff clean.
>
> Also: note the PROGRESS.md update obligation in CLAUDE.md.


<a id="pr-4"></a>

### #4 — Milestone 1: full Information model, Alembic migrations, pg_trgm

- **State:** Closed
- **Branch:** `claude/next-step-execution-vb4mjx` → `main`
- **Opened:** 2026-06-27
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/4

> Expands the minimal Slice 0 schema into the complete Information model defined in PLAN.md, wired up with Alembic and the pg_trgm extension:
>
> Schema additions (all backward-compatible — existing test_results.test_id kept; new columns nullable or with server defaults):
> - Run.baseline_run_id (self-FK, nullable) — records which run was used as baseline when this run was processed
> - RunShard — per-shard (permanent / permanent_py39) start/finish timing
> - TestIdentity — stable canonical test key across runs, tracks, renames; alias_of_id self-FK + alias_confirmed for rename/move tracking
> - TestResult — adds test_identity_id FK (nullable) + error_stack_trace
> - TestLifecycle — state (FAILING/FIXED/REMOVED), flaky flag, reopen_count, acknowledgement (flag + actor + timestamp), all orthogonal to each other
> - FailureEpisode — one row per fail→fix cycle; carries full attribution (cause, reason, provenance tier, original_ai_value, confirmed_by, causing_person, triage_status)
> - RunSignal — candidate SVN/data-change signals per run window
> - TestClassification — deterministic predicted cause + LLM hypothesis slot
> - KbSignature — normalized failure text + SHA-256 hash for exact lookup; GIN/pg_trgm index on sig_text for fuzzy similarity search
>
> Alembic setup:
> - alembic.ini + env.py reading DATABASE_URL from environment
> - 0001_initial_schema.py: full up/down migration including CREATE EXTENSION IF NOT EXISTS pg_trgm and the GIN index
>
> db.py: assert_pg_trgm() — raises RuntimeError if pg_trgm is absent on Postgres (no-op on SQLite for offline tests)
>
> Tests (20 new model tests + 7 migration tests):
> - test_models.py: SQLite-only, covers every table, constraint, FK, and lifecycle state transition; gate remains green with zero external deps
> - test_migrations.py: Alembic up/down, pg_trgm presence, GIN index, similarity() query; auto-skips when DATABASE_URL is not Postgres so the offline suite stays green; runs against the CI Postgres service
>
>
> Claude-Session: https://claude.ai/code/session_01FYJnPjS1Tj7v1UXp2titNG


<a id="pr-5"></a>

### #5 — Milestone 2: baseline diff, lifecycle/episodes, classification, poller

- **State:** Merged
- **Branch:** `claude/whats-next-4uox26` → `main`
- **Opened:** 2026-06-27 · **Merged:** 2026-06-27
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/5

> Turn accumulated runs into the cross-run picture (PLAN §1/§2), all derived
> from persisted facts so re-running the analysis is idempotent.
>
> New `uta.analyze` package:
> - baseline.py — select most-recent *complete* baseline (incomplete runs stored
>   but skipped); collapse both tracks to a per-identity status; diff into
>   regressions / newly-fixed / still-failing / removed, stamping baseline_run_id.
> - lifecycle.py — apply_run drives FAILING/FIXED/REMOVED + failure episodes vs
>   the baseline (not the stored state → idempotent per (baseline, run)). Reopen
>   bumps reopen_count and clears acknowledgement; fix closes the episode only on
>   a real pass (never on REMOVED); age/first-failure pointers maintained. Only
>   ever-failing tests get a lifecycle row.
> - classify.py — deterministic INFRASTRUCTURE > CODE_CHANGE/DATA_CHANGE > UNKNOWN
>   per new episode, from windowed candidates; no confidence (deferred to §4),
>   evidence JSON records candidate counts.
> - error_type.py — ASSERTION/EXCEPTION/TIMEOUT/INFRA/UNKNOWN from status + trace.
>
> Pipeline now persists code-change candidates (SVN changeSets) and data-change
> candidates (ut_ref feed, when supplied) over the lookback + B1 tolerance window,
> sets per-result error_type, and runs the analysis for complete runs — clearing
> and rebuilding on re-ingest without duplicating episodes/classifications.
>
> Scheduled poller (poller.py + `uta poll`): DB-resident high-water mark
> (max build_number) drives which new completed builds to ingest, oldest-first,
> on an APScheduler interval; `uta backfill <build> [--to N]` ingests a range.
> last_completed_build added to the Jenkins client + fake.
>
> No schema change (all columns exist from M1, so no new migration). Offline gate
> green: 69 passed, 3 skipped; ruff lint + format clean.
>
> Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
> Claude-Session: https://claude.ai/code/session_01R2m8heAPqZ8k3R5AZWLEzr


<a id="pr-6"></a>

### #6 — Milestone 3: dashboard — triage queue, per-test record, run summary

- **State:** Merged
- **Branch:** `claude/whats-next-kqyy4y` → `main`
- **Opened:** 2026-06-27 · **Merged:** 2026-06-27
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/6

> Adds the FastAPI dashboard (PLAN §0/§1/§2) on top of the M2 analysis:
>
> - §0 triage queue (GET /): three buckets as a pure projection of lifecycle
>   state × the orthogonal acknowledgement attribute — New (unacknowledged,
>   newest-first), Still-failing (acknowledged + REMOVED-with-open-episode
>   flagged), Recently-fixed (within RECENTLY_FIXED_DAYS).
> - §1 per-test record (GET /tests/{id}): lifecycle, every failure episode,
>   latest failing result + stack/location/links, and the candidate code/data
>   changes in the failure window.
> - §2 run summary (GET /runs/{build}): totals, per-shard timing, baseline +
>   diff (regressions/newly-fixed/still-failing/removed) linking to records.
> - Phase-1 self-declared identity (uta_actor cookie, default test-user) shown
>   in the header; every action stamped with it.
> - Actions with provenance: Acknowledge, one-click Confirm (AI_CONFIRMED),
>   and edit cause/reason/triage (AI_CONFIRMED / HUMAN_CORRECTED w/ original
>   retained / HUMAN_ENTERED). Post/Redirect/Get; logic in web/views+actions,
>   templates never touch a live session.
>
> Read-side projections normalize SQLite-naive vs Postgres-aware datetimes so
> window comparisons never mix tz. Adds python-multipart for form parsing.
>
> Tests: +19 (offline gate 88 passed, 3 skipped); ruff lint + format clean.
>
> Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
> Claude-Session: https://claude.ai/code/session_01DpG9mcWFg2Q3tRgqtYBwqw


<a id="pr-7"></a>

### #7 — Milestone 4: flakiness, knowledge base, regression email

- **State:** Merged
- **Branch:** `claude/whats-next-f1z36u` → `main`
- **Opened:** 2026-06-27 · **Merged:** 2026-06-27
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/7

> Oscillation flakiness (§3), KB signatures + recurrence/similarity (§4), and
> regression-only email (§5). No migration needed — the M1 schema already shipped
> failure_signatures (+ trigram GIN), signature_id FKs and the lifecycle flaky flag.
>
> - kb/signature.py: named, test-covered normalization (exception type + top-N
>   our-package frames, track prefix stripped; UUID/TS/IP:PORT/HEX/NUM masks) + hash.
> - kb/store.py: upsert + link a signature per failing result at ingest; occurrence
>   and first/last-seen recomputed from live links (idempotent re-ingest).
> - kb/retrieval.py: exact recurrence by hash; pg_trgm similarity with a difflib
>   fallback offline; provenance-weighted ranking. Attributions now link to the
>   episode's signature so confirmed/entered reasons feed retrieval.
> - analyze/flakiness.py: oscillation score (transitions/runs), gaps not flips,
>   flaky only when 0<fail-rate<1 and score>=threshold; shard correlation + pattern;
>   recompute_flaky_flags + leaderboard.
> - delivery/email.py: EmailSender + SmtpEmailSender + fake; regression-only report
>   (recovery-notice toggle). Wired into the poller (live); back-fill sends nothing.
> - web: /flaky leaderboard, /kb search, flakiness + recurrence cards on the test
>   record, nav links. Config + .env.example: FLAKY_WINDOW_DAYS, KB_TOP_K, SMTP.
>
> Offline gate: 119 passed, 3 skipped; ruff lint + format clean (+31 tests).
>
> Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
> Claude-Session: https://claude.ai/code/session_01TYVKomiqJtAJMAqxGW4oUN


<a id="pr-8"></a>

### #8 — Milestone 5: LLM root-cause hypothesis (provider + RAG over KB top-k)

- **State:** Merged
- **Branch:** `claude/whats-next-aqxd7c` → `main`
- **Opened:** 2026-06-27 · **Merged:** 2026-06-27
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/8

> Fill Classification.llm_hypothesis (shipped empty since M1) with a one-line,
> LLM-generated root-cause guess for each newly-opened failure episode, grounded
> in the top-k similar past cases the knowledge base already retrieves. No
> migration; no vector store — "RAG" is the existing pg_trgm/difflib retrieval
> rendered into a prompt.
>
> - llm/__init__.py: HypothesisProvider widened to hypothesize(system, user);
>   NoopHypothesisProvider stays the default (no key ⇒ no model call ⇒ NULL).
> - llm/prompt.py: pure, offline-tested prompt builder (failing test + deterministic
>   prior + retrieved validated conclusions; error/stack capped; no raw MODDATA).
> - llm/claude.py: AnthropicHypothesisProvider (official SDK, claude-opus-4-8),
>   local import so the offline path never loads the SDK; API errors → None.
> - analyze/hypothesize.py: hypothesize_run runs after the pure classify_run;
>   no-op under Noop. Wired into the pipeline's complete-run block.
> - poller passes the real provider; back-fill passes none (history never
>   re-hypothesised — same caller-side idempotency as the email path).
> - config + .env.example: ANTHROPIC_API_KEY, LLM_MODEL; anthropic dependency.
> - Tests (+10, offline gate green: 129 passed, 3 skipped): prompt rendering,
>   hypothesize wiring (Noop/real/declining/retrieval), pipeline coverage, and a
>   live-marked real-provider test (skipped in CI). ruff clean.
>
> Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
> Claude-Session: https://claude.ai/code/session_01TW7QRh5oKbavH1PsQkKu26


<a id="pr-9"></a>

### #9 — Post-v1: ingest the unittest console-log UT stages

- **State:** Merged
- **Branch:** `claude/whats-next-9o6h7y` → `main`
- **Opened:** 2026-06-28 · **Merged:** 2026-06-28
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/9

> Add the second ingest source the v1 plan deferred: the unittest stages
> (SMB Pricing/Transform, ITF Highlevel, LXS, Uniface deploy unit tests)
> that run inside Jenkins Shell Script steps and report results only in
> their stage console log — no JUnit artifact. Built behind the existing
> ingest interface; no schema change, no redesign.
>
> - ingest/unittest_log.py: parse verbose unittest console text into the
>   same TestCaseResult the JUnit parser emits (outcome mapping, ====
>   traceback blocks -> details/stack/first-frame file:line, 3.11+ identity
>   normalization; tolerates non-verbose runs).
> - wfapi.find_unittest_stages: discover "<suite> - <track>" stages by a
>   configurable suite allowlist (excludes devUTs and non-test stages).
> - JenkinsClient.stage_log(build, node_id) on the protocol + HTTP client;
>   fake serves stagelog_<build>_<node>.json fixtures.
> - Pipeline appends console-log cases to the JUnit cases before persisting,
>   so they share the identity/lifecycle/episode/classification/signature/
>   flakiness path. Off by default (devUTs path unchanged); idempotent on
>   re-ingest. Threaded through poller + CLI; INGEST_UNITTEST_STAGES (default
>   on) / UNITTEST_SUITES drive the live paths.
> - Anonymized golden fixtures (medical data redacted) + 13 offline tests
>   (parser, stage discovery, wired pipeline) -> 148 passed, 3 skipped.
>
> Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
> Claude-Session: https://claude.ai/code/session_0154k1ZCTh1fpGFiHmWj4vRc


<a id="pr-10"></a>

### #10 — fix: unblock live ingest (JUnit/console-log dedup) + real poller & migrate race

- **State:** Merged
- **Branch:** `fix/live-deploy-ingest-dedup-and-poller` → `main`
- **Opened:** 2026-06-29 · **Merged:** 2026-06-29
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/10

> First live run on the VM (empty DB, default config) had an empty triage queue.
> Root cause + two fixes:
>
> ### 1. Duplicate-(test_id, track) ingest crash
> With INGEST_UNITTEST_STAGES on (default), build #1707 hit a UniqueViolation on
> uq_run_test_track and the whole run rolled back → empty DB → blank triage. The
> unittest console-log stages are NOT disjoint from the devUTs nose2 surface (nose2
> also collects some of the modules those stages run), so the same test is reported
> by both sources in one build. `pipeline._dedupe_cases` now collapses duplicate
> (test_id, track) to the first occurrence — JUnit (authoritative) is listed first
> and wins; console-log fills only the gaps. Dropped keys are logged.
>
> ### 2. Poller didn't poll + cold-start migrate race
> The compose poller was still the Slice-0 placeholder (`init-db && sleep infinity`),
> and web + poller both ran Alembic at startup → race on CREATE TABLE alembic_version
> (poller crashed). A one-shot `migrate` service now owns schema migration; web
> (uvicorn only) and poller (`uta poll`) depend on it via service_completed_successfully.
>
> Offline gate green: 156 passed, 3 skipped. Verified live: migrate exits 0, poller
> polls every 300s without crashing.
>
> ### Known follow-up (not in this PR)
> Poller cold-start mass-ingest: on a truly empty DB, builds_to_ingest returns
> range(1, latest+1) and would try every historical build. Back-fill a recent
> baseline first, or add a range floor — tracked in docs/PROGRESS.md.


<a id="pr-11"></a>

### #11 — feat: cold-start backfill window, Jira ticket on episodes, collapsibl…

- **State:** Merged
- **Branch:** `feat/backfill-jira-collapsible-detail` → `main`
- **Opened:** 2026-06-30 · **Merged:** 2026-06-30
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/11

> …e test-detail page
>
> Three enhancements to make the tool usable from scratch and close gaps in the failure-episode workflow.
>
> Cold-start backfill (poller, cli, config):
> - builds_to_ingest now floors a fresh (empty) store to the last BACKFILL_DEPTH builds (default 10), oldest-first, instead of trying every historical build from #1. Incremental selection above the high-water mark is unchanged once the store is non-empty. Depth threaded through poll_once/run_scheduler/`uta poll`.
> - New `uta bootstrap [--depth N]` populates the same window on demand (no email/LLM, like backfill).
>
> Jira ticket on failure episodes (model, migration, web):
> - New nullable failure_episodes.jira_ticket (migration 4f1a2b3c5d6e), human-entered via the per-episode Save form alongside cause/reason/triage. Set directly on the episode (not a provenance-tracked Attribution conclusion); empty submission clears it. Rendered as a link to {JIRA_BASE_URL}/browse/<TICKET>.
>
> Test-detail page UX (test_record.html, base.html):
> - Every section is now a native <details>/<summary> collapsible (no JS). Default-open: Lifecycle, Failure episodes, Latest failure; collapsed: Flakiness, Knowledge base, Candidate changes. Failure episodes moved to directly after Lifecycle.
> - SVN revisions link into FishEye ({FISHEYE_CHANGELOG_URL}?cs=<rev>).
> - New config JIRA_BASE_URL / FISHEYE_CHANGELOG_URL, exposed to every page via the render context.
>
> Tests (+6): cold-start window (last-N oldest-first / from-1 / non-empty unchanged), set_attribution jira_ticket set+clear, web Jira link, collapsible
> + reorder, FishEye link. Offline gate green (162 passed, 3 skipped), ruff clean. Migration upgrade/downgrade/re-upgrade verified on live Postgres.
>
> Docs: PLAN, PROGRESS, .env.example, CLAUDE.md updated.


<a id="pr-12"></a>

### #12 — perf(ingest): batch per-test N+1s, bulk-insert results, defer flaky r…

- **State:** Merged
- **Branch:** `perf/ingest-batching-bulk-insert` → `main`
- **Opened:** 2026-07-01 · **Merged:** 2026-07-01
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/12

> …ecompute
>
> Cold-start refill of 10 builds (~25.6k results/build, ~1k failing tests/build) took ~4-6 min/build. Profiling showed the cost was per-test N+1 round-trips and row-by-row ORM inserts, not slow queries. Now ~13s/build (~20-25x faster; full 10-build refill ~2-3 min). Verified by wiping + refilling the dev Postgres and reading the new per-build timing logs.
>
> - Defer flaky recompute during backfill: recompute_flaky_flags walked all ~2,135 lifecycle rows (one query each) every build. Add ingest_build(recompute_flaky=) and have backfill/bootstrap pass False per build, recomputing once after the loop.
> - Batch the per-test N+1s: identity resolution (one chunked canonical_name IN(...) preload vs ~12.8k SELECTs/build); apply_run (preload lifecycles/open-episodes/ counts + one failing-run-starts scan for age, single flush); signatures (chunked hash preload + batched signature_id write-back + one grouped aggregate recompute).
> - Bulk-insert results via session.execute(insert(TestResult), rows) instead of ~25.6k ORM appends; record_signatures_for_run reads the run's failing results via query (run.results is unpopulated after a Core insert). persist is now the dominant phase (~7-10s of real write + index maintenance).
> - Add composite index ix_test_results_identity_run (test_identity_id, run_id) (migration a1b2c3d4e5f6) for the identity->run joins.
> - Per-build timing logs in ingest_build (fetch/parse/persist/signatures/lifecycle/ classify/flaky). alembic/env.py passes disable_existing_loggers=False and the CLI re-asserts the uta logger to INFO after migrations so the lines emit.
>
> Behavior/idempotency preserved: the 8 guardrail suites (lifecycle, pipeline, flakiness, kb, baseline_diff, poller, dashboard_views, web_dashboard) stay green.
>
> Also fix a pre-existing date-sensitive test (test_web_m4::test_flaky_leaderboard_ lists_oscillating_test): its fixture used a fixed 2026-06-01 epoch that aged out of the 30-day flaky window, failing on later run dates. Runs are now anchored to now.
>
> Offline gate: 162 passed, 3 skipped, ruff clean.


<a id="pr-13"></a>

### #13 — docs: concept/architecture overview (HTML) + maintainer agent

- **State:** Merged
- **Branch:** `docs/concept-overview` → `main`
- **Opened:** 2026-07-01 · **Merged:** 2026-07-01
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/13

> Add docs/OVERVIEW.html — a self-contained, schematic overview of the app: its purpose, the parts involved (Jenkins, Oracle ut_ref, PostgreSQL, the web/poller/migrate/db containers, LLM, SMTP, FishEye/Jira deep-links) with a system-map SVG, and the ingest → analysis → triage → learning → alert workflows.
>
> Add a docs-overview-maintainer subagent that keeps that page (prose + SVG) in sync with the product, and a required note in CLAUDE.md instructing that any change to the app's parts, communications, or workflows invoke it.


<a id="pr-14"></a>

### #14 — chore(devcontainer): activate gh CLI; close branch-protection + first-PR items

- **State:** Merged
- **Branch:** `chore/gh-cli-enablement` → `main`
- **Opened:** 2026-07-03 · **Merged:** 2026-07-03
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/14

> ## What
>
> `gh` is now installed and authed in the devcontainer (github-cli feature, account `palmkevin`), which unblocks the two long-open Slice-0 checklist items. This is also the **first PR created via `gh pr create`** (all prior PRs went through the web-URL flow, since `gh` wasn't available).
>
> ## Changes
> - **`.devcontainer/devcontainer-lock.json`** — lock the `github-cli` devcontainer feature.
> - **`.claude/settings.json`** — keep the `gh repo *` allow-rule.
> - **`CLAUDE.md`** — rescope the stale "no `gh` CLI on this host" note: `gh` is available in the devcontainer; the bare VM host still has none (fall back to local merge / web-URL PR there).
> - **`docs/PROGRESS.md`** — mark the gh-CLI add done; close both Slice-0 "Open" items:
>   - _First branch + PR_ — done long ago via the web flow; now also driven from the terminal.
>   - _CI required status on protected `main`_ — enabled via `gh api` (see below).
>
> ## Branch protection (applied out-of-band via `gh api`)
> `main` now requires the CI job **`test`** as a status check (strict / up-to-date-before-merge). `enforce_admins` is **off** so the owner keeps a direct-push hotfix path; no required reviews (solo). Editable/removable via the same endpoint.
>
> ## Not included
> The two untracked proposal docs (`docs/KEYCLOAK-INTEGRATION.md`, `docs/PROPOSAL-3-CONTROL-PANEL.md`) are intentionally left out of this PR.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)


<a id="pr-18"></a>

### #18 — chore(workflow): migrate task tracking to GitHub Issues; retire PROGRESS.md

- **State:** Merged
- **Branch:** `docs/15-adopt-issues-workflow` → `main`
- **Opened:** 2026-07-03 · **Merged:** 2026-07-03
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/18

> Task status now lives in GitHub Issues (open todos + closed-issue/PR history),
> driven via gh. Each change is a branch + PR that 'Closes #N'; the closed issue +
> merged PR is the record, replacing the hand-maintained PROGRESS.md checklist.
>
> - Delete docs/PROGRESS.md (zero open todos remained; all items done).
> - Relocate its 'Notes / decisions discovered during build' section into
>   docs/IMPLEMENTATION-PLAN.md (durable design rationale, not status).
> - CLAUDE.md: point 'Read these first' at Issues; add a 'Task workflow
>   (GitHub Issues + PR)' section (issue/branch/Closes-#N/label conventions,
>   public-repo hygiene, worktrees deferred).
> - README.md: replace the PROGRESS.md link with the Issues pointer.
> - Add .github/pull_request_template.md enforcing a 'Closes #' line.
> - settings.json: allow git checkout (used by the branch workflow).
>
> The planned-work docs (Control Panel, Keycloak) became tracking issues
> #16/#17; this migration is tracked by #15.
>
> Closes #15
>
> Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>


<a id="pr-21"></a>

### #21 — feat(dashboard): cap long test lists with "Load all N Tests" (default 50)

- **State:** Merged
- **Branch:** `fix/19-ui-row-cap` → `main`
- **Opened:** 2026-07-03 · **Merged:** 2026-07-03
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/21

> Caps each dashboard section at `ui_row_limit` rows (default **50**) with a
> "Load all N Tests" link that re-requests the page with `?expand=<section>` to
> render one section in full while the rest stay capped. Keeps huge lists — the
> ~25k-row §2 run-results surface — responsive.
>
> Brings the previously-unmerged UI-cap feature branch to `main`, with the
> default lowered from 100 → 50.
>
> - config: `ui_row_limit` setting (0 disables the cap), default 50.
> - views: `_cap()` helper; `triage_queue` caps the three buckets; `run_summary`
>   caps the results table before projection; both honor an `expand` set.
> - app: parse `?expand=`, thread `limit`/`expand` into views.
> - templates: shared `more_hint` macro; section ids + hints; `.more` styling.
> - tests: view- and HTTP-level coverage of cap / expand / limit=0.
>
> ## Acceptance check
> - Offline suite green (`pytest -m "not live"`): 171 passed locally.
> - Sections beyond 50 rows render capped with a working "Load all N Tests" link.
>
> Closes #19


<a id="pr-22"></a>

### #22 — fix(poller): tolerate 404 on a build detail endpoint instead of crashing

- **State:** Merged
- **Branch:** `fix/20-poller-tolerate-404` → `main`
- **Opened:** 2026-07-03 · **Merged:** 2026-07-03
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/22

> ## Problem
> The poller crash-looped when Jenkins reported a `lastCompletedBuild` whose detail endpoint returns **404**: `build_meta()` raised `httpx.HTTPStatusError`, which propagated uncaught through `poll_once`. Because the startup `_tick()` runs before `scheduler.start()`, the exception killed the process before the scheduler was ever established — so it could never recover on the next interval.
>
> ## Fix
> `poll_once` now catches a **404 per build**: it logs a warning, skips that build, and continues to the next one, so the poll pass (and the scheduler) stay alive. Any non-404 HTTP error still propagates as a real fault.
>
> **High-water mark:** no `Run` is persisted for the vanished build, so the mark stays unadvanced *for that build*. A later successful build advances the mark past the gap, so the missing build (gone from retention for good) is never retried.
>
> ## Tests
> - New `test_poll_once_skips_build_with_404_detail`: a fake whose `build_meta` 404s for one build number — `poll_once` skips it, still ingests the others, propagates no error, and a subsequent tick is a no-op (no retry).
> - Full offline suite green (`pytest -m "not live"`, 172 passed); ruff clean.
>
> Closes #20
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)


<a id="pr-24"></a>

### #24 — feat(dashboard): restyle UI with vendored Bootstrap 5

- **State:** Merged
- **Branch:** `claude/jenkins-ut-analyzer-23-68bgr8` → `main`
- **Opened:** 2026-07-03 · **Merged:** 2026-07-03
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/24

> Closes #23
>
> ## What changed
> Replaced the hand-rolled inline `<style>` block with **Bootstrap 5** as the dashboard's CSS framework.
>
> - Vendored `bootstrap.min.css` (5.3.3) into `src/uta/web/static/` — no CDN or runtime network dependency, no npm/build step, works fully offline.
> - Mounted a `StaticFiles` route at `/static` and linked the stylesheet from `base.html`; the header is now a Bootstrap navbar.
> - Re-themed the six page templates: responsive `.table` tables, `.btn` buttons, `.form-control`/`.form-select` inputs, cards. Domain-specific accents (test-status colours, flaky/removed badges, collapsible cards) kept in a small custom style block layered on top; the `card`/`episodes` class names the tests assert on are preserved.
> - Shipped the static assets via `package-data`.
>
> Pure styling — no routes, data, or workflow changes.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 169 passed, 3 skipped; `ruff` clean.
> - [x] `docs-overview-maintainer` considered — not needed: a pure CSS restyle leaves the app's parts, communications, and workflows unchanged.
> - Runtime smoke test: `/static/bootstrap.min.css` serves (200, `text/css`) and all pages render; screenshotted triage/run/test-record pages to confirm navbar, tables, cards, and status colours.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01Ndmk84MYLLkxYRfMXKuEup
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01Ndmk84MYLLkxYRfMXKuEup)_


<a id="pr-26"></a>

### #26 — feat(demo): synthetic dataset + ephemeral demo app + Render hosting

- **State:** Merged
- **Branch:** `claude/jenkins-ut-analyzer-25-d426vf` → `main`
- **Opened:** 2026-07-03 · **Merged:** 2026-07-03
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/26

> Add a fully offline "demo mode" so the app can run with no external systems
> (no Jenkins/Oracle ut_ref/FishEye/Jira/SMTP/LLM/real Postgres) — for integration
> tests and public online hosting.
>
> - src/uta/demo/dataset.py: SyntheticJenkins + SyntheticTrackingFeed generate a
>   deterministic synthetic build history shaped like the real payloads.
> - src/uta/demo/seed.py: drives it through the REAL ingest_build pipeline (+ a few
>   triage actions), so lifecycle/episodes/classification/signatures/flaky are all
>   computed the production way. All data invented — no LIMS/patient/MODDATA/names.
> - src/uta/demo/app.py: ephemeral SQLite store, seeded on startup, wired to the
>   existing FastAPI app (uta.demo.app:app) — the online-hosting entrypoint.
> - cli.py: `uta demo` (serve ephemeral demo) and `uta seed-demo` (seed DATABASE_URL).
> - tests/integration/: end-to-end assertions over the dataset (every triage bucket,
>   all four causes, flaky board, removed/attributed states, run diff, KB recurrence,
>   all routes 200). Runs in the normal offline `pytest -m "not live"` CI suite.
> - render.yaml: free Docker web service running the demo entrypoint, auto-deploying
>   main. Deploys are test-gated by construction (protected main requires CI green).
> - README + docs/OVERVIEW.html: document demo mode and the Render hosting surface.
>
> Closes #25
>
> Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
> Claude-Session: https://claude.ai/code/session_012KsMdVKvum3Mq1gHoif7YP


<a id="pr-27"></a>

### #27 — fix(render): drop redundant sh -c wrapper from dockerCommand

- **State:** Merged
- **Branch:** `claude/jenkins-ut-analyzer-25-d426vf` → `main`
- **Opened:** 2026-07-03 · **Merged:** 2026-07-03
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/27

> Refs #25
>
> ## What changed
> The first Render deploy built fine but exited 127 at start:
>
> ```
> sh: 1: uvicorn uta.demo.app:app --host 0.0.0.0 --port 10000: not found
> ```
>
> Render already runs `dockerCommand` in a shell (so `$PORT` expands). Wrapping it in an extra `sh -c "…"` double-quoted the whole command into a single token, so the container tried to exec a program *literally named* `uvicorn … --port 10000`. Fixed by using the canonical bare form:
>
> ```yaml
> dockerCommand: uvicorn uta.demo.app:app --host 0.0.0.0 --port $PORT
> ```
>
> ## How verified
> - [x] Offline gate unaffected (config-only change; CI runs on this PR)
> - [x] `docs-overview-maintainer` — not applicable (deploy config only, no parts/workflow change)
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_012KsMdVKvum3Mq1gHoif7YP)_


<a id="pr-28"></a>

### #28 — docs: fix retired PROGRESS.md link + note the live demo URL

- **State:** Merged
- **Branch:** `claude/jenkins-ut-analyzer-25-d426vf` → `main`
- **Opened:** 2026-07-03 · **Merged:** 2026-07-03
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/28

> Refs #25
>
> ## What changed
> - **`docs/OVERVIEW.html`** — the footer's "status" source linked the retired `docs/PROGRESS.md`; repoint it at **GitHub Issues** (the actual source of truth per CLAUDE.md).
> - **`CLAUDE.md`** — add a **Live demo** note with the public Render URL (<https://jenkins-ut-analyzer-demo.onrender.com>) and a one-paragraph description of how it runs (ephemeral synthetic in-memory store, no external systems, test-gated auto-deploy on `main`).
>
> ## How verified
> - [x] Docs-only change; CI runs on this PR
> - [x] `docs-overview-maintainer` — n/a (link/text correction + a project-note, no parts/workflow change)
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_012KsMdVKvum3Mq1gHoif7YP)_


<a id="pr-29"></a>

### #29 — feat(dashboard): in-app control panel — runtime tuning + on-demand ingest

- **State:** Merged
- **Branch:** `claude/jenkins-ut-analyzer-16-1wjyz4` → `main`
- **Opened:** 2026-07-04 · **Merged:** 2026-07-04
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/29

> Closes #16
>
> ## What changed
>
> A new `/control` dashboard page (navbar: **Control**) gives the monitor three operational levers without editing env + redeploying:
>
> - **Tune thresholds at runtime.** A whitelist of tunables (`uta/control/tunables.py`) — flaky threshold/window, KB cutoff & top-k, recently-fixed days, UI row cap, expected shards, data-change lookback/tolerance, backfill depth — is overridable from the UI, stored in a new `setting_overrides` table and merged onto the env `Settings` at read time. Overrides apply to dashboard views immediately (each GET route resolves effective settings) and to the poller on its next tick (re-read each tick, no restart); each reverts to its env default. Secrets/URLs are never overridable — a non-whitelisted or out-of-bounds key is rejected.
> - **On-demand ingest / re-analysis.** `POST /control/ingest` runs a build or range in a background thread with back-fill semantics (no email, no LLM), tracked in a new `ingest_jobs` table with live queued → running → done/error status + progress.
> - **Poller health.** Last poll, high-water mark, last-tick count and last error, from a new `poller_heartbeats` singleton the poller stamps each tick.
>
> Supporting: extracted client builders to `uta/clients.py` (CLI, poller and on-demand ingest build identical clients); alembic migration `c3d4e5f6a7b8` for the three operational tables; navbar link + `control.html`.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 200 passed, 3 skipped; ruff clean. 18 new tests (`tests/unit/test_control.py`, `tests/integration/test_control_web.py`) cover coercion/bounds, override CRUD + whitelist enforcement, effective-settings merge, ingest-job success/failure, heartbeat, and the acceptance flow end-to-end (set `ui_row_limit` → run view reflects it; trigger ingest → job reaches `DONE`; panel shows heartbeat + high-water mark).
> - [x] `docs-overview-maintainer` invoked — updated OVERVIEW.html (parts cards, system-map SVG + legend for the new web→Jenkins/Oracle on-demand path, and the ingest-loop section).
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_011pXoPdvHJAvSEvRJza32f4
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_011pXoPdvHJAvSEvRJza32f4)_


<a id="pr-30"></a>

### #30 — Run the devcontainer prompt-free; make development devcontainer-only

- **State:** Merged
- **Branch:** `claude/local-cloud-permissions-jicn4m` → `main`
- **Opened:** 2026-07-04 · **Merged:** 2026-07-04
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/30

> Closes #32
>
> ## What changed
> - **Bake `bypassPermissions` into the devcontainer image** via `/etc/claude-code/managed-settings.json` (`.devcontainer/Dockerfile`). That's the Linux managed-settings path — highest precedence, and not shadowed by the workspace bind mount or the `~/.claude` named volume, so the image copy is authoritative. Container sessions run prompt-free; `rm -rf /`/`~` and the repo `deny` rules still act as circuit-breakers.
> - **Empty `permissions.allow`** in `.claude/settings.json` (redundant under the managed mode); keep the `deny` backstop and the `acceptEdits` default for non-devcontainer contexts.
> - **CLAUDE.md**: replace the "Shell-command hygiene / avoid permission prompts" section with a "Development happens only in the devcontainer" note, and reframe the bare VM host as deployment-only.
>
> ## How verified
> - [ ] Offline gate green (`pytest -m "not live"`) — no Python/test files touched; relying on the required CI `test` check.
> - [x] `docs-overview-maintainer` considered — not needed: dev-environment / permission config only, with no change to the app's parts, integrations, or the ingest→analysis→triage→learning→alert workflows / PLAN §0–§5 outputs.
>
> Follow-up (separate): parallel in-container git worktrees — #31.


<a id="pr-33"></a>

### #33 — docs: retire planning MD files, fold reference into OVERVIEW, drop §N refs

- **State:** Merged
- **Branch:** `claude/section-symbol-references-5uoo97` → `main`
- **Opened:** 2026-07-04 · **Merged:** 2026-07-04
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/33

> The three docs/*.md files (PLAN, IMPLEMENTATION-PLAN, NEXT-PHASE-REQUIREMENTS)
> were the pre-build requirements. The tool is built, so they're retired; their
> durable content — the persisted information model and the load-bearing
> invariants — now lives in a new "Reference" section in docs/OVERVIEW.html, which
> becomes the single authoritative concept/architecture doc. Full history remains
> in git.
>
> Also removes the §N section-shorthand (§0–§5) that referenced those docs from
> everywhere it appeared: two user-visible dashboard labels, ~40 code
> docstrings/comments, tests, config, README, and the OVERVIEW prose/SVG. With the
> defining doc gone the numbering was dangling; each reference is reworded to plain
> descriptive language (e.g. "the §0 triage queue" → "the triage queue").
>
> CLAUDE.md, README.md and the docs-overview-maintainer agent are repointed to
> OVERVIEW.html + GitHub Issues as the sources of truth.
>
> Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
> Claude-Session: https://claude.ai/code/session_01YFdYq1G1v3keBF5R8zRD8F


<a id="pr-39"></a>

### #39 — chore: add VS Code run configs for rebuild/restart and debug

- **State:** Merged
- **Branch:** `chore/38-vscode-run-configs` → `main`
- **Opened:** 2026-07-04 · **Merged:** 2026-07-04
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/39

> Adds `.vscode/` run configs so the app can be rebuilt/restarted and debugged from the IDE.
>
> - **tasks.json** — `Ctrl+Shift+B` runs `docker compose up -d --build web poller` (rebuild + restart); also up/stop/tail-logs and the offline `pytest -m "not live"` gate.
> - **launch.json** — debugpy: uvicorn `--reload` web app, in-memory demo app, and a CLI subcommand.
>
> Docs-only editor tooling; no app code, parts, or workflows changed.
>
> Closes #38
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)


<a id="pr-40"></a>

### #40 — chore(infra): parallel in-container git worktrees for local dev

- **State:** Merged
- **Branch:** `chore/31-parallel-worktrees` → `main`
- **Opened:** 2026-07-04 · **Merged:** 2026-07-04
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/40

> Closes #31.
>
> ## What
>
> Enables multiple Claude Code / dev sessions to run **in parallel** on different branches, using **git worktrees inside the single devcontainer** (not a container per task).
>
> - **`make worktree name=<x>`** ([Makefile](Makefile) → [scripts/worktree.sh](scripts/worktree.sh)) does, in one shot:
>   - `git worktree add .worktrees/<x> -b <x> origin/main`
>   - per-worktree `.venv` + `pip install -e '.[dev]'` (the editable install pins one source path, so worktrees can't share a venv)
>   - writes the worktree's `.env` with `DATABASE_URL` rewritten to a throwaway `uta_<x>` DB
>   - `createdb uta_<x>` + `uta migrate`
> - **`make worktree-rm name=<x>`** — `git worktree remove` + branch delete + `dropdb`.
> - **`make worktree-ls`** — list worktrees.
> - `.worktrees/` added to [.gitignore](.gitignore) (lives in the bind mount → persists on the host, shares the one `.git`; no mount change, no rebuild).
> - [CLAUDE.md](CLAUDE.md) worktree note updated from "deferred" to the chosen in-container model.
>
> ## Two subtleties worth calling out
>
> - **DATABASE_URL override.** The devcontainer exports a container-wide `DATABASE_URL` that outranks the `.env` file in pydantic-settings, so the `.env` rewrite alone wouldn't isolate the DB. The helper also appends `export DATABASE_URL=…` to the worktree venv's `activate`, so `source .venv/bin/activate` points both the interpreter *and* the DB at the worktree.
> - **No `postgresql-client` in the image.** `CREATE`/`DROP DATABASE` go through `psycopg` (already a project dependency) — so `make worktree` works in the running container with no rebuild.
>
> ## Acceptance check (all verified locally)
>
> - `make worktree name=demo` → working worktree in ~15s; `pytest -m "not live"` → **204 passed** on its own venv + `uta_demo` DB.
> - Two worktrees ran the **destructive migration test concurrently** → both green, no interference (per-worktree DBs).
> - `make worktree-rm` cleanly removed worktrees, branches, and DBs.
> - 22 new offline tests ([tests/unit/test_worktree_helper.py](tests/unit/test_worktree_helper.py)) cover the validation boundary + pure helpers, with no git/Postgres side effects.
>
> docs-overview-maintainer reviewed: **no OVERVIEW.html update needed** (local dev tooling only — no change to the app's parts, communications, or workflows).
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)


<a id="pr-41"></a>

### #41 — feat(dashboard): show failure detail per episode, expand current+open

- **State:** Merged
- **Branch:** `feat/36-episode-failure-details` → `main`
- **Opened:** 2026-07-05 · **Merged:** 2026-07-05
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/41

> ## Ticket #36 — add error information of failing tests in failure episodes
>
> Move the per-test error detail out of the single standalone **Latest failure** section and into **each failure episode**, so a test with multiple fail→fix cycles shows the error that characterises each episode.
>
> ### What changed
> - **`src/uta/web/views.py`**
>   - New `_episode_failure_detail(session, ep)`: the latest failing `TestResult` scoped to the episode's **last-failing run** (falling back to its first-failure run), surfacing the same fields the old `latest_failure` did — `track`, `status`, `error_type`, `error_details`, `error_stack_trace`, `file_path`/`line`, and the run link.
>   - `_episode_dict` now carries a `failure` key (None when the episode has no failing result).
>   - Dropped the top-level `latest_failure` key from `test_record(...)`. `_latest_failing_result` is retained — it still feeds the KB `recurrence` block.
> - **`src/uta/web/templates/test_record.html`**
>   - Removed the standalone "Latest failure" `<details>`.
>   - Added a `<details>` "Failure detail" block inside each episode card, rendered only when `ep.failure` is present. It is `open` **only** when `lc and ep.id == lc.current_episode_id and ep.is_open`; collapsed otherwise.
>
> ### Tests
> - `test_dashboard_views.py`: episode carries scoped `failure` fields; `latest_failure` no longer on the record; a multi-episode test asserts each episode shows **its own** error (episode 1 closed / episode 2 current+open).
> - `test_web_dashboard.py`: "Latest failure" section gone, "Failure detail" present, and the current+open episode's block renders with `open`.
> - Offline suite green: `228 passed, 6 deselected`. `ruff check` clean.
>
> ### Note for rebase
> Renders timestamps normally (`{{ ef... }}` block is mostly error text/stack trace — no raw timestamp in the new block, so #35's `ts` filter rebase should be minimal). Will rebase over #35 and #34 before merge.
>
> Closes #36


<a id="pr-42"></a>

### #42 — feat(dashboard): timestamps to seconds precision, wrappable

- **State:** Merged
- **Branch:** `feat/35-timestamp-display` → `main`
- **Opened:** 2026-07-05 · **Merged:** 2026-07-05
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/42

> Timestamps were rendered by stringifying datetime objects directly, producing e.g. `2026-06-29 16:15:46.142000+00:00`. This trims them to seconds precision and ensures they render as ordinary breakable text.
>
> ## Changes
> - **`src/uta/web/app.py`**: new `format_ts` function registered as the `ts` Jinja filter on `_TEMPLATES.env.filters`. Formats a datetime as `%Y-%m-%d %H:%M:%S` (drops microseconds and the `+00:00` tz suffix — the app already normalizes to UTC), returns `—` for `None`, and falls through to `str()` for non-datetime values.
> - Applied `{{ x|ts }}` at every timestamp render site across all views: `triage.html`, `flaky.html`, `run.html`, `test_record.html`, `control.html`. (`kb.html` / `base.html` / `_macros.html` render no timestamps.)
> - Output is plain wrappable text — no `&nbsp;` / `white-space:nowrap` exists anywhere around timestamps, verified by grep.
> - **`tests/unit/test_ts_filter.py`**: covers seconds-precision formatting (aware + naive), `None` fallback, non-datetime pass-through, wrappable-text guarantees, and filter registration.
>
> ## Testing
> - `pytest -m "not live"`: **232 passed, 6 deselected**
> - `ruff check src/uta tests`: clean; `ruff format --check`: clean
>
> Closes #35


<a id="pr-43"></a>

### #43 — feat(flakiness): show true total on flaky leaderboard

- **State:** Merged
- **Branch:** `feat/34-flaky-leaderboard-total` → `main`
- **Opened:** 2026-07-05 · **Merged:** 2026-07-05
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/43

> ## What
> Adds a total count at the top of the flaky leaderboard header.
>
> The total is the **true** number of oscillating/flaky tests in the window,
> computed without the display `limit`, so it stays honest when there are more
> candidates than the 50-row display cap (header notes "(showing top N)" then).
>
> ## How
> - `analyze/flakiness.py`: extracted `leaderboard_candidates()` — the full ranked
>   candidate list with no display limit. `leaderboard()` now just slices it.
> - `web/views.py::flaky_leaderboard()`: single-pass — builds candidates once,
>   returns `rows[:limit]` plus `total = len(candidates)`.
> - `web/templates/flaky.html`: renders the count in the header using the existing
>   `.count`/`.meta` accent classes.
>
> ## Tests
> - `test_flakiness.py`: total from `leaderboard_candidates()` is independent of the
>   `leaderboard()` display limit.
> - `test_web_m4.py`: `flaky_leaderboard()` header total is the true count, not the
>   capped row count.
> - Offline suite green (`pytest -m "not live"`), ruff clean.
>
> Closes #34
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)


<a id="pr-45"></a>

### #45 — docs: note baked bypassPermissions is CLI-only; VS Code extension needs its own toggle

- **State:** Merged
- **Branch:** `docs/44-extension-bypass-note` → `main`
- **Opened:** 2026-07-05 · **Merged:** 2026-07-05
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/45

> Clarifies CLAUDE.md's "Development happens only in the devcontainer" section: the baked `bypassPermissions` in managed-settings makes the **terminal CLI** prompt-free, but the **native VS Code extension** has a separate per-machine gate and won't bypass until you enable "Allow dangerously skip permissions" (VS Code Settings → Extensions → Claude Code) and select the bypass mode. These are per-user VS Code settings the image can't bake.
>
> Closes #44
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)


<a id="pr-47"></a>

### #47 — Add ZEPHYR test case extraction, storage and deep-links (#46)

- **State:** Merged
- **Branch:** `claude/jenkins-ut-analyzer-46-ebxjwh` → `main`
- **Opened:** 2026-07-05 · **Merged:** 2026-07-05
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/47

> Failing tests emit a "ZEPHYR TEST CASE INFO" block naming the ZEPHYR
> (Kanoah) test case(s) that reference the unit test. Parse those ids from
> the stack trace, persist them on the test identity, and surface them as
> clickable deep-links on the per-test record.
>
> - ingest/ut_report.py: extract_zephyr() reads the block scope and returns
>   all LX-T… ids (de-duped, first-seen order) plus the first owner initials;
>   a test may reference more than one case. Wired into both the JUnit and
>   console-log parsers.
> - models/identity.py: new zephyr_test_cases column (comma-separated),
>   resolved at identity level like owner_initials — only refreshed from runs
>   that carry a block, so a later passing run never wipes it. Alembic
>   migration d4e5f6a7b8c9.
> - web: render the ids as links in the test-record header meta line, using a
>   configurable zephyr_test_case_url_prefix (Kanoah test-case URL).
> - docs/OVERVIEW.html: ZEPHYR added as a third read-only deep-link target.
>
> Closes #46
>
> Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
> Claude-Session: https://claude.ai/code/session_01L6QYUAknUBotDQFpsc8h6L


<a id="pr-48"></a>

### #48 — feat(dashboard): add "Job runs" page listing all ingested runs

- **State:** Merged
- **Branch:** `feat/37-job-runs-page` → `main`
- **Opened:** 2026-07-05 · **Merged:** 2026-07-05
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/48

> Closes #37
>
> ## What
> Adds a new **Job runs** dashboard page (`GET /runs`, nav link between Triage and Flaky) listing every ingested run, newest-first. For each run:
>
> - **Run number** → links to the existing run detail (`/runs/<n>`)
> - **State** — Jenkins result rendered as a green/orange/red badge (SUCCESS / UNSTABLE / FAILURE·ABORTED)
> - **Jenkins** link to the build URL
> - **Start** time and **Duration**
> - **Test overview** — passed / failed / skipped and overall total
> - **Regressions** — new failures vs the baseline
> - **Newly fixed** — tests fixed this run that failed in the baseline
>
> At the top, a banner shows the **poller's last tick** and the **projected next tick** (last + poll interval).
>
> ## How
> - `uta.web.views.job_runs` builds the projection from existing `Run` rows, using `compute_diff`/`select_baseline` (the same baseline the run summary uses, so the two pages never disagree) and `read_heartbeat` for the poller banner. Per-run status maps are cached and reused across runs (a run's baseline is usually the run before it), so the page costs roughly one lightweight `(identity_id, status)` scan per run.
> - New `duration` Jinja filter for compact `Hh Mm Ss` rendering.
> - `docs/OVERVIEW.html` updated (via docs-overview-maintainer) to list the new read-side surface.
>
> ## Tests
> - `test_dashboard_views.py`: diff counts, newest-first ordering, totals, poller next-tick, empty store.
> - `test_web.py`: `/runs` route renders and links to run detail.
> - Full offline suite green (`pytest -m "not live"`, 240 passed); ruff clean.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)


<a id="pr-56"></a>

### #56 — Enable TLS verification for the Jenkins client by default

- **State:** Merged
- **Branch:** `claude/issue-54-cpywtg` → `main`
- **Opened:** 2026-07-05 · **Merged:** 2026-07-05
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/56

> Closes #54
>
> ## What changed
> - `HttpJenkinsClient` now defaults `verify=True` instead of the hardcoded `verify=False` that silently disabled TLS certificate verification for all Jenkins traffic.
> - Added typed settings: `jenkins_verify_tls` (bool, default `true`) and `jenkins_ca_bundle` (path to a PEM CA bundle). A new `Settings.jenkins_verify` property resolves the value passed to httpx: the CA bundle path if set, else the bool flag.
> - `build_client` in `src/uta/clients.py` wires `settings.jenkins_verify` into the `HttpJenkinsClient` constructor.
> - Documented both new keys in `.env.example` (`JENKINS_VERIFY_TLS`, `JENKINS_CA_BUNDLE`), noting the CA bundle is the preferred fix over disabling verification.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 248 passed, 3 skipped.
> - [x] `ruff check` clean on the changed files.
> - [x] New unit tests (`tests/unit/test_jenkins_client.py`) assert TLS verification is on by default, can be explicitly disabled, and that `build_client` wires the setting through (including CA bundle precedence over the boolean flag).
> - [x] `docs-overview-maintainer` considered — not invoked; this is a config/security fix with no change to the app's parts, communications, or workflows.
>
> ## Deployment note
> Before rollout, confirm the real Jenkins cert chain is trusted by the deployment host (or set `JENKINS_CA_BUNDLE` to the internal CA's PEM) so the poller doesn't start failing TLS verification on upgrade.
>
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01EL3DXSWTi1b32jS5rLAkNP)_


<a id="pr-57"></a>

### #57 — feat(analysis): populate suggested_contact from change-candidate authors (#49)

- **State:** Merged
- **Branch:** `claude/issue-49-yyfgpi` → `main`
- **Opened:** 2026-07-05 · **Merged:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/57

> classify_episode() now derives the suggested contact at classification
> time: the sole SVN commit author for CODE_CHANGE, the sole V_TRACKING
> USRCODE for DATA_CHANGE. Multiple distinct authors, any candidate with
> unknown authorship, or a non-attributable cause (INFRASTRUCTURE/UNKNOWN)
> leave it None rather than guess — so one-click Confirm never stamps a
> fabricated causing_person.
>
> This makes the already-plumbed surfaces live: the regression email's
> "contact: X", the test-record suggestion, and Confirm stamping the
> contact as causing_person with AI_CONFIRMED provenance.
>
> The demo dataset (single-author candidate builds) now surfaces populated
> examples end-to-end, including a HUMAN_CORRECTED attribution where the
> seeded human answer overrides the AI suggestion; integration tests lock
> both in. OVERVIEW.html documents the derivation rule.
>
> Closes #49
>
> Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
> Claude-Session: https://claude.ai/code/session_01BfZgVGAwrhFaacZSLrMt3G


<a id="pr-58"></a>

### #58 — feat(infra): harden the poller — retries, quarantine, real /health, ops alerts, job recovery

- **State:** Merged
- **Branch:** `claude/issue-51-n8dp9i` → `main`
- **Opened:** 2026-07-05 · **Merged:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/58

> Closes #51
>
> ## What changed
> - **In-tick retries**: transient errors (network faults, HTTP 5xx/429, DB connection blips) retry with exponential backoff (`POLL_RETRY_ATTEMPTS` × `POLL_RETRY_BASE_SECONDS`); deterministic errors (parse failures, 4xx) fail fast.
> - **Build quarantine**: a build that still fails counts one attempt per tick on the new `build_quarantines` table and blocks the tick (preserving lifecycle order); after `QUARANTINE_AFTER_ATTEMPTS` it is quarantined — recorded on the control panel ("Build quarantine" table), ops-alerted by email, and excluded from selection so the high-water mark advances past it. A 404-rotated build quarantines immediately (the explicit form of the old silent skip). A successful on-demand re-ingest clears the record.
> - **Real `/health`**: DB ping + heartbeat freshness. The heartbeat gained `last_success_at` (moved only by error-free ticks) and `stale_alerted_at`; `/health` returns 503 when the DB is unreachable or no successful poll landed within `POLLER_STALE_AFTER_INTERVALS` × `POLL_INTERVAL_SECONDS`. Poller-less deployments (the public demo) report poller `"never"` and stay 200.
> - **Ops alert emails**: new `send_ops_alert` on the existing `EmailSender` seam (`UT Analyzer ops —` subjects) for quarantined/skipped builds and a stale poller — the staleness alert is latched so repeated health probes don't re-mail, and re-arms on recovery.
> - **Orphaned-job recovery**: web startup flips `QUEUED`/`RUNNING` ingest-job rows left by a restart to `ERROR` with an explanatory message.
> - Alembic migration `e5f6a7b8c9d0`; control panel shows "Last successful poll"; demo dataset seeds a quarantined-build example; `docs/OVERVIEW.html` synced (SMTP/postgres/poller/web cards, system map SVG, ingest + alerting workflows).
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 263 passed, including 18 new tests (fake Jenkins/email, injected `sleep`): transient failure retried and succeeding within a tick; persistent failure quarantined with the high-water mark advancing and the alert sent; `/health` 503 on a stale heartbeat and on an unreachable DB; restart leaving no job `RUNNING`. Migration tests additionally verified against a real Postgres 16 (upgrade + clean downgrade).
> - [x] `docs-overview-maintainer` considered (invoked; it updated OVERVIEW.html)
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_0179fuAAptvSGHyUhK5kFE3C
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_0179fuAAptvSGHyUhK5kFE3C)_


<a id="pr-59"></a>

### #59 — perf: add data retention/pruning and fix dashboard scale (#52)

- **State:** Merged
- **Branch:** `claude/issue-52-shqdvi` → `main`
- **Opened:** 2026-07-05 · **Merged:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/59

> Closes #52
>
> ## What changed
> - **Retention** (new `src/uta/retention.py`, run at the end of every poll tick + new `uta prune` CLI): passing/skipped results from runs older than `RESULT_RETENTION_DAYS` (default 90, tunable, 0 disables) are pruned; failing results, runs, episodes, lifecycles, attributions and KB signatures are kept forever. Only unsigned (`signature_id IS NULL`) rows are ever deleted, so KB occurrence counts can't be corrupted. Finished (done/error) ingest jobs older than `INGEST_JOB_RETENTION_DAYS` (default 30, tunable) are pruned too; the heartbeat is a singleton (no history to cap). Both windows form a new "Retention" control-panel tunables group. Accepted degradation: diffs of runs *older than the window* lose their "newly fixed" entries (stored run totals stay exact forever).
> - **Server-side pagination**: `/runs/{build}` results table and the `/runs` list paginate in SQL (`?page=N`, page size = `ui_row_limit`), replacing the all-or-nothing `?expand=results` link — no route loads all results unbounded. Triage buckets keep the expand/cap UX. The demo seeds a `ui_row_limit=20` override so pagination is visible live.
> - **N+1 fixes**: the triage queue is 3 queries total regardless of rows (eager-loaded lifecycle→identity/episode/attribution + batched latest-classification and run-ref lookups); the runs list batches its per-run status-map scans into one grouped query (`identity_status_maps`) and resolves baselines in bulk.
> - Branch updated from `main` (merged in #53 sparklines / #60 run-health timeline; the timeline now spans the rendered page).
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`, 281 passed) — includes new tests proving KB occurrence counts and episode history survive pruning, pruning idempotence, the poll-tick retention pass, pagination (views + HTTP level), and SQLAlchemy statement-counter tests asserting flat query counts on the triage and runs pages
> - [x] `docs-overview-maintainer` considered — invoked; it updated OVERVIEW.html (prune step in the ingest flow + system map, paginated surfaces, new Retention invariant row)
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_018qokTMefaX9tFey7SvhVdY


<a id="pr-60"></a>

### #60 — feat(dashboard): add run-health timeline and per-test flakiness sparklines

- **State:** Merged
- **Branch:** `claude/issue-53-g1czhi` → `main`
- **Opened:** 2026-07-05 · **Merged:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/60

> Closes #53
>
> ## What changed
> Every dashboard surface was point-in-time tables, but the data is trend-rich. Adds a small set of server-rendered inline SVG charts (no JS framework, no CDN — the app stays script-free), driven by data these pages already compute:
>
> - **`/runs`**: a new "Run health" timeline chart above the runs table — two polylines (failed count, regression count) plotted across all ingested runs, oldest to newest.
> - **`/flaky`**: a new "Recent" column with a per-test sparkline — one colored bar per run in the flakiness window, red = failed — so oscillation is visible at a glance instead of just the numeric score.
> - **Per-test record**: the same sparkline added to the "Flakiness & history" card.
>
> Implementation:
> - `src/uta/web/charts.py` (new) — pure geometry builders (`run_health_timeline()`, `sparkline()`) that turn plain row/point data into ready-made SVG coordinates. No HTTP/template concerns, so it's unit-testable standalone; templates just render the numbers.
> - `src/uta/analyze/flakiness.py` — exposes a new `history()` function returning the previously-private per-run pass/fail sequence, windowed identically to the existing flakiness stats (`flaky_window_days`), so a sparkline and its flakiness card never disagree.
> - `src/uta/web/views.py` — wires the above into `job_runs()`, `flaky_leaderboard()`, and `test_record()`.
> - Templates (`runs.html`, `flaky.html`, `test_record.html`, `_macros.html`, `base.html`) render the charts; a shared `sparkline()` Jinja macro is reused across the two per-test surfaces.
> - `docs/OVERVIEW.html` updated (via the `docs-overview-maintainer` agent) to describe the new charts alongside the existing field-level description of these pages.
>
> No new external systems, data model, or ingest/analysis flow changes — this is purely an additional rendering of data already displayed as text/numbers on these three pages. The demo dataset already seeds a 14-run history with a rising failure trend and an oscillating test (`test_pdf_render`), so the live demo exercises both charts without any dataset changes.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"` — 253 passed, plus one pre-existing unrelated failure in `test_worktree_helper.py` caused by this sandbox's system Python lacking `sqlalchemy`, reproduced identically on `main`)
> - [x] `docs-overview-maintainer` considered and invoked — made a small precise edit to `docs/OVERVIEW.html`
> - [x] Manually rendered `/runs`, `/flaky`, and `/tests/{id}` against the demo dataset and confirmed the SVG charts show a real rising failure trend and a clearly oscillating sparkline
>
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_015fNVConhkritNFEtixLNsN)_


<a id="pr-61"></a>

### #61 — fix(ingest): stop defaulting unrecognized unittest outcomes to PASSED

- **State:** Merged
- **Branch:** `claude/issue-56-k8d53f` → `main`
- **Opened:** 2026-07-05 · **Merged:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/61

> An unmatched verbose-line outcome tail in the console-log stage parser
> silently mapped to PASSED, so a nose2/logging format drift would turn
> real failures green. Map it to SKIPPED (the existing neutral "hole"
> status) instead and log a warning with the offending line.
>
> Closes #55


<a id="pr-62"></a>

### #62 — feat(analysis): rank change candidates per failing test and feed details to the LLM prompt (#50)

- **State:** Merged
- **Branch:** `claude/issue-50-lb6ajh` → `main`
- **Opened:** 2026-07-06 · **Merged:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/62

> Closes #50
>
> ## What changed
> - New pure module `uta.analyze.relevance`: scores each run-windowed candidate against one failing test — changed SVN paths vs the test's module/stack-frame paths (module / file-name / package tiers), changed `V_TRACKING` entities/components as whole words vs the error text. Coarse deterministic tiers, no fabricated confidence.
> - **Test record**: candidates render most-relevant-first with the match reason visible (path overlap / entity mention) instead of the flat run-wide chronological list.
> - **`classify_episode()`**: relevance breaks the former "both code and data present → UNKNOWN" tie when exactly one kind matches this test; the tie-break and top matches land in the evidence JSON. Composes with #57's suggested-contact rule (merged from `main`).
> - **`build_prompt()`**: top-ranked candidates' revision/author/message and entity/change-type/author plus match reasons replace the bare integer counts, so hypotheses can name a concrete suspect. Redaction is structural — the ranked data-change dataclass carries only key/author fields; `MODDATA` is never persisted upstream.
> - **Demo dataset**: `test_invoice_rounding` tie-breaks to CODE_CHANGE via path overlap, `test_timezone_convert`'s top candidate is the LORDER data change its error names, `test_pdf_render` keeps the no-match UNKNOWN case — asserted by new integration tests.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 292 passed incl. 15 new relevance tests (path/entity/no-match tiers against golden #1702 fixtures), classify tie-break tests, rewritten prompt tests (authors/paths appear, redaction allowlist), and demo divergence tests; ruff clean
> - [x] `docs-overview-maintainer` considered — it updated OVERVIEW.html's Classification card and per-test-record paragraph
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01R5yvdzBrqwuFetpYwB5vtK
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01R5yvdzBrqwuFetpYwB5vtK)_


<a id="pr-64"></a>

### #64 — feat(dashboard): triage filters/sort, global search, and bulk actions

- **State:** Merged
- **Branch:** `claude/issue-63-ntsjpv` → `main`
- **Opened:** 2026-07-06 · **Merged:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/64

> Closes #63
>
> ## What changed
>
> - **Filter/sort bar on the triage queue** (`GET /`): owner, suite, track, predicted cause, triage status, flaky flag; sort by age (default)/name/owner. All via query params, so it's bookmarkable and survives the acknowledge Post/Redirect/Get round trip (the redirect target is the referer, which already carries the query string).
> - **"Failures only" filter on the run-results table** (`/runs/{build}`): restricts both the results and their count/pagination to non-passing statuses.
> - **Global "jump to test" search**: navbar search box → `GET /search?q=`. A unique match redirects straight to the test record; multiple matches render a short pick-list.
> - **Bulk actions on the triage queue**: row checkboxes + "Acknowledge selected" on the New bucket (`POST /tests/bulk/acknowledge`); row checkboxes + "Apply to selected" (triage status / causing person / reason) on Still-failing (`POST /episodes/bulk/attribute`).
> - **"Acknowledge all with this signature"**: one-click per New-bucket row (`POST /signatures/{id}/acknowledge`). A `FailureSignature` is test-identity + normalized text (so it's never literally shared across tests); the bulk action matches on exception type + message with each test's own stack-frame lines stripped out — the real "one outage broke N tests" grouping key.
> - **Demo dataset**: added a shared-outage pair (`test_email_dispatch` / `test_sms_dispatch`, same error, distinct signature rows) plus a new suite/owner, so the live demo exercises the filter bar and the signature bulk action.
> - `docs/OVERVIEW.html` updated to describe the new triage-queue/run-summary surfaces (no system-map/parts change — this is dashboard read/write surface only).
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`, 351 passed)
> - [x] `ruff check` clean
> - [x] `docs-overview-maintainer` invoked — updated the `web` container description and the triage section
> - [x] Manually exercised filters, bulk-acknowledge, acknowledge-by-signature, search, and the run failures-only toggle against a seeded demo store
>
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01GfJBdJfGqN2rE9R8kgozBX)_


<a id="pr-66"></a>

### #66 — Parallelize Jenkins fetch phase to reduce ingest latency (issue #65)

- **State:** Merged
- **Branch:** `claude/jenkins-ut-analyzer-65-hmkst8` → `main`
- **Opened:** 2026-07-06 · **Merged:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/66

> Closes #65
>
> ## What changed
>
> Refactored the build ingest pipeline to fetch Jenkins endpoints concurrently instead of serially:
>
> - **Base endpoints** (`build_meta`, `wfapi`, `test_report`, `change_sets`) now dispatch to a thread pool and resolve their futures independently, reducing fetch time from ~4× serial latency to ~1× (the slowest endpoint).
> - **Unittest stage logs** (describe/log pairs) also fetch in parallel once `wfapi` resolves and stages are identified, rather than one-by-one.
> - Added `_ConcurrencyTrackingFake` test helper to verify peak concurrency ≥ 2 for both base endpoints and stage logs.
> - Added `_FailingReportFake` to verify that a single endpoint failure still surfaces its original exception type (unwrapped from the thread pool).
> - Verified that parallel fetch produces identical persisted results to serial fetch (no data corruption from concurrency).
>
> The change uses `ThreadPoolExecutor` with a 16-worker cap (comfortably above the ~14 concurrent calls in typical use: 4 base + 5 suites × 2 tracks). The sync `httpx.Client` behind the `JenkinsClient` Protocol/fake seam is thread-safe, so no locking is needed in the client itself.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`)
>   - `test_ingest_fetches_base_endpoints_concurrently`: verifies peak concurrency ≥ 2 for base calls
>   - `test_ingest_fetches_unittest_stages_concurrently`: verifies peak concurrency ≥ 2 for stage logs
>   - `test_ingest_parallel_fetch_matches_serial_output`: verifies identical row counts (22 TestResults, 9 FailureEpisodes, 9 Classifications) as the serial baseline
>   - `test_ingest_propagates_single_endpoint_failure`: verifies exception handling (HTTPStatusError unwrapped)
> - [ ] `docs-overview-maintainer` considered: No change to parts, communications, or workflows — purely an internal optimization of the fetch phase. No update needed.
>
> https://claude.ai/code/session_01MyazEJCKQo5oErG4aXdSwN


<a id="pr-67"></a>

### #67 — Add flag-gated Keycloak OIDC auth (AUTH_ENABLED, off by default)

- **State:** Merged
- **Branch:** `claude/issue-17-spec-rework-z4s2k1` → `main`
- **Opened:** 2026-07-06 · **Merged:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/67

> Phase-2 auth (issue #17): when AUTH_ENABLED=true the app requires a
> Keycloak login (confidential client, auth-code flow + PKCE via Authlib)
> and every write action stamps the verified preferred_username instead of
> the self-declared uta_actor cookie. current_actor stays the single
> identity choke point; routes and the data model are untouched.
>
> - src/uta/web/auth.py: OAuth client, /login + /auth/callback + /logout
>   (RP-initiated, ends the central Keycloak session via id_token_hint),
>   and a fail-closed require-auth middleware (allowlist: /health, the
>   auth endpoints, /static/).
> - identity.py: session principal wins over the Phase-1 cookie fallback.
> - app.py: flag-guarded wiring (SessionMiddleware outermost, 8h max-age,
>   Secure/lax cookie); fails fast if AUTH_ENABLED without SESSION_SECRET.
> - base.html: auth-on header shows the signed-in user + Logout instead of
>   the free-text actor form.
> - Dockerfile / docker-compose: uvicorn --proxy-headers so the OIDC
>   callback URL is built from Traefik's external https address.
> - Offline tests seed a real signed session cookie (itsdangerous, the
>   SessionMiddleware format) instead of faking Authlib; /login and
>   /logout are covered with mocked discovery metadata. A live-marked
>   test asserts the realm's discovery document supports the flow.
>
> With the flag off (default — local dev, demo, CI) the app is
> behaviour-identical to before and needs zero Keycloak access.
>
> Refs #17
>
> Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
> Claude-Session: https://claude.ai/code/session_017SqoriGaBhrqiinCZQUozb


<a id="pr-69"></a>

### #69 — feat(dashboard): add light/dark theme toggle to the navbar

- **State:** Merged
- **Branch:** `claude/theme-selector-button-l5ssts` → `main`
- **Opened:** 2026-07-06 · **Merged:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/69

> Bootstrap 5.3's built-in data-bs-theme dark mode was never wired up.
> Add a navbar toggle button, default to the OS/browser
> prefers-color-scheme on first visit, persist an explicit choice in
> localStorage, and apply it in a blocking <head> script to avoid a
> flash of the wrong theme. Extend the domain-specific CSS overrides
> (status colors, badges, timeline chart, sparklines) with dark-mode
> variants.
>
> Closes #68
>
> Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
> Claude-Session: https://claude.ai/code/session_01EzXAuiqtAoXjSookzzi8cL


<a id="pr-70"></a>

### #70 — Add light/dark theme toggle to the dashboard

- **State:** Merged
- **Branch:** `claude/theme-selector-button-l5ssts` → `main`
- **Opened:** 2026-07-06 · **Merged:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/70

> Closes #68
>
> ## What changed
> - Added a light/dark theme toggle button to the navbar (`base.html`), defaulting to the visitor's
>   OS/browser `prefers-color-scheme` on first visit and persisting an explicit choice in
>   `localStorage`. Applied via `data-bs-theme` in a blocking `<head>` script to avoid a flash of the
>   wrong theme.
> - Fixed a follow-up contrast bug: every card/table across the dashboard hardcoded Bootstrap's
>   `bg-white`/`bg-light`/`table-light` utility classes, which are fixed colours rather than theme
>   variables, so the toggle only ever flipped the navbar/body and left every card/table pinned
>   white with low-contrast text. Removed those hardcoded classes from all 9 templates and replaced
>   them with a small surface-token layer in `base.html` (`--bs-body-bg` / `--uta-surface`) feeding
>   Bootstrap's own `--bs-card-bg`/`--bs-table-bg`, with dark values (`#121212` body / `#1e1e1e`
>   surface) drawn from Material's dark theme rather than Bootstrap's stock dark grey. Table headers
>   and the stack-trace `<pre>` block pick up Bootstrap's own `--bs-tertiary-bg` for a subtle
>   elevation tint in both themes.
> - Re-checked contrast on the existing dark-mode status/badge colours against the new, genuinely
>   dark surfaces (all pairs ≥ 5:1).
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`, 369 passed) and `ruff check` clean.
> - [x] Verified visually with Playwright screenshots in both color schemes across triage, runs, run
>       detail, flaky, KB, control, and test record — no more grey-on-white, every surface actually
>       darkens.
> - [x] `docs-overview-maintainer` considered — this is a pure client-side presentation change (no
>       new/removed integration, container, workflow, or output), so no update to `OVERVIEW.html` is
>       needed.
>
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01EzXAuiqtAoXjSookzzi8cL)_


<a id="pr-71"></a>

### #71 — docs: add Configuration chapter to OVERVIEW.html

- **State:** Merged
- **Branch:** `claude/app-config-docs-b5aug6` → `main`
- **Opened:** 2026-07-06 · **Merged:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/71

> Group every env var from .env.example/config.py by topic (Jenkins,
> Oracle ut_ref, PostgreSQL, email, auth/Keycloak, app tuning, deep
> links, LLM, ingest windows, poller resilience), marking which are
> control-panel runtime-tunable vs secret-only.


<a id="pr-74"></a>

### #74 — feat(analysis): close the learning loop — AI-accuracy metric, score-aware tie-break, classification confidence

- **State:** Merged
- **Branch:** `claude/issue-73-93s75p` → `main`
- **Opened:** 2026-07-07 · **Merged:** 2026-07-07
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/74

> Implements issue #73 (Refs #73):
>
> - Classifier tie-break is now score-magnitude-aware: when both candidate
>   kinds are present, the top code candidate's relevance score is compared
>   against the top data candidate's with a one-tier margin
>   (TIE_BREAK_MARGIN), so a tier-3 module code match beats a tier-2
>   component data mention instead of collapsing to UNKNOWN.
> - Classification.confidence is populated by a documented deterministic
>   formula: flat 0.9 for INFRASTRUCTURE, flat 0.2 for UNKNOWN, and
>   0.5 + 0.4·(relevance-score gap) + 0.1·(KB provenance weight of the
>   failure's signature) for CODE/DATA — validated human knowledge about
>   the exact failure raises confidence. Inputs are recorded in the
>   evidence JSON; the test record shows a confidence badge.
> - New AI-suggestion accuracy metric (uta.control.ai_accuracy) counts
>   confirmed (AI_CONFIRMED) vs corrected (HUMAN_CORRECTED) triage verdicts
>   per conclusion field, all-time and over a 30-day window, and surfaces
>   the precision table on /control — original_ai_cause/original_ai_reason
>   are finally consumed.
> - Demo dataset seeds test_discount_tiers (a resolved score-magnitude
>   tie-break with a visible confidence) and Confirms its suggestion, so
>   the live demo shows one confirmed and one corrected cause verdict.
> - Offline tests cover the tie-break in both directions, the confidence
>   formula (single-candidate, close-tie, KB-boosted) and the accuracy
>   metric; OVERVIEW.html synced.
>
> Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
> Claude-Session: https://claude.ai/code/session_018LbDZs2hkSrA6K98BCmb5r


<a id="pr-90"></a>

### #90 — fix(poller): drop next_run_time=None so the interval job actually fires

- **State:** Merged
- **Branch:** `fix/80-poller-scheduler-paused` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/90

> Closes #80
>
> ## What changed
> `run_scheduler` passed `next_run_time=None` to `add_job`, which in APScheduler 3.x adds the interval job **paused** — the poller ran its one manual startup tick and then never polled again. Dropped the argument (the interval trigger already first-fires at now+interval) and split scheduler construction into `build_scheduler()` so a unit test can assert the registered job is not paused without calling the forever-blocking `start()`.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — new regression test asserts the job would actually fire
> - [x] `docs-overview-maintainer` considered — pure bug fix, no change to parts/communications/workflows
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R)_


<a id="pr-91"></a>

### #91 — fix(ingest): send the regression alert after the ingest transaction commits

- **State:** Merged
- **Branch:** `fix/81-email-outside-ingest-txn` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/91

> Closes #81
>
> ## What changed
> The regression alert (a live SMTP send) ran inside the ingest transaction: an SMTP outage rolled back the whole ingest and eventually quarantined a healthy build, and a post-send commit failure re-sent the identical alert on retry. The alert is now two-phased around the commit — `build_regression_report` composes the message inside the transaction, the new `send_alert` delivers it only after the commit succeeded and swallows/logs send failures (same best-effort discipline as the LLM providers). At-most-once per run: a commit failure raises before anything is sent; the poller never re-ingests below its high-water mark; re-ingest paths pass no sender.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — new tests: a raising sender no longer prevents run persist; a post-send-commit-failure retry does not double-send
> - [x] `docs-overview-maintainer` considered — alert flow ordering is an internal fix; depicted parts/workflows unchanged
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R)_


<a id="pr-92"></a>

### #92 — fix(analysis): never drive the lifecycle from a historical re-ingest

- **State:** Merged
- **Branch:** `fix/82-lifecycle-out-of-order-reingest` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/92

> Closes #82
>
> ## What changed
> Re-ingesting a historical build (the documented quarantine-recovery path) replayed its old diff into the *current* lifecycle — phantom reopened episodes that never close, live episodes closed "in the past", acknowledgements cleared. The pipeline now checks `has_newer_complete_run` before the analysis pass: a historical re-ingest still persists the run, its results, and KB signatures, but skips `apply_run` and the dependent classify/hypothesize/notify steps (logged, display baseline still stamped). Strictly-greater comparison keeps re-ingest of the newest build on the normal idempotent path.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — new end-to-end test scripts the quarantine-recovery scenario: lifecycle/episodes/acks untouched by the historical re-ingest, newest-build re-ingest stays idempotent
> - [x] `docs-overview-maintainer` considered — ingest→analysis flow unchanged in shape; guard is internal
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R)_


<a id="pr-93"></a>

### #93 — fix(ingest): require every UT shard to finish before marking a run complete

- **State:** Merged
- **Branch:** `fix/83-shard-status-completeness` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/93

> Closes #83
>
> ## What changed
> `RunTiming.is_complete` only counted shards and ignored the parsed stage status, so a build aborted mid-UT-stage was persisted `complete=True` and became the next run's baseline — inventing phantom mass transitions. Completeness now also requires every UT shard's status to be in the `FINISHED_STAGE_STATUSES` allow-list (SUCCESS / UNSTABLE / FAILED — test outcomes, not truncation); ABORTED / IN_PROGRESS / PAUSED / NOT_EXECUTED and any unknown status fail safe to incomplete.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — new wfapi + pipeline tests: ABORTED shard ⇒ incomplete and never a baseline; SUCCESS/UNSTABLE/FAILED stay complete
> - [x] `docs-overview-maintainer` considered — pure correctness fix, depicted flows unchanged
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R)_


<a id="pr-94"></a>

### #94 — fix(dashboard): match the triage track filter against every failing track

- **State:** Merged
- **Branch:** `fix/84-triage-track-filter` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/94

> Closes #84
>
> ## What changed
> Triage rows collapsed the per-(identity, run) failing rows into a single track (last write wins), so a test failing in **both** tracks vanished from the queue under `?track=permanent`. Rows now carry `tracks` (every failing track), the filter matches when any of them equals it, and the queue renders one badge per failing track. Demo dataset gains a track-divergent example (a py39-only `X | Y` TypeError) so both the plural and singular forms are visible in the live demo.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — new tests: a both-tracks failure appears under both track filters and lists both tracks
> - [x] `docs-overview-maintainer` considered — dashboard row detail only; parts/communications/workflows unchanged
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R)_


<a id="pr-95"></a>

### #95 — fix(ingest): let a FAIL/ERROR block override a garbled status-line outcome

- **State:** Merged
- **Branch:** `fix/85-unittest-log-fail-block` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/95

> Closes #85
>
> ## What changed
> A test printing to stdout garbles its verbose status line; the parser mapped the unrecognized tail to SKIPPED and discarded the test's parsed FAIL/ERROR traceback block — persisting a real failure as a skip (no episode, no alert). A parsed traceback block is now authoritative: it overrides the status-line outcome and surfaces the failure with its details/traceback. Also, the unrecognized-tail warning no longer logs the raw console line (which in these legacy LIMS suites may carry patient data) — it logs the test identity and tail length only.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — new tests: garbled line + FAIL/ERROR block ⇒ FAILED with block details; no-block behavior unchanged; warning content sanitized
> - [x] `docs-overview-maintainer` considered — parser fix, depicted flows unchanged
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R)_


<a id="pr-96"></a>

### #96 — fix(analysis): anchor INFRA regex tokens so substring hits can't fake an infra fault

- **State:** Merged
- **Branch:** `fix/86-infra-regex-word-boundaries` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/96

> Closes #86
>
> ## What changed
> `_INFRA_RE`'s unanchored `o(?:racle)?error` matched the substring "oerror" inside `IOError`/`ProtoError`, and `socket\.` matched inside `websocket.exceptions.*` — plain code bugs got typed INFRA and force-classified as INFRASTRUCTURE at 0.9 confidence, suppressing real SVN-commit evidence. Every INFRA token is now anchored (`\boracleerror\b`, `\boracledb\.`, `\boperationalerror\b`, `\bora-\d{4,5}\b`, boundary-anchored 502/503/504, `(?<[\w.])socket\.`); the generic TIMEOUT/ASSERTION patterns stay unanchored on purpose (their substring hits are still timeouts/assertions).
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — regression tests in both directions (IOError/ProtoError/websocket no longer INFRA; OracleError/oracledb.*/ORA-/TNS:/socket.timeout still INFRA)
> - [x] `docs-overview-maintainer` considered — heuristic tightening only
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R)_


<a id="pr-97"></a>

### #97 — fix(ingest): make ut_ref CREDATIM window bounds and row conversion DST-fold-safe

- **State:** Merged
- **Branch:** `fix/87-oracle-dst-fold` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/97

> Closes #87
>
> ## What changed
> On the fall-back night the naive CREDATIM mapping is non-monotonic, so the `BETWEEN` window silently excluded changes that happened inside the window, and `from_ut_ref_local` relied on the implicit `fold=0`. New fold-safe helpers `to_ut_ref_local_window_start/_window_end` widen only across the repeated hour (over-inclusion is safe — the tolerance/lookback already widens the window); `OracleTrackingFeed`, the offline fake, and the demo feed all use the pair. `from_ut_ref_local` now pins `fold=0` explicitly and documents deterministic readings for ambiguous and nonexistent (spring-forward) times.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — tests pin the real 2025-10-26 transition (the 45-min-before-window-end change is kept), ambiguous/nonexistent readings, and byte-identical behavior on ordinary days
> - [x] `docs-overview-maintainer` considered — conversion internals only; the depicted Oracle feed is unchanged
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R)_


<a id="pr-98"></a>

### #98 — fix(dashboard): reject cross-site unsafe-method requests app-wide (CSRF)

- **State:** Merged
- **Branch:** `fix/88-csrf-protection` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/98

> Closes #88
>
> ## What changed
> No state-changing POST had CSRF protection, and the default auth-off deployment had no session check either — a cross-site form could land control-panel and triage mutations from any intranet browser. New `uta.web.csrf` middleware (installed unconditionally) rejects unsafe-method requests with 403 when browser fetch metadata says cross-site: `Sec-Fetch-Site` outside {same-origin, none}, else a mismatching `Origin` host:port. Header-less clients (curl, scripts, TestClient) pass — CSRF is a browser attack and every current engine sends the evidence. No token plumbing; identical auth-off/auth-on behavior; OIDC flow untouched (all GETs).
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — new tests: cross-site `Sec-Fetch-Site`/mismatched `Origin` ⇒ 403 on control + triage endpoints; same-origin/matching/header-less pass; GETs unaffected; existing tests unchanged
> - [x] `docs-overview-maintainer` considered — request-guard only; parts/workflows unchanged
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R)_


<a id="pr-99"></a>

### #99 — fix(demo): lock down control-panel mutations in the public demo (403)

- **State:** Merged
- **Branch:** `fix/89-demo-control-lockdown` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/99

> Closes #89
>
> ## What changed
> The public Render demo mounted the full real app: anyone could persist setting overrides into the shared demo store, and POST `/control/ingest` would build a real `HttpJenkinsClient` and fire outbound HTTPS at the config-default internal Jenkins hostname from a public host. `create_app` gains a `demo_mode` flag (default off — real app unchanged) that `uta.demo.app` enables: the three mutating control routes return 403 with a friendly note before any store write, job row, thread, or Jenkins client exists. GET `/control` still renders every seeded panel, with a read-only notice and disabled buttons so the lockdown is honest in the UI; triage actions stay live (part of the demo story, store is ephemeral).
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — new tests: demo app 403s all three mutations with no Jenkins client constructed, `/control` still renders; real app behavior unchanged
> - [x] `docs-overview-maintainer` considered — OVERVIEW.html's Public-demo card updated in this PR (read-only control panel)
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R)_


<a id="pr-100"></a>

### #100 — feat(dashboard): flash feedback for every mutating action

- **State:** Merged
- **Branch:** `feat/75-flash-feedback` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/100

> Closes #75
>
> ## What changed
> - New `src/uta/web/flash.py`: one-shot flash messages (success/error) carried across the POST→303 redirect via a short-lived cookie, cleared on render — a reload does not re-show the banner.
> - `base.html` renders the flash as a dismissible Bootstrap alert at the top of `<main>` on every page.
> - Every mutating action in `app.py` now reports what it did with count-bearing messages (acknowledge, bulk acknowledge, ack-by-signature, episode attribute/confirm, bulk attribute, identity set, control-panel setting save/revert and ingest submission).
> - The `/control` `?error=` mechanism is migrated onto the same flash pattern (error variant), so there is one feedback path.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — new `tests/unit/test_web_flash.py` covers the flash round-trip (POST → redirect → banner rendered once, gone on second GET) for the action endpoints; `ruff check` clean. (The one pre-existing `test_worktree_helper` failure in this container is environmental — system `python3` lacks sqlalchemy — and unrelated.)
> - [x] `docs-overview-maintainer` considered — dashboard feedback polish; no change to the app's parts, communications, or workflows.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01Jc1hwW7GHBB5puSD8WRd7N
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01Jc1hwW7GHBB5puSD8WRd7N)_


<a id="pr-101"></a>

### #101 — feat(dashboard): bulk-selection ergonomics on the triage queue

- **State:** Merged
- **Branch:** `feat/76-bulk-selection` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/101

> Closes #76
>
> ## What changed
> - New `src/uta/web/static/bulk-select.js` (vanilla JS, no CDN): a generic, data-attribute-driven bulk-selection helper shared by both triage bulk forms.
> - `triage.html`: select-all checkbox in the header of the "New failing" and "Still failing" tables (with indeterminate state on partial selection), live selected-count on the "Acknowledge selected (n)" / "Apply to selected (n)" buttons, and the bulk buttons disabled while nothing is selected.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — new tests in `tests/unit/test_web_dashboard.py` assert the rendered contract (select-all present in both tables, data-attribute hooks wired, bulk buttons initially disabled); `ruff check` clean. (The one pre-existing `test_worktree_helper` failure in this container is environmental and unrelated.)
> - [x] `docs-overview-maintainer` considered — triage-queue ergonomics only; no change to the app's parts, communications, or workflows.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01Jc1hwW7GHBB5puSD8WRd7N
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01Jc1hwW7GHBB5puSD8WRd7N)_


<a id="pr-102"></a>

### #102 — feat(dashboard): instant, self-describing triage filters

- **State:** Merged
- **Branch:** `feat/77-instant-filters` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/102

> Closes #77
>
> ## What changed
> - Triage filter selects and the flaky checkbox auto-submit on change (tiny inline JS); text inputs keep Enter/Apply behaviour.
> - Active filters render as removable chips above the tables — each chip's ✕ re-requests the page with just that filter removed (links built server-side in `views.py`).
> - The Test and Owner column headers are now click-to-sort links with a visible marker on the active sort; the `?sort=` URL scheme is unchanged and shareable.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — new tests in `tests/unit/test_dashboard_views.py` and `tests/unit/test_web_dashboard.py` cover chip rendering/removal links and sort-link generation; `ruff check` clean. (The one pre-existing `test_worktree_helper` failure in this container is environmental and unrelated.)
> - [x] `docs-overview-maintainer` considered — filter UX polish; no change to the app's parts, communications, or workflows.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01Jc1hwW7GHBB5puSD8WRd7N
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01Jc1hwW7GHBB5puSD8WRd7N)_


<a id="pr-103"></a>

### #103 — feat(dashboard): auto-refresh ingest jobs via vendored HTMX polling

- **State:** Merged
- **Branch:** `feat/78-htmx-job-polling` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/103

> Closes #78
>
> ## What changed
> - Vendored `htmx.min.js` under `src/uta/web/static/` (no CDN at runtime), loaded from `base.html` so other pages can adopt it later.
> - Extracted the ingest-jobs table into a `_control_jobs.html` partial served by a new `GET /control/jobs` fragment endpoint.
> - The jobs container polls that endpoint every 3s via `hx-get` while any job is QUEUED/RUNNING; the trigger attribute is only rendered when active jobs exist, so the final swapped-in fragment naturally stops the polling loop.
> - RUNNING jobs show a Bootstrap progress bar from the existing `builds_done / builds_total`; the "Reload to refresh job status" hint is gone.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — new tests in `tests/integration/test_control_web.py` cover the fragment endpoint and the poll-stop condition (trigger present with active jobs, absent when all terminal); `ruff check` clean. (The one pre-existing `test_worktree_helper` failure in this container is environmental and unrelated.)
> - [x] `docs-overview-maintainer` considered — in-app refresh mechanics only; no new external system, no change to parts/communications/workflows.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01Jc1hwW7GHBB5puSD8WRd7N
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01Jc1hwW7GHBB5puSD8WRd7N)_


<a id="pr-104"></a>

### #104 — feat(dashboard): active nav state, triage-count badge, relative timestamps

- **State:** Merged
- **Branch:** `feat/79-orientation-polish` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/104

> Closes #79
>
> ## What changed
> - Active nav state: the current section gets Bootstrap's `active` class + `aria-current` on every page (derived centrally in the template context).
> - Triage-count badge: a small red badge on the "Triage" nav link shows the live count of unacknowledged new failing tests from every page (hidden at zero), computed by a single cheap count query shared via the base-template context.
> - Relative timestamps: new `|reltime` Jinja filter renders "2 days ago"-style times with the absolute timestamp in a `title` tooltip (server-side, no JS), applied to the triage queue and test-record lifecycle/episode times; tabular run listings stay absolute.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — new `tests/unit/test_reltime_filter.py` (boundary cases: minutes/hours/days/None) and nav/badge assertions in `tests/unit/test_web_dashboard.py`; `ruff check` clean. (The one pre-existing `test_worktree_helper` failure in this container is environmental and unrelated.)
> - [x] `docs-overview-maintainer` considered — navigation/presentation polish; no change to the app's parts, communications, or workflows.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01Jc1hwW7GHBB5puSD8WRd7N
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01Jc1hwW7GHBB5puSD8WRd7N)_


<a id="pr-105"></a>

### #105 — docs: sync OVERVIEW.html with the review-fix batch

- **State:** Merged
- **Branch:** `docs/overview-sync-review-fixes` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/105

> Refs #82, #83, #88
>
> ## What changed
> Post-merge `docs-overview-maintainer` pass over the ten review fixes: OVERVIEW.html now reflects the shard-status completeness rule (an ABORTED shard keeps a run incomplete, #83), the historical re-ingest analysis skip (#82), and the app-wide CSRF guard on the web container (#88). The maintainer judged the other seven fixes immaterial to the depicted parts/communications/workflows (the #89 demo card was already updated in its own PR).
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — docs-only change
> - [x] `docs-overview-maintainer` considered — this PR *is* its output
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01NFMdopwPTpLcuAFpNedb4R)_


<a id="pr-107"></a>

### #107 — feat(dashboard): signature-level bulk attribution

- **State:** Merged
- **Branch:** `claude/app-value-proposals-kvr42p` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/107

> Closes #106
>
> ## What
>
> When a shared outage breaks many tests with the same failure signature, one root-cause conclusion can now be applied to all of them in one submit — mirroring the existing signature-wide acknowledge.
>
> - New `POST /signatures/{signature_id}/attribute`: applies causing person / reason / Jira ticket / triage status to **all open episodes whose current failure shares the signature** (same error-key matching as signature-acknowledge, whose episode-finding logic is now factored into a shared `open_episodes_for_signature`).
> - Per-episode provenance follows the single-episode flow: `HUMAN_CORRECTED` where an AI suggestion existed (originals retained), `HUMAN_ENTERED` otherwise — the AI-accuracy metric and KB provenance weighting stay correct. Conclusions attach to each episode's signature as before.
> - UI: the test record's attribution form gains an "Apply to all N affected tests with this signature" submit (plain-HTML `formaction`, rendered only when the signature affects more than one open failing test). PRG + count-bearing flash, CSRF middleware covers the new route.
> - Deliberate deviation: an **empty Jira field leaves existing tickets untouched** in the signature-wide action (the single-episode form clears on empty), so a shared-outage submit can't mass-clear unrelated tickets. Documented and test-covered.
> - Demo: the seeded shared-outage pair (`test_email_dispatch` / `test_sms_dispatch`) stays untriaged so the control renders and is exercisable on the live demo.
> - `docs/OVERVIEW.html` synced (Human-triage section) via the docs-overview-maintainer agent.
>
> ## Tests
>
> New coverage in `test_dashboard_views.py`, `test_web_dashboard.py`, `test_web_flash.py`, `test_csrf.py`, and the demo integration suite (signature-wide apply, non-sharing episode untouched, mixed provenance, empty-Jira no-op, unknown-signature error flash, render-only-when-shared, PRG + CSRF). Offline gate green locally: ruff clean, `pytest -m "not live"` — 509 passed, 3 skipped.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01WcvRpKWLVPzTMb2GnS1ALo
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01WcvRpKWLVPzTMb2GnS1ALo)_


<a id="pr-109"></a>

### #109 — feat(analysis): close the learning loop — AI accuracy, score-aware tie-break, confidence

- **State:** Closed
- **Branch:** `claude/issue-73-93s75p` → `main`
- **Opened:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/109

> Closes #73
>
> ## What changed
>
> - **Score-magnitude tie-break** in `analyze/classify.py`: with both candidate kinds present, the top code candidate's relevance score is compared against the top data candidate's with a one-tier margin (`TIE_BREAK_MARGIN = 1.0`) — a tier-3 module code match now beats a tier-2 component data mention instead of collapsing to UNKNOWN; equal-tier ties still stay UNKNOWN.
> - **`Classification.confidence` populated** by a documented deterministic formula: flat 0.9 for INFRASTRUCTURE, flat 0.2 for UNKNOWN, and `0.5 + 0.4·gap + 0.1·kb` for CODE/DATA (`gap` = winner-vs-loser relevance-score lead normalized by the top tier; `kb` = strongest KB provenance weight attached to the failure's signature, via a new `strongest_provenance_weight` in `kb/retrieval.py`). Inputs recorded in the evidence JSON; the test record shows a confidence badge next to the predicted cause.
> - **AI-suggestion accuracy metric** (`control/ai_accuracy.py`): confirmed (`AI_CONFIRMED`) vs corrected (`HUMAN_CORRECTED`) verdicts per conclusion field, all-time and last-30-days, with precision — surfaced as a new panel on `/control`. `original_ai_cause`/`original_ai_reason` are finally consumed.
> - **Demo** seeds `test_discount_tiers` (a resolved tier-3-vs-tier-2 tie-break with a visible 0.63 confidence) and Confirms its suggestion, so the live demo shows the resolved tie-break, the confidence badge, and an accuracy panel with 1 confirmed / 1 corrected cause verdict.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"` — 382 passed; new unit tests cover the tie-break in both directions, the three confidence acceptance cases, and the accuracy metric; demo integration tests assert the seeded examples)
> - [x] `docs-overview-maintainer` considered (invoked — it updated OVERVIEW.html's classification card, learning-loop section, `/control` surface and information-model reference)
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_018LbDZs2hkSrA6K98BCmb5r
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_018LbDZs2hkSrA6K98BCmb5r)_


<a id="pr-110"></a>

### #110 — feat(email): dashboard deep links in alert emails

- **State:** Merged
- **Branch:** `claude/app-value-proposals-kvr42p` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/110

> Closes #108
>
> ## What
>
> Alert emails now deep-link into the dashboard, so recipients land on the exact test record instead of searching by hand.
>
> - New env-only setting **`APP_BASE_URL`** (default empty; documented in `.env.example`, README, and OVERVIEW). Deliberately not a control-panel tunable — URLs are env-only there, matching Jenkins/Jira/FishEye.
> - **Regression email**: each new-failing test line gains an absolute link to its `/tests/{identity_id}` record (indented continuation line, keeps the plain-text format readable), plus a `Dashboard:` link to `/runs/{build}` next to the existing Jenkins URL. The **recovery notice** links the run too.
> - **Unset base URL (the default) keeps email bodies byte-identical to before** — no empty labels, no relative links. Trailing-slash joining is handled.
> - Wired through the live path only: `poll_tick` passes `cfg.app_base_url` into `ingest_build` → `build_regression_report`; backfill/bootstrap/on-demand ingest remain email-free as before.
> - Ops alerts (quarantine/skip/stale-poller) intentionally left link-free: those builds persist no `Run` row, so a `/runs/{build}` link would 404.
>
> ## Tests
>
> 4 new offline tests in `tests/unit/test_email.py`: links present when the base URL is set, absent when unset, clean joining with a trailing slash, and the recovery-notice run link. Offline gate green locally: ruff clean, `pytest -m "not live"` — 513 passed, 3 skipped.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01WcvRpKWLVPzTMb2GnS1ALo
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01WcvRpKWLVPzTMb2GnS1ALo)_


<a id="pr-111"></a>

### #111 — feat(dashboard): show last ingested run on Triage screen

- **State:** Merged
- **Branch:** `feat/72-last-ingested-run-triage` → `main`
- **Opened:** 2026-07-08 · **Merged:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/111

> Adds a small info line to the Triage header showing the most-recently ingested run: its build number (linked to `/runs/<build>`) and start time. Degrades to "none yet" on an empty store.
>
> - New `views.latest_run()` helper mirrors `job_runs`' newest-first ordering (`started_at desc, id desc`) so the Triage header and the Runs list always agree on which build is latest.
> - Wired into the `GET /` triage route and rendered in `triage.html` with the existing `|ts` filter.
> - Unit tests cover the populated and empty-store cases.
>
> The live demo already ingests runs through the real pipeline, so this element is exercised automatically — no dataset change needed.
>
> Closes #72
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)


<a id="pr-113"></a>

### #113 — docs: auth/Keycloak config guide + broaden docs-overview-maintainer to own config docs

- **State:** Merged
- **Branch:** `docs/112-auth-config-guide` → `main`
- **Opened:** 2026-07-09 · **Merged:** 2026-07-09
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/113

> Closes #112 (both aspects).
>
> ## Aspect 1 — Auth/Keycloak config guide (README)
> Adds an **"Auth / Keycloak OIDC (optional)"** subsection to the README Configuration section:
> - the env-var table that was missing (auth was the *only* subsystem without one): `AUTH_ENABLED`, `OIDC_SERVER_METADATA_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_POST_LOGOUT_REDIRECT`, `SESSION_SECRET`;
> - an ordered **per-environment activation checklist** (provision confidential client → register `/auth/callback` + post-logout URIs → generate `SESSION_SECRET` → set vars → flip `AUTH_ENABLED=true`, `--proxy-headers` behind a proxy);
> - the fail-closed middleware + public-allowlist note.
>
> ## Aspect 2 — a guardrail so config docs can't drift again (lighter convention)
> Rather than a second agent, **broadens the existing [`docs-overview-maintainer`](.claude/agents/docs-overview-maintainer.md)** to own three hand-maintained surfaces: OVERVIEW.html, the **README Configuration tables**, and **`.env.example`**. Its "material" criteria and the [CLAUDE.md](CLAUDE.md) invocation mandate now cover a **settings-surface change** — a `config.py` field / `.env.example` key added, removed, renamed, re-gated, or with a changed default/effect. This is exactly the guardrail whose absence let the auth table drift out of the README.
>
> ## Why
> The README config reference silently implied auth didn't exist, no ordered "turn Keycloak on" runbook existed, and nothing prompted a config-doc sync check after settings changes.
>
> ## Test
> Docs/agent-definition/CLAUDE.md only — no application code touched; offline gate unaffected.
>
> Closes #112
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)


<a id="pr-128"></a>

### #128 — fix(ingest): unfinished unittest console-log stage marks run incomplete

- **State:** Merged
- **Branch:** `fix/115-log-stage-completeness` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/128

> Closes #115
>
> ## What changed
> - `run.complete` now also requires every **selected** unittest console-log stage (matched by `find_unittest_stages` against the suite allowlist) to have a status in `FINISHED_STAGE_STATUSES` — mirroring the devUTs shard guard from #83. Previously `LogStage.status` was captured but never read, so an ABORTED/NOT_EXECUTED stage's truncated log parsed to a partial case list on a run still marked complete (phantom REMOVED transitions, poisoned baseline, spurious regression alert on the next healthy run).
> - A suite stage **absent** from the wfapi payload does not affect completeness (job configuration varies over history), and the truncated stage's results are still fetched/persisted — analysis/baseline/alerting stay gated on `run.complete`, exactly as for incomplete devUTs runs.
> - Tests (`tests/unit/test_pipeline.py`): ABORTED and NOT_EXECUTED selected stage with both devUTs shards SUCCESS ⇒ incomplete (results persisted, no episodes, never a baseline); all selected stages finished (incl. the fixture's UNSTABLE py39 stage) ⇒ complete; absent stage ⇒ complete; unfinished stage with log ingestion off ⇒ complete.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 519 passed, 3 skipped; `ruff check .` clean
> - [x] `docs-overview-maintainer` considered (invoke it if the app's parts / communications / workflows changed) — pure bug fix — no parts/communications/workflow change
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq)_


<a id="pr-129"></a>

### #129 — fix(email): send recovery notice only on the red-to-green transition

- **State:** Merged
- **Branch:** `fix/118-recovery-notice-transition` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/129

> Closes #118
>
> ## What changed
> The "UT back to green" gate in `build_regression_report` fired on **every** green run — it never checked that anything transitioned, so with `EMAIL_RECOVERY_NOTICE=true` a healthy suite got a nightly "back to green … Newly fixed this run: 0" email. The gate now also requires an actual red→green transition: the baseline had ≥1 failing test that this run resolved — fixed (`diff.newly_fixed`) **or** absent this run (`diff.removed`; a deleted failing test still turns the suite green — the choice is documented in the docstring). Already-green baselines and all-green first runs (no baseline) send nothing. New unit tests cover the already-green, first-ever-green, and removed-failure cases; the existing transition test is unchanged.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"` — 518 passed, 3 skipped; `ruff check .` clean)
> - [x] `docs-overview-maintainer` considered (pure bug fix — no parts/communications/workflow change)
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq)_


<a id="pr-130"></a>

### #130 — fix(analysis): close open episode when a REMOVED test reappears passing

- **State:** Merged
- **Branch:** `fix/117-removed-reappear` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/130

> Closes #117
>
> ## What changed
> A test that went FAILING → REMOVED and later reappeared **passing** was stuck as REMOVED forever with its episode open: `compute_diff` only emits `newly_fixed` for identities FAILED in the baseline, and a REMOVED test is absent from the baseline, so the passing reappearance landed in no diff bucket (and `apply_run` had no REMOVED → FIXED edge). `apply_run` now reconciles any identity that passes the current run while its failure episode is still open into `diff.newly_fixed`, so the normal fix path closes the episode (`fixed_in_run_id`/`fixed_at`, state FIXED). The reconciliation lives in `apply_run` — not `compute_diff`, which is also recomputed for historical runs (run page, email) where present-time episode state must not leak in. The intended boundary is untouched: a reappearance that **fails** continues the same open episode (no new episode, no acknowledgement clearing), and re-applying the same run stays idempotent. Two unit tests pin the fixed scenario and the boundary.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 517 passed, 3 skipped; ruff clean
> - [x] `docs-overview-maintainer` considered (invoke it if the app's parts / communications / workflows changed) — pure bug fix — no parts/communications/workflow change
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq)_


<a id="pr-131"></a>

### #131 — fix(ingest): stop stringifying NULL V_TRACKING columns to "None" (#119)

- **State:** Merged
- **Branch:** `fix/119-oracle-null-columns` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/131

> Closes #119
>
> ## What changed
> `_row_to_change` (`src/uta/refdb/oracle.py`) built its row dict from `cursor.description`, so every selected column key always exists and a SQL NULL arrives as Python `None` — the `.get(..., "")` defaults were dead code, and `str(row.get("PKLST", ""))` persisted the literal string `"None"` as the candidate's pk (rendered as `pk None` in the dashboard and the LLM prompt); a NULL `LXTABLECODE`/`TYPE` would likewise flow `None` into non-optional `str` fields. NULLs are now normalized explicitly, following the existing `pk_ref` precedent: NULL `LXTABLECODE` / `PKLST` / `TYPE` become `""` (matching `DataChange`'s non-optional `str` fields); the optional fields keep passing `None` through. Added two unit tests in `tests/unit/test_oracle_feed.py`: an all-NULL row yields `""` for the stringified fields (and no `"None"` string anywhere), and normal values pass through unchanged.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 517 passed, 3 skipped; `ruff check .` clean
> - [x] `docs-overview-maintainer` considered (invoke it if the app's parts / communications / workflows changed) — pure bug fix — no parts/communications/workflow change
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq)_


<a id="pr-133"></a>

### #133 — fix(flakiness): require same-track consistency for shard_correlated

- **State:** Merged
- **Branch:** `fix/124-shard-correlated-track` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/133

> Closes #124
>
> ## What changed
> `compute_stats` flagged `shard_correlated` whenever every failing run in the window failed in exactly one track while the other passed — without checking that it was the **same** track, so failures alternating between `permanent` and `permanent_py39` (ordinary flakiness) still set the flag, contradicting the documented "failures cluster in ONE track" semantic and misdirecting the flaky-leaderboard infra tell. The per-run qualification is kept; the fix additionally requires the union of `fail_tracks` across the qualifying runs to be exactly one track. Tests added for the alternating-track case (now `False`) and the degenerate single-failing-run case (still `True`); the existing consistent-single-track test stays green.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 517 passed, 3 skipped; `ruff check .` clean
> - [x] `docs-overview-maintainer` considered (invoke it if the app's parts / communications / workflows changed) — pure bug fix — no parts/communications/workflow change
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq)_


<a id="pr-134"></a>

### #134 — fix(dashboard): make test_search honor limit<=0 as "no cap" (#123)

- **State:** Merged
- **Branch:** `fix/123-search-limit-zero` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/134

> Closes #123
>
> ## What changed
> `test_search` passed `ui_row_limit` straight into `.limit()`, so the documented "disable the cap" value `0` emitted `LIMIT 0` — the navbar "jump to test" search answered "No tests match" for every query and the unique-match redirect never fired. It now skips `.limit()` when `limit <= 0`, matching the `_cap` / `_page_window` semantics, and the docstring says so. Added unit tests: `limit=0` returns all matches, a positive limit still caps.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"` — 517 passed, 3 skipped; `ruff check .` clean)
> - [x] `docs-overview-maintainer` considered (pure bug fix — no parts/communications/workflow change)
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq)_


<a id="pr-135"></a>

### #135 — fix(demo): make control-state seeding idempotent on re-seed

- **State:** Merged
- **Branch:** `fix/122-idempotent-seed` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/135

> Closes #122
>
> ## What changed
> `_seed_control_state` now `session.merge()`s (upserts) the fixed-PK rows — `PollerHeartbeat(id=1)`, the `BuildQuarantine` build, and the two `SettingOverride` keys — and deletes the previous seed's demo-actor `IngestJob` rows before inserting, so re-running `uta seed-demo` against a persistent store converges to the same state instead of dying with a duplicate-PK `IntegrityError` at the final commit (or duplicating the auto-PK ingest jobs). No change to the seeded values.
>
> Added `test_reseeding_the_same_store_converges` (offline): seeds the same store twice with a fixed anchor — no exception, exactly one heartbeat / one quarantine / two overrides / two demo ingest jobs, values identical to a fresh single seed.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 516 passed, 3 skipped; `ruff check .` clean
> - [x] `docs-overview-maintainer` considered (invoke it if the app's parts / communications / workflows changed) — pure bug fix, no parts/communications/workflow change
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq)_


<a id="pr-136"></a>

### #136 — fix(email): wire SMTP credentials into SmtpEmailSender with STARTTLS + login

- **State:** Merged
- **Branch:** `fix/120-smtp-auth` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/136

> Closes #120
>
> ## What changed
> - `SmtpEmailSender` now takes optional `user`/`password`/`starttls`; when a user is configured it negotiates STARTTLS and calls `login()` before `send_message`. No credentials ⇒ behavior identical to before (plain unauthenticated send). The password is never logged.
> - `build_email_sender` forwards `smtp_user`/`smtp_password`/`smtp_starttls` from `Settings` (previously the documented `SMTP_USER`/`SMTP_PASSWORD` were dead config, so on an auth-requiring relay every alert send raised and was swallowed by the best-effort alert path).
> - New `SMTP_STARTTLS` setting forces TLS on/off; unset it defaults to on exactly when credentials are set. An empty `SMTP_STARTTLS=` (as `.env.example` ships every key) parses as "unset", not a startup error.
> - Documented in `.env.example` and the README config table (which had marked the keys "Reserved — not yet used"); tests added to `tests/unit/test_email.py` with a recording fake `smtplib.SMTP` — no socket ever opened.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 520 passed, 3 skipped; `ruff check .` clean
> - [x] `docs-overview-maintainer` considered (invoke it if the app's parts / communications / workflows changed) — pure bug fix — no parts/communications/workflow change
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq)_


<a id="pr-137"></a>

### #137 — fix(infra): make send_ops_alert best-effort so SMTP outages can't break /health or the tick record

- **State:** Merged
- **Branch:** `fix/121-guard-ops-alert` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/137

> Closes #121
>
> ## What changed
> - `send_ops_alert` now guards `sender.send()` like its sibling `send_alert`: a send failure is logged (warning + traceback) and swallowed, returning `None` so callers see non-delivery. `check_health` keeps its existing "latch `stale_alerted_at` only on success" semantics and returns the proper stale/503 `HealthReport` instead of raising, and the poller's quarantine/skip alert paths can no longer escape `poll_once` and wipe the tick's heartbeat record (`processed=[]`).
> - The `smtplib.SMTP` dial in `SmtpEmailSender.send` now carries a 10 s timeout, so a black-holed relay fails fast instead of hanging `/health` for the platform connect timeout on every probe. No other change to `SmtpEmailSender`.
> - Tests: raising-sender fakes pin all three bug scenarios — `send_ops_alert` returns `None` without raising; `check_health` with a raising sender returns the stale report, leaves the latch unarmed, and a later working relay still alerts once; `poll_tick`/`poll_once` with a raising sender still record the ingested builds (heartbeat `last_processed`, `last_success_at`) past a 404-skipped and a quarantined build. Plus a monkeypatched check that the SMTP dial passes a timeout.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 521 passed, 3 skipped; `ruff check .` clean
> - [x] `docs-overview-maintainer` considered (invoke it if the app's parts / communications / workflows changed) — pure bug fix — no parts/communications/workflow change
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq)_


<a id="pr-138"></a>

### #138 — fix(infra): make /health report a never-succeeded poller stale (#127)

- **State:** Merged
- **Branch:** `fix/127-health-never-succeeded` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/138

> Closes #127
>
> ## What changed
> `check_health` fell back from `last_success_at` to `last_poll_at`, but `last_poll_at` moves on **every** tick — so a poller misconfigured from day one (`last_success_at = NULL` forever, every tick failing) reported `poller: "ok"` indefinitely, contradicting the module's own contract ("a poller that ticks but keeps failing goes stale too"). The fallback now uses the heartbeat row's `created_at` instead: the same one-off grace window (`poller_stale_after_intervals × poll_interval_seconds`) covers both the upgrade window the fallback existed for (row predating the `last_success_at` column) and a fresh failing deployment, then flips to stale once the window passes without any success. Missing heartbeat row still reports `poller: "never"` (200, the web-only/demo topology); healthy pollers unaffected. Two unit tests added in `tests/unit/test_poller_resilience.py` (stale after grace with a fresh `last_poll_at`, ok within grace).
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 517 passed, 3 skipped; ruff clean
> - [x] `docs-overview-maintainer` considered (invoke it if the app's parts / communications / workflows changed) — pure bug fix — no parts/communications/workflow change
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq)_


<a id="pr-139"></a>

### #139 — fix(kb): rank and label similar cases by the strongest of both provenance columns

- **State:** Merged
- **Branch:** `fix/126-retrieval-provenance` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/139

> Closes #126
>
> ## What changed
> KB retrieval ranked and labeled similar cases by `reason_provenance` only, so an attribution where a triager entered just the causing person (`cause_provenance` HUMAN_ENTERED/HUMAN_CORRECTED, `reason_provenance` still AI_UNCONFIRMED) got weight 0 — ranking below unconfirmed AI guesses on near-equal text matches and rendering with no `[provenance]` tag in the LLM prompt, contradicting the module contract that validated human knowledge ranks first. Extracted the per-attribution "stronger of cause/reason" logic (already used by `strongest_provenance_weight`) into `_strongest_provenance` in `src/uta/kb/retrieval.py` and use it for `_best_attribution`'s ranking key and `_to_case`'s provenance label + weight. Added a unit test asserting a human-entered cause outranks an unconfirmed AI reason at equal similarity and carries the human provenance label.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 516 passed, 3 skipped; ruff clean
> - [x] `docs-overview-maintainer` considered (invoke it if the app's parts / communications / workflows changed) — pure bug fix, no parts/communications/workflow change
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq)_


<a id="pr-140"></a>

### #140 — fix(demo): re-stamp seeded heartbeat on /health so the demo never goes stale

- **State:** Merged
- **Branch:** `fix/125-demo-health-staleness` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/140

> Closes #125
>
> ## What changed
> The demo seeds a poller heartbeat to populate `/control` but runs no poller, so ~21 minutes into the process (`poll_interval_seconds × poller_stale_after_intervals` = 1500 s by default) the stamp crossed the staleness window and `/health` flipped to 503 "poller stale" — and Render's `healthCheckPath: /health` then restarted the service, wiping the ephemeral store (and any visitor's triage edits) mid-session.
>
> Demo-side fix in `src/uta/demo/app.py`: a middleware in `create_demo_app` re-stamps the seeded heartbeat's `last_poll_at`/`last_success_at` before every `/health` probe, so the pollerless demo stays 200 for the process's whole lifetime while `/control` still renders the seeded tick details (processed builds/count untouched). `check_health` and real-deployment staleness detection are unchanged; `seed.py` is untouched.
>
> New test `test_demo_health_stays_ok_past_the_staleness_window` ages the seeded heartbeat 6 h past the window, sanity-checks that bare `check_health` reports the stale fault that used to 503 the demo, then asserts the demo app's `/health` returns 200 with `poller: "ok"` and the `/control` panel still shows a populated, fresh heartbeat.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 516 passed, 3 skipped; `ruff check .` clean
> - [x] `docs-overview-maintainer` considered (invoke it if the app's parts / communications / workflows changed) — bug fix — no parts/communications/workflow change
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq)_


<a id="pr-141"></a>

### #141 — fix(kb): recompute orphaned signature aggregates on re-ingest

- **State:** Merged
- **Branch:** `fix/116-orphaned-signature-aggregates` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/141

> Closes #116
>
> ## What changed
> - `ingest_build` now captures the signature ids linked to the run's old results **before** the idempotent delete and passes them to `record_signatures_for_run`, which recomputes the **union** of old and new affected signatures — a signature whose failure vanished (or re-hashed) on re-ingest now actually gets the documented zero/empty reset instead of keeping a stale `occurrence_count` / `last_seen_run_id`.
> - Same-root fix in `_recompute_aggregates_bulk`: `first/last_seen_run_id` were `min/max(Run.id)` while `first/last_seen_at` were `min/max(started_at)` — wrong after a historical re-ingest (quarantine recovery gives an older build a higher run id). The recompute now ranks by `started_at` (run id as tie-break), still one grouped query.
> - Tests: pipeline-level re-ingest scenario (occurrence 4 → 2, last-seen repointed to the run actually containing the failure), all-links-lost zero/empty reset, store-level changed-error-text orphan via the new `stale_signature_ids` param, and first/last-seen-run-id chronology under out-of-order run ids.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 519 passed, 3 skipped; `ruff check .` clean
> - [x] `docs-overview-maintainer` considered (invoke it if the app's parts / communications / workflows changed) — pure bug fix, no parts/communications/workflow change
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq)_


<a id="pr-142"></a>

### #142 — fix(dashboard): make triage "Load all" expand links preserve filters and sort

- **State:** Merged
- **Branch:** `fix/132-expand-preserves-filters` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/142

> Closes #132
>
> ## What changed
> The `more_hint` macro emitted `href="?expand=…#section"`, replacing the whole query string — a filtered triage view's "Load all N Tests" link (whose N is the post-filter count) landed on the full unfiltered, default-sorted bucket, silently dropping filters and sort. The per-section expand URLs are now pre-built in the view layer (`views.triage_expand_urls`, on the same `_triage_url` builder as the issue-#77 chips and header sort links): every active filter and the sort survive, the section is merged into the already-expanded set exactly once, and the `#section` anchor is kept. The macro takes the pre-built URL; the now-unused global `expand` render-context entry was dropped.
>
> Tests: view-layer unit tests for `triage_expand_urls` (filters+sort preserved; merge with already-expanded sections) and an HTTP-level test asserting a filtered capped page's expand link carries `owner` + `sort` + `expand`, and that following it renders the filtered bucket in full (518 passed, 3 skipped).
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`)
> - [x] `docs-overview-maintainer` considered (pure bug fix — no parts/communications/workflow change)
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_016rfT4XAyx9t4DNyX7bWXvq)_


<a id="pr-146"></a>

### #146 — feat(dashboard): keep-your-place navigation — back-links + episode anchors

- **State:** Merged
- **Branch:** `feat/143-keep-your-place-nav` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/146

> Closes #143
>
> ## What changed
> - **Back-links on the drill-down pages (N1):** new shared `ui.breadcrumb` macro (`_macros.html`); the test record shows "← Triage queue" preserving the referring filtered/sorted queue URL, the run detail shows "← Job runs". The triage queue's record links carry the queue's URL-encoded state as `?return=` (only when non-default), and `views.triage_url` (formerly `_triage_url`) builds it.
> - **Same-origin safety:** `_same_origin_path` accepts only absolute-path relative references (no scheme/authority, no `//host`, no backslash tricks); an unusable `?return=` falls back to the plain list URL. The PRG `back()` builder now reduces the Referer to its validated same-origin path + query — a crafted absolute referer can no longer redirect off-app.
> - **Episode anchors (N4):** each episode card gets a stable `id="episode-N"`; the episode-scoped actions (Save attribution, Confirm AI suggestion, Apply-to-all-with-signature) pass the anchor via a hidden form field and redirect back with `#episode-N` appended (validated, fragments never reach the server via Referer), landing the browser on the card just edited. The `?return=` param survives the bounce since it rides the referer's query.
> - **Demo:** exercises both surfaces naturally already — the flaky oscillator record has 7 episodes (anchors), and any filter/sort produces `?return=`-carrying links — so no `dataset.py` change.
> - Tests: `tests/unit/test_web_navigation.py` (27 cases) covering the sanitizer gate, breadcrumb rendering/fallbacks, return-param propagation, fragment redirects, invalid-anchor drop, and the off-app referer hardening.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 547 passed locally (only the known container-environment `test_worktree_helper` failure, which passes in CI); ruff clean
> - [x] `docs-overview-maintainer` considered — deferred to orchestrator, running once across the three queued UX PRs
> - Smoke-checked against the demo dataset: filtered queue → record → "← Triage queue" restores the exact URL; `/runs/612` shows "← Job runs"; the 7-episode record renders every anchor.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01P86RiPLhh1YD7sjjG7RacC
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01P86RiPLhh1YD7sjjG7RacC)_


<a id="pr-147"></a>

### #147 — fix(dashboard): pass/fail readable without color + explicit UTC timestamps

- **State:** Merged
- **Branch:** `fix/144-status-not-color-alone` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/147

> Closes #144
>
> ## What changed
> - **Non-color status cues (V1):** the runs-table Passed / Failed / Skipped / Regressions / Newly-fixed counts now carry a small aria-hidden ✓ / ✕ / ○ glyph next to the existing red/green coloring, via a shared `count_cell` macro in `_macros.html` (zero counts in the conditional columns render as plain undecorated numbers). Places that already spell out the status word (run results, test record, lifecycle) are left untouched — no double decoration.
> - **Sparkline second channel:** failed bars render full-height, passed bars shorter and bottom-aligned (`charts.sparkline` now emits per-bar `y`/`height`; 0.55 × chart height for passes). Colors unchanged; per-bar `<title>` tooltips already existed.
> - **Explicit UTC timestamps (D5):** `format_ts` appends an explicit ` UTC` label and wraps the text in a `<span>` whose hover `title` carries the full ISO-8601 timestamp with offset (naive datetimes treated as UTC). `format_reltime`'s hover title reuses the same UTC-labelled text. Centralized in the one filter, so every `|ts` render site picks it up.
> - Tests updated/added: `test_ts_filter.py` (suffix, ISO title, naive-as-UTC, offset preservation), `test_reltime_filter.py`, `test_charts.py` (height channel), `test_web_dashboard.py` (glyphs on `/runs`, plain zeros, UTC label + ISO title in rendered HTML), `test_web_m4.py` (bar heights on `/flaky`), `test_dashboard_views.py` (new bar geometry).
>
> Demo rule: the demo dataset already shows failing runs, regressions and sparklines, so every changed surface is exercised without dataset growth — verified by rendering the demo app (`/runs`, `/runs/{n}`, `/flaky` all show glyphs, UTC labels, ISO titles, and both bar heights).
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 527 passed; only pre-existing environmental failure `test_worktree_helper.py::test_url_for_db_swaps_only_the_database_name` (container-local, passes in CI). `ruff check src tests` clean.
> - [ ] `docs-overview-maintainer` considered — deferred to orchestrator, running once across the three queued UX PRs
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01P86RiPLhh1YD7sjjG7RacC
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01P86RiPLhh1YD7sjjG7RacC)_


<a id="pr-148"></a>

### #148 — feat(dashboard): error snippets in triage queue + trace clamp/copy on test record

- **State:** Merged
- **Branch:** `feat/145-triage-error-snippet` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/148

> Closes #145
>
> ## What changed
> - **Triage queue:** New and Still-failing rows show a muted one-line error snippet under the test name — the traceback's closing exception line (JUnit `errorDetails` is usually the constant "test failure", so the exception line is the informative part), falling back to the details field, truncated to 160 chars. Carried through the existing batched `_failure_infos` query (no N+1; the query-count guard passes unchanged). New `kb.signature.display_message` reuses the normalizer's "last exception line wins" rule so snippet and signature always describe the same failure.
> - **Test record:** error details / stack traces longer than 15 lines are clamped client-side behind a "Show full trace (N lines)" toggle, plus a "Copy trace" button (full trace on the clipboard, with a non-secure-context fallback). Vanilla vendored `static/trace.js`, progressive enhancement — the full text always ships in the HTML.
> - **Demo:** `test_timezone_convert`'s seeded trace is padded past 15 lines with *library* frames (ignored by the signature normalizer, so signatures / KB similarity stories are untouched) so the live demo exercises the clamp; every failing queue row already yields a distinct snippet from its exception line.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 532 passed; the only failure is the known container-environment-only `test_worktree_helper` (passes in CI). New unit tests cover the view projection (`error_type`/`error_snippet`, fallback, truncation, still-failing bucket), `display_message`, HTML rendering of snippets in both tables, and the record's clamp/copy hooks; demo integration tests assert snippets on every New row and the >15-line trace.
> - [x] `docs-overview-maintainer` considered — deferred to orchestrator, running once across the three queued UX PRs
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01P86RiPLhh1YD7sjjG7RacC
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01P86RiPLhh1YD7sjjG7RacC)_


<a id="pr-149"></a>

### #149 — docs: reflect triage-queue error snippets + trace clamp in OVERVIEW.html

- **State:** Merged
- **Branch:** `docs/overview-triage-error-snippet` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/149

> Refs #145
>
> ## What changed
> `docs-overview-maintainer` pass over the three merged UX PRs (#146, #147, #148): only #148 was material. Updated the `#triage` section of docs/OVERVIEW.html — the New and Still-failing bucket cards now mention the one-line error snippet under each test name, and the per-test record paragraph notes the 15-line trace clamp with show-full toggle and copy button. #146 (navigation plumbing) and #147 (presentation/accessibility polish) required no update. No SVG/parts change — no part, communication, or workflow stage changed.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — docs-only change, suite unaffected
> - [x] `docs-overview-maintainer` considered (this PR is its output)
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01P86RiPLhh1YD7sjjG7RacC
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01P86RiPLhh1YD7sjjG7RacC)_


<a id="pr-153"></a>

### #153 — fix(dashboard): preserve ?expand= across filter/sort; cap run-diff lists with counts

- **State:** Merged
- **Branch:** `fix/151-url-state-run-diff` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/153

> Closes #151
>
> Finishes the URL-state coherence work started in #142, plus the run-page diff readability fix.
>
> **Part 1 — `?expand=` survives filter/sort changes (triage).** `triage_filter_chips` and `triage_sort_links` now take the expanded-section set and thread it through the existing `triage_url` builder (the pattern #142 established), and the filter form carries a hidden `expand` input next to the existing hidden `sort`. Applying/removing a filter or re-sorting no longer collapses expanded sections. "Clear" deliberately remains a bare `/` (full reset, expand included) — documented and tested.
>
> **Part 2 — run-page diff lists capped with counts.** Diff buckets were unbounded comma-separated link streams with no counts. Now: `DIFF_ROW_LIMIT = 20`, per-bucket totals in the row headers ("Regressions — new failures (25)"), and view-built "Show all N" URLs via `run_expand_urls` (mirrors `triage_expand_urls`: preserves the whole query string including `failures_only` and results pagination, distinct expand keys per bucket, anchors to the diff section).
>
> Demo dataset untouched — it already shows a non-empty diff; seeding >20 rows just to show the cap isn't worth the bloat.
>
> **Tests:** 7 new (view-layer URL builders + page-level renders), 2 existing diff-shape assertions updated. Offline suite green (606 passed; the one failure locally is the known env-only `test_worktree_helper` sqlalchemy issue, unrelated).
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01VKpMwgVVTzQPxyf5r8pXTS
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01VKpMwgVVTzQPxyf5r8pXTS)_


<a id="pr-154"></a>

### #154 — fix(dashboard): trustworthy triage actions — ack anchors, truthful bulk flash, disable-on-submit, toast flashes

- **State:** Merged
- **Branch:** `fix/150-triage-action-trust` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/154

> Closes #150
>
> Four small trust/feedback fixes on the dashboard's action loop:
>
> 1. **Ack keeps your place.** Hidden `anchor` fields (`new` / `still_failing`) on the per-row ack, signature-ack, bulk-ack and bulk-attribute forms, passed through the routes via the existing `back(request, anchor=...)` mechanism (issue #143's pattern, `_ANCHOR_RE`-validated) — acknowledging no longer scrolls you back to the top of the queue.
> 2. **Truthful bulk flash.** New `actions.has_attribution_input()` mirrors `set_attribution`'s write conditions; `bulk_set_attribution` returns 0 on all-blank input instead of counting untouched episodes. The route now distinguishes no-selection, blank-input ("Nothing to apply — fill in a status, person or reason"), and vanished-episode cases — no more "Updated 5 selected tests" after writing nothing.
> 3. **Disable-on-submit.** Vendored `form-busy.js` (bulk-select.js style): disables the submitter on submit (deferred a tick so name/value still post) and swaps in a spinner + "Working…"; `pageshow` restores bfcache'd buttons. Kills double-POSTs that re-stamp `validated_at`/actor.
> 4. **Toast flashes.** Flash messages are now a fixed bottom-right toast with `role="status"` `aria-live="polite"`, 6 s auto-dismiss with pause-on-hover, manual dismiss kept — visible regardless of anchor scroll position and announced to screen readers.
>
> Verified end-to-end against the real `uta.demo` app (ack → `/#new` redirect, toast markup, all-blank bulk → error flash). Offline suite green (608 passed; the single local failure is the known env-only `test_worktree_helper` sqlalchemy issue, unrelated — passes in CI). Ruff check + format clean.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01VKpMwgVVTzQPxyf5r8pXTS
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01VKpMwgVVTzQPxyf5r8pXTS)_


<a id="pr-155"></a>

### #155 — feat(dashboard): show blast-radius count on "Ack all w/ signature (N)"

- **State:** Merged
- **Branch:** `feat/152-signature-blast-radius` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/155

> Closes #152
>
> "Ack all w/ signature" previously committed blind — the user learned it hit N tests only from the after-the-fact flash, and there is no un-acknowledge route, so a mis-scoped signature-wide ack is irreversible. The button now shows its blast radius **before** the click: `Ack all w/ signature (34)`, and renders only when the count is > 1 (a count of 1 adds nothing over plain Acknowledge).
>
> **Implementation.** Signatures are per-test (two tests with the same error get distinct `FailureSignature` rows), so this is not a `GROUP BY signature_id`: the triage projection gains exactly one extra batched query — collect the pre-filter, pre-cap New bucket's signature ids, load their `normalized_text` in one `IN` query, group by `actions._error_key` in Python (imported, not duplicated, so the grouping can never drift from what `acknowledge_by_signature` does at commit time) — and attaches `signature_ack_count` to each New row. Counting is deliberately pre-filter/pre-cap because the bulk action ignores the view's filters; a test pins that a track-filtered view hiding the sibling still shows (2). The query-count guard is updated (5 flat queries).
>
> **Consistency asserted directly:** a test with three sharers (one pre-acknowledged) checks the shown count equals `acknowledge_by_signature`'s return. Row clustering by signature is explicitly out of scope.
>
> **Demo:** the seeded SMTP-outage pair already surfaces the feature — new integration test asserts the demo renders exactly two `Ack all w/ signature (2)` buttons and no other bulk-ack button. `docs/OVERVIEW.html` New-bucket prose updated via the docs-overview-maintainer agent.
>
> Offline suite green (604 passed; the single local failure is the known env-only `test_worktree_helper` sqlalchemy issue, unrelated — passes in CI). Ruff check + format clean.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01VKpMwgVVTzQPxyf5r8pXTS
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01VKpMwgVVTzQPxyf5r8pXTS)_


<a id="pr-156"></a>

### #156 — docs: align web-card signature-ack wording with the (N) blast-radius button

- **State:** Merged
- **Branch:** `docs/overview-signature-ack-consistency` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/156

> Refs #152
>
> Follow-up from the docs-overview-maintainer pass after #153/#154/#155: the `web` container part card in `docs/OVERVIEW.html` still said "acknowledge all with this signature" (wording from #107), now inconsistent with the New-bucket card updated in #155. Aligned it with the shipped `Ack all w/ signature (N)` behavior and its N>1 gating. The maintainer confirmed #153 and #154 need no OVERVIEW changes (presentation/trust polish within already-documented surfaces).
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01VKpMwgVVTzQPxyf5r8pXTS
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01VKpMwgVVTzQPxyf5r8pXTS)_


<a id="pr-160"></a>

### #160 — Add in-app Help page (workflow, statuses, LLM feedback loop)

- **State:** Merged
- **Branch:** `claude/in-app-user-docs-900ywx` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/160

> Closes #161
>
> ## What changed
> - New `/help` page (`src/uta/web/templates/help.html`, linked from the navbar) explaining, for the person actually using the dashboard:
>   - the daily triage workflow (New / Still failing / Recently fixed, Acknowledge, bulk and signature-wide actions, filters, per-test record)
>   - the full status/badge glossary (raw result statuses, lifecycle states, triage status, predicted cause + confidence, and the smaller badges: track, reopened ×N, flaky, shard-correlated, flakiness pattern, overridden, run-state colors)
>   - what the LLM does (a one-sentence root-cause hypothesis, RAG'd from deterministic signals + similar past knowledge-base cases) versus the deterministic classifier
>   - how to act on an AI suggestion — Confirm vs. manual edit, the four provenance tiers, and how that feeds future confidence scores and the Control panel's AI-suggestion-accuracy metric
>   - the knowledge base, a tour of the other dashboard pages, and the external deep links (Jira/FishEye/ZEPHYR)
> - Broadened the `docs-overview-maintainer` agent (and CLAUDE.md's sync-trigger section, and the PR template checklist) to also own the new Help page, so future status/badge/LLM-feedback changes prompt a check of it, the same way architectural changes already prompt a check of `docs/OVERVIEW.html`.
>
> ## Test plan
> - [x] `pytest -m "not live"` green (626 passed, 3 skipped)
> - [x] `ruff check .` clean
> - [x] New tests in `tests/unit/test_web_help.py` (page renders, navbar link + active-state highlight)
> - [x] Visually verified the rendered page in both light and dark themes via a real browser against the demo app


<a id="pr-162"></a>

### #162 — feat(dashboard): render classification evidence — "Why this prediction" on the test record

- **State:** Merged
- **Branch:** `feat/159-classification-evidence` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/162

> Closes #159
>
> The test record asked the user to "Confirm AI suggestion" with only a bare confidence badge — the classification's evidence JSON was parsed and shipped to the template context but never rendered. Each episode with a classification now gets a collapsed **"Why this prediction"** `<details>` under the predicted-cause line, so the Confirm button sits next to its justification.
>
> **What's rendered** (whitelisted, human-labelled — not raw JSON): infra-error flag, code/data candidates in the correlation window ("2 candidates · 1 matched this test"), the top code/data match ("r48612 by … (score 3) — reasons"), the tie-break (only when set), and the confidence inputs ("relevance score 3 vs 2 · KB provenance weight 4"). `baseline_run_id` is deliberately dropped (internal store PK). Degenerate string/list payloads render as a single row; empty payloads render no shell. New `_evidence_items` shaping in views.py; the raw `evidence` context key is untouched, no new queries.
>
> **Demo:** the demo seeds through the real pipeline, so the tie-break episode already carries a full payload — a new integration test asserts the demo record page shows the collapsed block with the match/tie-break/confidence rows. `docs/OVERVIEW.html`'s per-test-record output description updated via the docs-overview-maintainer agent (verdict: material).
>
> **Tests:** 2 shaping + 2 render + 1 demo integration. Offline suite green (627 passed; single local failure is the known env-only `test_worktree_helper` sqlalchemy issue — passes in CI). Ruff clean.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01VKpMwgVVTzQPxyf5r8pXTS
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01VKpMwgVVTzQPxyf5r8pXTS)_


<a id="pr-163"></a>

### #163 — feat(dashboard): linkify owner/suite/cause, clickable failed count, cross-referring search empty states

- **State:** Merged
- **Branch:** `feat/157-pivot-links` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/163

> Closes #157
>
> Turns inert facts into pivots — href-only changes into routes that already exist.
>
> **1. Pivot links.** New `views.pivot_url(key, value)` builds single-filter queue URLs through the existing `triage_url` (encoding matches the filter bar exactly); URLs are precomputed per row in the view layer and rendered via one shared `ui.pivot` macro with subtle dotted-underline styling. Linkified: triage owner + predicted-cause cells (a human-entered reason still wins as plain text in Still-failing), run-results owner, flaky-leaderboard owner, search-result suite + owner. Clicking never inherits the current view's other filters — single-filter by design.
>
> **2. Actionable failed count.** The run header's failed total links to `?failures_only=1#results` when > 0; the heading reads "Results — failures only (N of M)" when active (M from existing totals, no extra query). The failures-only checkbox now submits on change (the triage instant-filter pattern), Apply kept as no-JS fallback. Side fix: `tests/builders.make_run` now mirrors the pipeline's totals computation.
>
> **3. Cross-referring empty states.** `/search`'s zero-result state links the same query into `/kb?q=…` and vice versa (URL-encoded, only on non-empty-query zero-result renders).
>
> **Demo:** no dataset change needed — new integration tests assert the seeded demo exercises every pivot surface, the failed-count link/heading on run 612, and both empty-state cross-links (encoding asserted). docs-overview-maintainer consulted: no OVERVIEW.html update needed.
>
> Offline suite green (640 passed; single local failure is the known env-only `test_worktree_helper` sqlalchemy issue — passes in CI). Ruff clean.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01VKpMwgVVTzQPxyf5r8pXTS
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01VKpMwgVVTzQPxyf5r8pXTS)_


<a id="pr-164"></a>

### #164 — docs(help): document the evidence panel, pivot links, failed-count deep-link and search cross-referral

- **State:** Merged
- **Branch:** `docs/help-page-catchup-157-159` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/164

> Refs #157, #159
>
> The `/help` page had only its creation commit and was never checked against today's dashboard changes. Docs-maintainer pass over the cumulative #153/#154/#155/#162/#163 merges:
>
> - **"Acting on an AI suggestion"** now describes the collapsed "Why this prediction" panel (top code/data match, tie-break, confidence inputs) next to the Confirm button (#162).
> - **"Daily workflow"** notes owner/suite/predicted-cause values are clickable pivots to the pre-filtered queue (#163).
> - **Job-runs row** notes the failed count deep-links to failures-only results; the **Knowledge base** card notes the `/search` ↔ `/kb` empty-state cross-referral (#163).
> - #154/#153 assessed as UI polish with no user-facing concept change — no doc edits. OVERVIEW.html verified already current (updated in #155/#162/#156).
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01VKpMwgVVTzQPxyf5r8pXTS
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01VKpMwgVVTzQPxyf5r8pXTS)_


<a id="pr-165"></a>

### #165 — Owner = main developer (SVN blame), not the ZEPHYR test-case author (#114)

- **State:** Merged
- **Branch:** `feat/114-owner-main-developer` → `main`
- **Opened:** 2026-07-12 · **Merged:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/165

> ## What & why
> The dashboard **Owner** had been silently taken over by the **ZEPHYR test-case author** (initials from a failing test's `ZEPHYR TEST CASE INFO` block). That was never wanted. This restores the original intent (retired `PLAN.md`): **Owner = the test's main developer**, resolved from `svn blame` of the test's source file.
>
> ## Changes
> - **New SVN-blame boundary** behind an interface (`uta.refdb.svn.SvnBlameClient`) + CLI impl (`svn blame --xml`, modal line author) + offline fake + path mapping. Gated by `SVN_BLAME_ENABLED` (default off) exactly like the Oracle/LLM live paths — the offline gate, local dev and the demo touch no SVN.
> - `analyze/ownership` resolves `TestIdentity.main_developer`; wired into ingest (incremental, per run's failing tests) and a new **`uta reattribute-owners`** backfill CLI (the "fix existing data" pass).
> - **ZEPHYR author kept as honest ZEPHYR metadata**: `owner_initials` → `zephyr_owner` (identity + result), surfaced on the per-test record next to the ZEPHYR links (e.g. "(owner kam)"). ZEPHYR deep-links unchanged.
> - **Schema migration** renames the columns (data preserved) and adds `main_developer` (NULL until blame).
> - **UI**: Owner column/filter/sort, the flakiness leaderboard, and the regression email now read `main_developer`.
> - **Demo** seeds synthetic main developers via `SyntheticSvnBlame` so the live demo shows the new meaning.
> - **Docs**: OVERVIEW.html (new SVN-blame part + system-map box + info-model) and the in-app **Help page** updated to define Owner and distinguish the ZEPHYR owner.
>
> ## Fix existing data
> The migration re-labels existing ZEPHYR data under its honest name; `main_developer` is populated by ingest (flag on) or a one-shot `uta reattribute-owners`.
>
> ## Testing
> `pytest -m "not live"` green (incl. new `test_svn_blame`, `test_ownership`) + ruff clean. The real `svn` path is unit-tested against a fake and gated `live` — it cannot run in CI or without SVN access, same as the Oracle/LLM real paths.
>
> Closes #114


<a id="pr-167"></a>

### #167 — Install subversion in the Docker image so owner blame works (#166)

- **State:** Merged
- **Branch:** `fix/166-svn-cli-in-image` → `main`
- **Opened:** 2026-07-13 · **Merged:** 2026-07-13
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/167

> ## Problem
> `uta reattribute-owners` and the incremental owner-resolution from #114 resolve **0** owners in the deployed stack: `SvnCliBlameClient` shells out to `svn`, but the image (`python:3.12-slim`) installed only `tzdata`. A missing binary is caught and returned as `None` (blame must never fail ingest), so every blame silently no-oped. Verified against production: 13,011 identities, 57,739 results with a source path, blame confirmed working from an env that *has* `svn`, yet 0 resolved.
>
> ## Fix
> Add `subversion` to the image's apt install.
>
> ## After merge (deployment)
> ```
> git pull && docker compose build && docker compose up -d
> docker compose run --rm poller uta reattribute-owners
> ```
>
> Closes #166


<a id="pr-169"></a>

### #169 — feat(dashboard): show Owner in the still-failing bucket and as a pivot link on the record page

- **State:** Merged
- **Branch:** `feat/168-owner-still-failing-and-record` → `main`
- **Opened:** 2026-07-14 · **Merged:** 2026-07-14
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/169

> ## What & why
>
> The test **Owner** (main developer, resolved via `svn blame`) was surfaced only in the **New failing** triage bucket, even though every triage row already carries `owner`/`owner_url`. Owner is just as useful when chasing or escalating a test that has been failing for a while — so this adds an **Owner column (pivot link)** to the **Still failing** bucket, matching New.
>
> Separately, the **per-test record page** rendered owner as plain inline text (`· owner X`), inconsistent with the run summary, search, and flaky pages, which all render it as a clickable **pivot link**. It now uses the same pivot link (the view exposes `owner_url` on the record dict).
>
> The **Recently fixed** bucket deliberately keeps no Owner column — those tests are no longer actionable.
>
> ## Changes
> - `triage.html` — Owner header + pivot cell in the Still-failing table.
> - `test_record.html` — owner rendered via `ui.pivot(...)`; `views.py` adds `owner_url` to the record dict.
> - Test: `test_still_failing_bucket_and_record_show_owner_pivot` asserts the pivot renders in the Still-failing bucket and on the record page.
> - `help.html` — lists the record page among the owner pivot surfaces (via docs-overview-maintainer; OVERVIEW.html needed no change).
>
> ## Demo
> No dataset change needed — the demo already seeds acknowledged still-failing tests with synthetic owners, so the new column is exercised in the live demo automatically.
>
> ## Testing
> - `ruff check .` + `ruff format --check .` clean.
> - Offline dashboard/demo suites green (`pytest -m "not live"`).
>
> Closes #168
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)


<a id="pr-170"></a>

### #170 — docs: give docs-overview-maintainer a third surface — the config reference

- **State:** Merged
- **Branch:** `docs/112-config-docs-guardrail` → `main`
- **Opened:** 2026-07-16 · **Merged:** 2026-07-16
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/170

> Completes the remaining half of #112 (aspect 2), in the lighter-convention form agreed earlier: **no second agent** — instead broaden the existing [`docs-overview-maintainer`](.claude/agents/docs-overview-maintainer.md).
>
> ## Context
> Since aspect 1 (the README Auth/Keycloak subsection) merged in #113, the agent had already grown from **one** owned surface (OVERVIEW.html) to **two** (OVERVIEW.html + the in-app Help page). So aspect 2 is re-applied fresh against that current structure rather than cherry-picked from the now-stale earlier commit.
>
> ## What
> Adds the **README Configuration section + `.env.example`** as a **third owned surface** — the settings reference for operators:
> - **Agent:** a third "material" block (a `config.py` field / `.env.example` key added, removed, renamed, re-gated, or a changed default/effect; a new subsystem → a new table subsection); a per-surface edit rule (keep README and `.env.example` mutually consistent, same placeholder/redaction discipline as the fixtures); and a widened ownership carve-out — it may now edit README.md's Configuration section and `.env.example`, but still **never** `config.py`, app code, or CLAUDE.md.
> - **[CLAUDE.md](CLAUDE.md) "Keep the docs in sync":** adds the settings-surface trigger, so the agent must be invoked when config keys change.
>
> ## Why
> The auth/Keycloak table was missing from the README for a long time despite the feature being fully wired — because nothing prompted a config-doc sync check. This closes that gap using the one agent already in the workflow.
>
> ## Test
> Agent-definition + CLAUDE.md only — no application code, no runtime surface. Offline gate unaffected.
>
> Closes #112
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)


<a id="pr-173"></a>

### #173 — Add domain-modeling skills, initialize CONTEXT.md, and rename Run → Build

- **State:** Merged
- **Branch:** `claude/add-skills-to-repo-yp1pti` → `main`
- **Opened:** 2026-07-23 · **Merged:** 2026-07-23
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/173

> Closes — no tracking issue; this shipped from a live domain-modeling session (the first `/grill-with-docs` run).
>
> ## What changed
>
> - **Skills**: vendored `grill-with-docs` + its dependencies `grilling` and `domain-modeling` (from mattpocock/skills) into `.claude/skills/`.
> - **Domain model initialized**: root `CONTEXT.md` (ubiquitous-language catalogue, 15 curated terms with `_Avoid_` synonyms; Track/Shard deferred) and `docs/adr/0001` (CONTEXT.md owns terminology, OVERVIEW.html owns architecture, `docs-overview-maintainer` guards both). CLAUDE.md and the agent remit updated to make CONTEXT.md the fourth guarded doc surface.
> - **Run → Build rename** (the session's first term decision): ORM `Run`→`Build`, `RunShard`→`BuildShard`; Alembic migration `a7b8c9d0e1f2` renames 2 tables, 13 columns, 6 indexes, 2 unique constraints (pure renames, no data touched); `/runs`→`/builds` routes with 301 redirects so deep links in already-sent alert emails keep working; templates, UI copy, demo dataset and tests renamed; the build number is exposed as `number` (no more `run.build` stutter). Run-as-a-verb prose deliberately kept.
> - **Docs synced** by `docs-overview-maintainer`: OVERVIEW.html (incl. system-map SVG + Reference/Configuration tables), help.html, README, `.env.example`.
>
> Note for deploy: the VM stack applies the table renames on its next `alembic upgrade head`.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — run in batches; migration additionally verified upgrade→downgrade→upgrade against a throwaway Postgres 16; `ruff check` + `ruff format --check` green; legacy `/runs` redirects smoke-tested on the demo app
> - [x] `docs-overview-maintainer` considered — invoked; it edited all of OVERVIEW.html, help.html, README and `.env.example`, and verified CONTEXT.md needed no change
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01QePnhAE6Zq5RoFHT7kHR3k
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01QePnhAE6Zq5RoFHT7kHR3k)_


<a id="pr-175"></a>

### #175 — Rename shard → track: one term for the parallel lanes

- **State:** Merged
- **Branch:** `claude/shards-vs-track-language-of47v6` → `main`
- **Opened:** 2026-07-23 · **Merged:** 2026-07-24
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/175

> Closes #174
>
> ## What changed
> Domain-modeling session outcome: **Track** is the single canonical term for the parallel lanes the nightly build runs the test suite in; **shard** is banned (`_Avoid_` in CONTEXT.md) — nothing is partitioned, every lane runs the full suite, so CI-style "sharding" was the wrong metaphor. Recorded in new **ADR-0002**; CONTEXT.md gains the **Track** entry and loses the "deliberately not yet defined" footnote.
>
> Clean break at all depths, per the agreed mapping: `BuildShard` → `BuildTrack`, `ShardTiming` → `TrackTiming`, `build.shards` → `build.tracks`, `shard_correlated` → `track_correlated`, `expected_shards` → `expected_tracks`; table `build_shards` → `build_tracks` via pure-rename migration `b8c9d0e1f2a3` (the `track` column is untouched — it matches `test_results.track`); build-page heading "Tracks", "track-correlated" badge; help page, OVERVIEW.html, README config table and `.env.example` synced. Historical migrations keep their old names (the new migration renames *from* them). Completeness semantics unchanged (still a track *count*).
>
> > [!WARNING]
> > **Operator-breaking:** `EXPECTED_SHARDS` → `EXPECTED_TRACKS`, deliberately with no compat alias. If the VM deployment's `.env` sets it (default is 2), rename the key when deploying this.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`: 800 passed, migration tests skip locally without Postgres and run in CI); `ruff check .` + `ruff format --check .` green; `alembic heads` shows the single new head
> - [x] `docs-overview-maintainer` invoked — it updated OVERVIEW.html (10 mentions, incl. its `EXPECTED_TRACKS` settings row) and verified help.html, README + `.env.example`, and CONTEXT.md consistent
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01XyU5CBrzXh23NK6wUwCJnG
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01XyU5CBrzXh23NK6wUwCJnG)_


<a id="pr-176"></a>

### #176 — Correct "nightly build" language: the analyzed pipeline is the Permanent Pipeline (per commit)

- **State:** Merged
- **Branch:** `claude/rename-build-permanent-pipeline-a2inys` → `main`
- **Opened:** 2026-07-24 · **Merged:** 2026-07-24
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/176

> ## What changed
>
> The analyzed Jenkins job (`…build-release-permanent`) was described everywhere as the "nightly build". It is **not** nightly — it runs permanently, **one build per commit**, which is precisely *why* the poller polls Jenkins continuously. This scrubs "nightly" as a descriptor of this pipeline across docs, code comments, and the LLM prompt (terminology only — no logic changes).
>
> - **CONTEXT.md**: added a first-class **Permanent Pipeline** term; redefined **Build** as "one execution of the Permanent Pipeline"; reworded **Track** to note the `permanent` prefix merely echoes the pipeline name (a track's distinguishing attribute is its execution environment).
> - **"nightly" is reserved, not banned** — it correctly names a *separate* pipeline not yet monitored by this app; recorded via an `_Avoid_` note.
> - **ADR-0003** records the factual correction and why `Permanent Pipeline` is first-class (anticipating a future nightly pipeline); **ADR-0002** gets a supersession pointer on its "nightly" premise.
> - Synced the four doc surfaces (README, OVERVIEW.html, help.html, .env.example) via `docs-overview-maintainer`, plus CLAUDE.md, into the corrected language.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — all in-scope unit + integration tests pass; the lone `test_worktree_helper` failure is environmental (its subprocess uses the system interpreter, which lacks the project deps in this remote sandbox — unrelated to this text-only change). `ruff check .` and `ruff format --check .` both clean.
> - [x] `docs-overview-maintainer` invoked — the domain language changed (new `Permanent Pipeline` term), so all four surfaces were reviewed and updated.
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_017StYFohdEaEZqoNNMeRnia)_


<a id="pr-179"></a>

### #179 — Accept "Jenkins run"/"pipeline run" as prose synonyms for Build

- **State:** Merged
- **Branch:** `claude/grill-with-docs-synonym-eome9r` → `main`
- **Opened:** 2026-07-24 · **Merged:** 2026-07-24
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/179

> Closes #178
>
> ## What changed
> The CONTEXT.md **Build** entry now accepts the compound forms "Jenkins run" and "pipeline run" as *prose* synonyms (Jenkins's own API calls builds *runs* — `wfapi/runs` — translated to Build at the ingest boundary), while keeping **Build** as the sole canonical term for identifiers, schema, routes, and UI labels. Standalone "run" stays under `_Avoid_`, now with its reason spelled out: ambiguous with a single test's execution. No code changes.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — doc-only diff; `ruff check` + `ruff format --check` pass locally, CI runs the full gate
> - [x] `docs-overview-maintainer` considered — invoked; it confirmed OVERVIEW.html, the Help page, and the README config reference need no update (they only use "run" as a verb / in the pre-existing `/runs` redirect note)
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01Vf1bp3So84MmZ7utYPjFyD)_


<a id="pr-180"></a>

### #180 — perf: build-boundary data-change window; re-derive retention estimate

- **State:** Merged
- **Branch:** `claude/grill-with-docs-lfalg8` → `main`
- **Opened:** 2026-07-24 · **Merged:** 2026-07-24
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/180

> Closes #177
>
> ## What changed
>
> Both numbers were sized against the old ~365-builds/year (once-a-night) assumption, which ADR-0003 corrected to one build per commit (~15–20/active weekday).
>
> **Data-change lookback → build-boundary window (ADR-0004).** A fixed 12h lookback overlapped ~20 neighbouring builds at per-commit cadence, over-attributing `ut_ref` changes (flipping episodes to DATA_CHANGE, skewing the relevance tie-break, mis-suggesting the contact). The window's lower bound is now the **previous build's start** — each change is a candidate for the first build that ran after it, self-adapting to cadence. Anchored at the previous build's *start*, not its end, because `ut_ref` data can change *during* a build's run: a test that already ran misses it, so the change must stay a candidate for the next build (a one-build overlap accepted by design — coverage over clean-partition for a triage-support tool).
> - New setting **`DATA_CHANGE_MAX_LOOKBACK_DAYS`** (default `30`): caps the reach and is the fallback when there's no previous build (first-ever build / cold start).
> - **Removed** `DATA_CHANGE_LOOKBACK_HOURS`; `DATA_CHANGE_TOLERANCE_MINUTES` unchanged.
> - Governs *data*-change candidates only; code candidates come from the build's own `changeSets` and are untouched.
>
> **Retention estimate re-derived.** `retention.py` docstring no longer quotes "~9M rows/year" (that baked in the nightly assumption). At per-commit cadence gross growth is ~110M rows/yr, which is *why* pruning matters — it holds passing/skipped rows to a bounded ~28M-row 90-day window. `RESULT_RETENTION_DAYS=90` confirmed (comfortably above `FLAKY_WINDOW_DAYS=30`); noted that the kept-forever failing rows now grow ~12× faster but stay small (out of scope here).
>
> **Demo:** seeds the intra-build-change edge case (`test_status_transition`) — a `ut_ref` change during the previous build's run attributed to the failing build. Existing data-change examples verified to still land under the new window.
>
> **Docs:** README + `.env.example` (key swap), `docs/OVERVIEW.html` (correlation flow + config row), `CONTEXT.md` ("Change Candidate" phrasing), and new `docs/adr/0004-data-change-attribution-window.md`.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — full unit + integration suites pass locally (one pre-existing, environment-only failure in `test_worktree_helper.py`, unrelated: its subprocess uses system `python3` which lacks sqlalchemy here; passes in CI). New/updated tests cover the previous-build-start window, the first-build cap fallback, the long-gap cap, and the intra-build-change attribution end-to-end. `ruff check .` and `ruff format --check .` both clean.
> - [x] `docs-overview-maintainer` invoked — updated README, `.env.example`, OVERVIEW.html, and CONTEXT.md; help.html unchanged (window mechanics aren't end-user-facing).
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_016N2UWpeRT3YbgNF8wRqaW6)_


<a id="pr-182"></a>

### #182 — feat: add Build Incident triage for pipeline-level build failures

- **State:** Merged
- **Branch:** `claude/jenkins-ut-analyzer-docs-qh7gxd` → `main`
- **Opened:** 2026-07-24 · **Merged:** 2026-07-24
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/182

> Closes #171
>
> ## What changed
> Adds a build-level triage entity — **Build Incident** — so Jenkins pipeline failures/aborts are managed alongside test failures.
>
> - **Model/lifecycle**: opens on a build whose top-level result is `FAILURE`/`ABORTED`, collapses a streak of consecutive non-green builds into one incident (mixed kinds stay one), recovers on the next `SUCCESS`/`UNSTABLE`. `hung`/`slow` kinds reserved for #172.
> - **Detection**: folded into the existing ingest path (runs even when test analysis is skipped; high-water mark still advances), gated by new `INGEST_BUILD_INCIDENTS` (default on).
> - **Enrichment**: `FAILURE` reuses the full stack — change candidates, deterministic classification, LLM hypothesis, confirm/correct provenance — with an incident-namespaced failure signature from the failing stage's log (no cross-matching with test signatures); `ABORTED` is human-documented only.
> - **Triage fields (generalized to test episodes too)**: new **Assignee** and **Resolution Ticket**; existing single ticket field renamed/migrated to **Cause Ticket**.
> - **UI/alerts**: dedicated `/incidents` queue, per-build inline incident card, open-incident nav badge, and an email alert on a newly opened `pipeline_failure`.
> - **Migration**: new `build_incidents` table, ticket rename, `assignee`/`resolution_ticket` columns, `failure_signatures.kind`.
> - **Demo**: seeds a failure streak that recovers and an open abort.
> - Follow-up #181 (Teams notifications) filed, non-blocking.
>
> ## How verified
> - [x] Offline gate green (`ruff check` + `ruff format --check` + `pytest -m "not live"` in batches: 687 passed; the 3 migration up/down tests skip locally with no Postgres and run in CI)
> - [x] `docs-overview-maintainer` invoked — updated OVERVIEW.html, help.html, CONTEXT.md, and README + `.env.example`
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01B4h2P4LLHTb6E11NYATyJW)_


<a id="pr-183"></a>

### #183 — docs(adr): record ADR-0005 for the Build Incident entity

- **State:** Merged
- **Branch:** `claude/jenkins-ut-analyzer-docs-qh7gxd` → `main`
- **Opened:** 2026-07-25 · **Merged:** 2026-07-25
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/183

> Refs #171
>
> ## What changed
> Adds **ADR-0005** retroactively capturing the load-bearing design decisions behind the Build Incident feature (shipped in #182), and cross-links it from OVERVIEW.html's Build Incidents section (matching the ADR-0004 precedent). No code changes; CONTEXT.md already carries the terminology.
>
> The ADR records *why*:
> - Build Incident is a **distinct build-level entity**, not a stretched Failure Episode (test identity vs. build identity).
> - A **general** incident with a kind discriminator, not a failure-only entity — so #172's `hung`/`slow` land as enum values, not a migration.
> - **Streak** lifecycle (not one-incident-per-build), recovering on `SUCCESS`/`UNSTABLE`.
> - Failure-signature **namespacing** (TEST vs INCIDENT, no cross-match).
> - The **Cause Ticket / Resolution Ticket / Assignee** generalization.
>
> Background: this ADR should have been produced during the original `grill-with-docs` session (which chains grilling + domain-modeling); the domain-modeling half was missed, so this backfills it.
>
> ## How verified
> - [x] Offline gate green — docs-only change (ADR markdown + one OVERVIEW cross-link), no code touched, so `pytest -m "not live"` is unaffected
> - [x] `docs-overview-maintainer` scope considered — CONTEXT.md/OVERVIEW/help/README already synced in #182; ADRs are the domain-modeling surface, added here
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01B4h2P4LLHTb6E11NYATyJW)_


<a id="pr-186"></a>

### #186 — docs: record ADR-0006 + CONTEXT.md terms for the #172 split (overrunning builds)

- **State:** Merged
- **Branch:** `claude/grill-with-docs-ticket-1t5cg3` → `main`
- **Opened:** 2026-07-26 · **Merged:** 2026-07-26
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/186

> Design outcome of a grill-with-docs session on #172 (long-running pipelines),
> now split into a tracking issue + two children (#184, #185):
>
> - ADR-0006: an overrunning in-progress build is an ephemeral, poller-observed
>   live signal (a dashboard banner), NOT a persisted Build Incident; the durable
>   record comes only from the existing ABORTED path. Revises ADR-0005's
>   assumption that both reserved kinds land as incident kinds — HUNG does not.
> - CONTEXT.md: add Expected Duration + Overrunning Build; drop HUNG from the
>   Incident Kind note; standardize on the canonical term "overrunning".
>
> Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
> Claude-Session: https://claude.ai/code/session_01R5ANQBzu2FHMoYG2QeGmCv


<a id="pr-187"></a>

### #187 — feat: visualize overrunning in-progress pipelines

- **State:** Merged
- **Branch:** `claude/issue-184-injebd` → `main`
- **Opened:** 2026-07-26 · **Merged:** 2026-07-26
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/187

> Closes #184
>
> ## What changed
> Surface a still-running pipeline that has run past its Expected Duration as a **live, poller-observed banner** on the triage dashboard so a human can go stop it. An Overrunning Build is **never** a Build Incident (ADR-0006) — the durable record only comes from the `aborted` incident if someone stops the build.
>
> - **Detection (poller = single source of truth):** new `JenkinsClient.last_build()` → `LastBuild(number, building, timestamp)`; `expected_duration_seconds()` = median wall-clock of the last 20 `SUCCESS`/`UNSTABLE` builds (undefined below the sample); each tick the poller observes the in-progress build, writes a single-row snapshot on the heartbeat, and emails **once** per overrunning build (de-duped by a persisted marker, survives restart).
> - **Overrunning** when `elapsed > expected × (1 + overrun_ratio)` (default `1.0` ⇒ 2× median).
> - **Dashboard:** always-on in-progress banner reflecting the stored snapshot, computing only `elapsed` live at render; highlighted iff the stored flag is set; omits "expected" below the 20-build baseline.
> - **Config:** `DETECT_OVERRUNNING_BUILDS` (default true), `OVERRUN_RATIO` (default 1.0, live-tunable), `POLL_INTERVAL_SECONDS` 300 → 60.
> - **Domain:** removed `IncidentKind.HUNG` (no detector ever wrote it); `slow` stays reserved.
> - **Demo:** seeds an un-flagged in-progress build so the banner's normal state is on show.
> - Alembic migration `d1e2f3a4b5c6` adds the six `overrunning_*` heartbeat columns.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — 681 passed, 3 skipped (Postgres-only migration tests); ruff check + format clean. New coverage in `test_overrunning.py` and `test_jenkins_client.py`.
> - [x] `docs-overview-maintainer` invoked — OVERVIEW.html, help.html, README + .env.example updated; CONTEXT.md already matched.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> https://claude.ai/code/session_01AbdLbuxV1EjyoZm9AR6bUG
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01AbdLbuxV1EjyoZm9AR6bUG)_


<a id="pr-188"></a>

### #188 — Multi-channel alerting: Microsoft Teams webhook channel

- **State:** Merged
- **Branch:** `claude/grill-with-docs-181-gt716z` → `main`
- **Opened:** 2026-07-26 · **Merged:** 2026-07-26
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/188

> Closes #181
>
> ## What changed
>
> Generalizes the email-only delivery layer into a **multi-channel alert layer** (ADR-0007) and adds a **Microsoft Teams** channel.
>
> - **`delivery/alert.py`** (new): channel-neutral `Alert` + `AlertKind` (incident/regression/recovery/overrun/ops), `AlertChannel` protocol, `wants()` compose-guard, best-effort `dispatch()` (per-channel isolation — one channel failing never blocks the other or the ingest).
> - **`delivery/email.py`**: `EmailAlertChannel` renders an `Alert` to the same plain text as before (byte-for-byte); the five composers now return kind-tagged `Alert`s.
> - **`delivery/teams.py`** (new): `TeamsAlertChannel` POSTs an Adaptive Card (Power Automate Workflows `attachments` envelope) to a webhook via `httpx`, ~10s fail-fast, behind an injectable-client seam (no socket in the offline suite).
> - **`config.py`**: `+TEAMS_WEBHOOK_URL` (secret, never logged), `+TEAMS_EVENTS` (default empty, opt-in), `+EMAIL_EVENTS` (default `incident,regression,overrun,ops`, preserving today's behavior); **removed `EMAIL_RECOVERY_NOTICE`** (its effect is now "is `recovery` in `EMAIL_EVENTS`"); startup fail-fast on an unknown kind.
> - **`clients.py::build_channels(...)`** + wiring in `ingest/pipeline.py`, `poller.py`, `control/health.py`, `web/app.py`, `cli.py`. Back-fill / on-demand ingest pass no channels (history never re-alerts).
>
> **Routing** is a full per-event × per-channel matrix via the two `*_EVENTS` allowlists; each channel is enabled independently (Email iff SMTP host+recipients; Teams iff webhook set).
>
> **Docs/design:** ADR-0007 + CONTEXT.md `Alert Channel`/`Alert Kind` entries; OVERVIEW.html (Teams as the 5th external system, system-map SVG, Alerting section), README + `.env.example` synced (new keys, `EMAIL_RECOVERY_NOTICE` dropped), one Help-page wording tweak. Also corrects a pre-existing OVERVIEW drift (poll cadence 300s→60s). No demo-dataset change (backend side-effect; demo leaves Teams unconfigured).
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — run in 4 batches (whole-suite OOMs in this container); ~700 passed, 3 skipped (need real Postgres). `ruff check .` and `ruff format --check .` both pass. Acceptance check encoded as a test: webhook configured + `incident` in `TEAMS_EVENTS` → a new `pipeline_failure` incident POSTs a card linking back to `…/builds/N`; unconfigured/unsubscribed → no POST.
> - [x] `docs-overview-maintainer` invoked — it updated OVERVIEW.html, README, `.env.example`, and the Help page; CONTEXT.md confirmed already correct.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)


<a id="pr-190"></a>

### #190 — feat: search the triage queue by failure detail

- **State:** Merged
- **Branch:** `claude/grill-with-docs-189-wgr4eo` → `main`
- **Opened:** 2026-07-27 · **Merged:** 2026-07-27
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/190

> Closes #189
>
> ## What changed
>
> Adds a free-text **failure detail** filter to the triage queue's filter bar (URL param `failure`).
>
> - Case-insensitive substring match against the **raw** failure text (error message + stack trace) of each open/recent episode's characterising result — the same text the row's snippet is drawn from. Typing `uuid4` pulls out every currently-queued test whose latest failure mentions it.
> - Plugs into the existing filter machinery: renders a removable chip ("failure detail: uuid4"), narrows all three buckets before capping, stays fully bookmarkable/shareable via the URL (sort + expanded sections preserved). No new queries — the full failure text is already fetched into each episode's projection.
> - Scope: searches the current triage queue only (not the full failure history) and leaves the name-based `/search` page untouched. Plain substring, no regex/AND/whole-word.
> - **CONTEXT.md**: new **Failure Detail** term (raw error text of a Test Result), distinct from the normalized Failure Signature.
> - **Demo**: seeds a New-bucket failure whose error text names `uuid4` (the ticket's worked example) so the live demo exercises the filter.
> - **Docs**: Help page + OVERVIEW filter-bar lists updated.
>
> ## How verified
> - [x] Offline gate green (`pytest -m "not live"`) — dashboard views, demo/integration, web app/dashboard/help, navigation, and query-count batches all pass; `ruff check .` + `ruff format --check .` clean.
> - [x] `docs-overview-maintainer` considered — invoked; it updated `help.html` and `docs/OVERVIEW.html` (filter-bar lists), confirmed README/.env.example need no change, and verified the CONTEXT.md term.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> ---
> _Generated by [Claude Code](https://claude.ai/code/session_01KqyV719hStok7ibkxV5kXD)_


<a id="pr-192"></a>

### #192 — chore(dashboard): remove the triage queue's Suite filter

- **State:** Merged
- **Branch:** `chore/191-remove-suite-filter` → `main`
- **Opened:** 2026-07-27 · **Merged:** 2026-07-27
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/192

> Closes #191
>
> ## Why
>
> The triage filter bar's **Suite** field matched `TestIdentity.suite`. For every devUTs test that value is the literal JUnit suite-element name `nose2-junit` — the report exposes exactly two suite elements, one per track, both with that name ([`ut_report.py`](../blob/main/src/uta/ingest/ut_report.py) takes `suite["name"]` verbatim). The module prefix people actually filter by (`ut_ldt`, `ut_pricing`, …) lives in `class_name` / `canonical_name`, which the filter never read.
>
> So the control could only ever select "all devUTs tests" or one of the five console-log stage suites — while its placeholder, `e.g. ut_pricing`, promised module filtering it could not deliver. That is how this surfaced: filtering on `ut_ldt` returned nothing even though those tests were failing.
>
> ## What
>
> - drop `suite` from `_TRIAGE_FILTER_KEYS`, `_matches_filters`, `_CHIP_LABELS` — a stale `?suite=` bookmark is now **inert** rather than silently hiding rows (covered by a test)
> - drop `suites` from `triage_filter_options` (the datalist source) and the now-dead `suite` key from the triage row projection
> - remove the Suite input + datalist from `triage.html`
> - render suite as plain text in the search pick-list — its pivot pointed at the filter that no longer exists
>
> Suite stays a *displayed* fact on the test record and in search results. Narrowing to a module is the navbar search's job (`canonical_name ILIKE`), and `help.html` / `OVERVIEW.html` now say so — including *why* there is no suite filter, so nobody re-adds one.
>
> A dedicated triage-queue name/module filter is deliberately out of scope; worth a follow-up issue if the search box turns out not to cover it.
>
> ## Test
>
> `ruff check .` + `ruff format --check .` clean; `pytest -m "not live"` green in batches (730 passed). New/updated tests: a stale `suite=` param leaves every bucket intact, the filter bar renders no Suite control, search rows carry no `suite_url`, and the navbar search narrows by module prefix (`ut_ldt`).
>
> Doc surfaces updated inline (this session is configured not to dispatch subagents): `help.html` and `OVERVIEW.html` filter-bar copy. README/`.env.example` unaffected — no settings change. CONTEXT.md unaffected — "suite" is not a catalogued term and the `suite` attribute on Test Identity is unchanged.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)


<a id="pr-193"></a>

### #193 — Add failure-episode status and sorting to global test search

- **State:** Merged
- **Branch:** `claude/global-test-search-enhancements-pgajmz` → `main`
- **Opened:** 2026-07-28 · **Merged:** 2026-07-28
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/pull/193

> Enhance the /search page so each result shows its failure-episode status and results are sortable.
>
> **Failure status per row** (one signal each):
> - **open episode** — the test is failing now.
> - **removed** — the test disappeared from the suite while failing; its episode stays open (gone ≠ fixed), so it's flagged distinctly rather than shown as "failing now" (mirrors the triage queue).
> - **closed** — the most recent episode closed (the test passed again), with the relative close time.
> - **no failures on record** — never failed.
>
> **Sortable column headers** (Test / Owner / Latest failure), single-direction like the triage queue. Default sort is by most recent failure episode, newest-first; never-failed tests sort last.
>
> Episode facts come from one grouped scan of the matched identities' episodes joined into the query (plus a lifecycle join for the removed flag) — no per-row lookups — and the sort + cap are applied in SQL so the top-N by recency are the ones returned. NULL ordering is expressed portably so Postgres and SQLite agree.
>
> Scope: `/search` stays an enriched navigation aid, not a second triage queue — no filters, no bulk actions, no open-first ranking (status is display-only, never a ranking key). The triage queue remains the single prioritization surface.
>
> **Docs:** CONTEXT.md gains an "Open / closed episode" glossary entry and a fix to the Failure Episode definition (removal leaves an episode open); the in-app Help page describes the new status column and sorting.
>
> This branch is merged up to date with `main` (including #192's Suite-filter removal, which also dropped the suite pivot from search rows).
>
> Extends the global test search delivered in #63 (now closed); refs #191.

