# PROGRESS — Jenkins UT Analyzer

The **durable, committed checklist** of what's done and what's open. Source of truth for status;
update it as part of every change (it diffs in PRs). The phased plan lives in
[IMPLEMENTATION-PLAN.md](./IMPLEMENTATION-PLAN.md); this file tracks execution against it.

_Last updated: 2026-06-27 (Milestone 3)_

## Legend
`[x]` done & verified · `[~]` in progress · `[ ]` not started

---

## Slice 0 — end-to-end spike (de-risk the load-bearing layer)

**Goal:** ingest one real run end-to-end and render it, proving the formats + clock model.

### Done
- [x] **Real artifacts captured** from build **#1702** (Jenkins `testReport` / `changeSets` /
      `wfapi`; Oracle `V_TRACKING` sample + DB clock facts).
- [x] **Golden fixtures committed** (anonymized) under `tests/fixtures/` — stack-trace values
      redacted, raw `MODDATA` dropped; structure (paths, lines, exception classes, ZEPHYR initials)
      preserved.
- [x] **`CLAUDE.md`** operating contract (invariants + testing contract, points at the plan).
- [x] **Package skeleton**: `pyproject.toml`, `src/uta/`, `config.py` (typed env settings),
      `db.py` (engine/session, `DATABASE_URL`).
- [x] **`clock.py`** — Jenkins-UTC + ut_ref `Europe/Luxembourg` (DST-aware) normalization.
      **8 unit tests** incl. summer/winter/DST-boundary and naive↔aware guards.
- [x] **Parsers**, golden-tested against #1702 fixtures:
  - [x] `ut_report.py` (devUTs JUnit → per-`(test, track)` results; file/line + ZEPHYR owner).
  - [x] `svn_update.py` (changeSets → code-change candidates, UTC).
  - [x] `wfapi.py` (per-shard UT timing + completeness + run window).
- [x] **External clients behind interfaces + offline fakes**: `ingest/jenkins.py`
      (`HttpJenkinsClient`), `refdb/oracle.py` (`OracleTrackingFeed`, `MODDATA` never selected),
      `llm/` (`NoopHypothesisProvider`). Fakes in `tests/fakes/`.
- [x] **Ingest pipeline** (`ingest/pipeline.py`) — fetch→parse→persist, idempotent re-ingest;
      `data_change_window` lookback (changes precede the nightly run — confirmed on #1702).
- [x] **Minimal schema** (`models/`: `Run`, `TestResult` keyed by `(run, test, track)`).
- [x] **Read-only web view** (`web/app.py` + `run.html`) listing a run's tests.
- [x] **CLI** (`cli.py`: `init-db`, `backfill`).
- [x] **Offline suite green: 30 passed**, `ruff` lint + format clean.

### Done (cont.)
- [x] **Container infra**: `Dockerfile` (single image, role via command, tzdata),
      `docker-compose.yml` (web/poller/db, healthchecks, `WEB_PORT` override), `.dockerignore`.
- [x] **GitHub Actions CI** (`.github/workflows/ci.yml`): ruff → `pytest -m "not live"` → coverage,
      with a `services:` Postgres.
- [x] **Live end-to-end verified** (2026-06-27): `docker compose up`, `uta backfill 1702` ingested
      **25,592** results (counts match source), run window UTC-normalized (17:08→18:41Z),
      `/runs/1702` renders. **`V_TRACKING` tz proven**: latest change naive-local 15:46 → 13:46Z;
      436 candidates in the lookback window. Captured as `live`-marked tests in `tests/live/`.

### Open
- [ ] Make CI a **required status on protected `main`** (needs GitHub web UI or `gh` — branch
      protection; can't be done from code alone).
- [ ] First **branch + PR**.

---

## Milestone 1 — full schema + migrations  ·  `[x]`
Alembic migrations for the full Information model; `CREATE EXTENSION pg_trgm`; indexing from scale.

### Done
- [x] **Full Information-model schema** (`src/uta/models/`, one module per concern, re-exported):
      `Run` + `RunShard`, `TestIdentity` (alias self-ref), `TestResult` (keyed `(run, identity,
      track)`), `TestLifecycle` (state + `flaky` + `reopen_count` + acknowledgement), `FailureEpisode`
      (per fail→fix cycle, `current_episode` back-pointer via `use_alter`), `Attribution`
      (cause/reason + provenance tier + original-AI value + validator), `Classification`
      (cause/confidence-nullable/LLM hypothesis), `CodeChangeCandidate` + `DataChangeCandidate`
      (run-windowed signals), `FailureSignature` (normalized text + hash + trigram GIN). Enums kept as
      portable `varchar` (`enums.py`).
- [x] **Alembic** scaffolded; `env.py` wired to `Base.metadata` + `DATABASE_URL` (12-factor, not
      `alembic.ini`). Initial migration `31fdfa8031ac` creates all 11 tables.
- [x] **`CREATE EXTENSION pg_trgm`** + the `gin_trgm_ops` GIN index in the migration; **startup
      assertion** `assert_pg_trgm()` wired into the web lifespan + `uta migrate`/`backfill`.
- [x] **`uta migrate`** (alembic upgrade head) replaces Slice-0's `create_all`; `init-db` is now an
      alias.
- [x] **Verified against real Postgres** (docker): `upgrade → downgrade base → upgrade` round-trips
      clean, `alembic check` reports **no drift**, `pg_trgm` + GIN + `similarity()` all live, and the
      `use_alter` circular FK lands.
- [x] **Tests**: `test_models.py` (9, SQLite — relationships, constraints, defaults, alias,
      failure-history-as-results, cascade) + `test_migrations.py` (3, real Postgres, **skip-if-absent**
      so the gate stays green offline; runs in CI via the `services:` Postgres). Offline suite: **42
      passed** (39 + 3 skipped without PG); ruff clean.

### Scale sizing (B3)
~25k tests × 2 tracks ≈ **50k `test_results` rows/run**; at ~1 run/day ≈ **18M rows/year**. Covered by
B-tree indexes on `test_results(run_id)`, `(test_identity_id)`, `(status)` and the unique
`(run, identity, track)`. Time/run partitioning of `test_results` is **deferred** until row counts
warrant it (no code change — a migration when needed).

## Milestone 2 — ingest pipeline + classification  ·  `[x]`
Scheduled poll (APScheduler); complete-run baseline + diff; lifecycle state machine + episodes;
deterministic CODE/DATA/INFRA/UNKNOWN from time-windowed candidates.

### Done
- [x] **`analyze/` package** — analysis derives only from persisted facts, so re-running it for an
      already-processed run is idempotent (the offline gate proves this).
- [x] **Baseline + diff** (`analyze/baseline.py`): `select_baseline` walks back to the most recent
      **complete** run (incomplete runs stored/shown but skipped); per-identity status collapses both
      tracks (FAILED in either ⇒ failing); `compute_diff` →
      regressions / newly-fixed / still-failing / removed; the chosen baseline id is stamped on the run.
- [x] **Lifecycle state machine + episodes** (`analyze/lifecycle.py`): `apply_run` drives
      `FAILING`/`FIXED`/`REMOVED` against the baseline (not the stored state → **idempotent per
      (baseline, run)**). Regression opens an episode; reopen bumps `reopen_count` and **clears
      acknowledgement**; fix closes the episode (only on a real pass, never on REMOVED — disappeared ≠
      fixed); `age_runs` + all-time/episode first-failure pointers maintained. Only ever-failing tests
      get a lifecycle row.
- [x] **Deterministic classification** (`analyze/classify.py`): per new episode, `INFRASTRUCTURE`
      (error_type INFRA) > `CODE_CHANGE`/`DATA_CHANGE` (one signal kind in window) > `UNKNOWN`
      (both/neither). **No confidence number** (deferred to §4); evidence JSON records the candidate
      counts.
- [x] **Error-type derivation** (`analyze/error_type.py`): ASSERTION/EXCEPTION/TIMEOUT/INFRA/UNKNOWN
      from status + stack trace, set on every result at ingest (INFRA ordered first).
- [x] **Pipeline wired** (`ingest/pipeline.py`): now also persists **code-change candidates** (SVN
      changeSets) and **data-change candidates** (`ut_ref` feed, when supplied) over the lookback +
      **tolerance (B1)** window, then runs the analysis for **complete** runs. Re-ingest clears+rebuilds
      candidates and re-runs analysis without duplicating episodes/classifications.
- [x] **Scheduled poller** (`poller.py` + `uta poll`): high-water mark = `max(Run.build_number)` in
      the DB (restart-safe, converges with back-fill); ingests every new completed build oldest-first
      on an APScheduler interval. `last_completed_build` added to the Jenkins client + fake.
      `uta backfill <build> [--to N]` now ingests a range.
- [x] **Tests (+27, offline gate green: 69 passed, 3 skipped)**: `test_error_type`,
      `test_baseline_diff`, `test_lifecycle` (regression/fix/reopen+ack-clear/removed/still-failing/age,
      **re-apply idempotency**), `test_classify` (all four causes), `test_poller` (selection +
      idempotent poll), and pipeline coverage that ingest drives lifecycle/episodes/classification and
      persists code+data candidates. ruff lint + format clean.

### Open / deferred to later milestones
- **Flaky flag** is computed in M4 (oscillation over the 30-day window); the diff's "flaky" column is
  intentionally not populated yet.
- **Acknowledgement** is cleared on reopen here, but the **set** action arrives with the M3 dashboard.

## Milestone 3 — dashboard (FastAPI + HTMX)  ·  `[x]`
Triage queue (§0), per-test record (§1) with acknowledge/confirm/edit, run summary (§2).

### Done
- [x] **Phase-1 self-declared identity** (`web/identity.py`): the acting user is a plain string read
      from the `uta_actor` cookie, defaulting to `app_default_actor` (`test-user`). Set via a header
      form (`POST /identity`); every human action is stamped with it. Phase-2 (Keycloak) swaps only
      *how* the value is obtained — no data-model change.
- [x] **§0 triage queue** (`web/views.triage_queue`, `GET /`): the three buckets as a pure
      **projection** of lifecycle `state` × the orthogonal `acknowledged` attribute — **New**
      (FAILING & unacknowledged, newest-first), **Still failing** (FAILING & acknowledged, plus
      `REMOVED` open episodes surfaced with a distinct **Removed** flag), **Recently fixed** (FIXED
      within `recently_fixed_days`, default 7). Counts double as the health indicator.
- [x] **§1 per-test record** (`web/views.test_record`, `GET /tests/{id}`): identity + lifecycle,
      every failure **episode** (first/last/fixed runs, age, triage), the latest failing result
      (error type / details / stack / `file:line` / Jenkins link), and the **candidate code/data
      changes** in the failure window — chronological.
- [x] **§2 run summary** (`web/views.run_summary`, `GET /runs/{build}`): totals, per-shard timing,
      the chosen **baseline** + the diff (regressions / newly-fixed / still-failing / removed) each
      linking to the per-test record, and the full results table. Replaces the Slice-0 list view.
- [x] **Actions with provenance** (`web/actions.py`): **Acknowledge** (stamps actor, moves New →
      Still-failing); one-click **Confirm** of an AI suggestion (`AI_CONFIRMED`, retains original);
      **edit** causing-person / reason / triage — provenance derived vs the AI suggestion
      (`AI_CONFIRMED` / `HUMAN_CORRECTED` + original AI value retained / `HUMAN_ENTERED`). All
      Post/Redirect/Get; thin route handlers, logic in views/actions, templates never touch a live
      session.
- [x] **Templates** (`base.html` + `triage.html` / `test_record.html` / `run.html`): server-rendered
      Jinja, no external assets (CSP/offline-safe); self-declared actor shown in the header.
- [x] **`python-multipart`** added for form parsing; `RECENTLY_FIXED_DAYS` added to settings +
      `.env.example`.
- [x] **Tests (+19, offline gate green: 88 passed, 3 skipped)**: `test_dashboard_views`
      (bucket projection incl. removed flag & recently-fixed window, per-test record, run diff, and
      the three provenance tiers) + `test_web_dashboard` (HTTP routes, identity cookie, and PRG
      actions mutating state end-to-end). ruff lint + format clean. **SQLite-naive vs Postgres-aware**
      datetimes normalized in the views so window comparisons never mix tz-aware/naive.

### Open / deferred
- **HTMX progressive enhancement** — actions are plain PRG forms today (fully functional + offline-
  testable); inline HTMX swaps can be layered on without changing the handlers.
- **Flaky leaderboard / KB search** surfaces arrive with M4; the `flaky` column shows the M2 flag
  (still unpopulated until M4 computes oscillation).

## Milestone 4 — flakiness, knowledge base, email  ·  `[ ]`
Oscillation flakiness (§3); KB signatures + `pg_trgm` similarity (§4); regression-only email (§5).

## Milestone 5 — LLM hypothesis  ·  `[ ]`
Real provider behind `HypothesisProvider`, RAG over KB top-k.

---

## Notes / decisions discovered during build
- **Data-change correlation needs a lookback window**, not just the run's own start/finish — the
  #1702 run window (19:01–20:41 local) contained **zero** `V_TRACKING` rows; the day's changes were
  earlier (latest 15:46 local). `data_change_window()` defaults to a 12h lookback (provisional).
- **Clock confirmed empirically**: Oracle `SYSDATE` returns local time while `DBTIMEZONE=+00:00`
  → `CREDATIM` is naive `Europe/Luxembourg`. Tests pin summer(+2)/winter(+1)/DST.
- Offline DB tests use **in-memory SQLite**; the web test needs `StaticPool` + a shared connection
  so the request thread sees the same in-memory DB.
- **Lifecycle is computed vs the baseline, not vs the stored state** (M2). Deriving transitions from
  two fixed facts (baseline + current results) makes re-ingest idempotent and keeps episodes stable
  across re-runs (so M2 classifications and future M3 human input attached to an episode survive).
  Only **complete** runs advance lifecycle — an incomplete run's missing shard would otherwise read
  as a mass `REMOVED`. Both follow directly from PLAN §2 ("baseline = most recent complete run").
- **Both-signal classification is `UNKNOWN`, not a guess** (M2). Most runs carry a commit, so when a
  `ut_ref` change *also* falls in the window the cause is genuinely ambiguous; with no KB to rank yet
  (confidence deferred), we attach both candidate sets as evidence and let the human attribute.
