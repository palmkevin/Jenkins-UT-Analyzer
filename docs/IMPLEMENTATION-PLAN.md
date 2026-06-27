# Jenkins UT Analyzer — Implementation Plan

> This is the "next document" promised by [`PLAN.md`](./PLAN.md) and gated by
> [`NEXT-PHASE-REQUIREMENTS.md`](./NEXT-PHASE-REQUIREMENTS.md). `PLAN.md` defines **what** the
> tool outputs; the requirements manifest defines the **inputs** that must be in hand. This
> document defines **how and in what order** it gets built — a phased plan, **thin vertical slice
> first**, so the load-bearing parsers + clock discipline are proven against real data before any
> breadth is built.

## Decisions locked (2026-06-27)

| Area | Decision |
|---|---|
| Deployment | Docker on the current VM; `docker-compose` (web / poller / db) |
| Postgres | container now, **external later** via `DATABASE_URL` (no code change) |
| Web UI | FastAPI + **HTMX + Jinja2** (no SPA build step) |
| Jenkins ingest | live API pull (anonymous read works; token on file) |
| v1 test scope | **devUTs (nose2) JUnit only**; unittest-log stages deferred post-v1 |
| Test identity | **test-level**, with track (`permanent` / `permanent_py39`) as an attribute |
| Data-change feed | Oracle **`V_TRACKING`** as-is (PFLOG / BFLOGLINK deferred) |
| `ut_ref` clock | `CREDATIM`/`UPDDATIM` are **local UTC+2** → normalize via `Europe/Luxembourg` |
| LLM | stubbed (no-op) behind a swappable interface in v1 |
| Identity | Phase 1 self-declared `actor` (default `test-user`); Keycloak = Phase 2 |

## Deployment model (decided)

The app runs **in Docker**, not directly on the host OS.

- **Runtime:** Docker engine **on the current VM** (containerized, not bare-metal). Jenkins and the
  Oracle `ut_ref` DB are reached over the network from inside the containers, so outbound access to
  both from the VM's Docker network is a prerequisite (see Execution gate).
- **Orchestration:** a single **`docker-compose.yml`**. Services:
  - `web` — the FastAPI app (dashboard + per-test/run views + actions).
  - `poller` — the scheduled Jenkins poll + ingest pipeline (same image as `web`, different
    entrypoint/command). Also exposes the on-demand back-fill command.
  - `db` — **PostgreSQL** as a container with a persistent named volume, `pg_trgm` enabled.
- **Postgres is "container now, external later":** the DB ships as a compose service for dev/test,
  but the app reaches it **only** through a configurable connection string (`DATABASE_URL`). Pointing
  production at an existing external PostgreSQL is then a config change with **no code change** —
  remove/disable the `db` service and set `DATABASE_URL`. This preserves `PLAN.md`'s "use the
  existing Postgres" intent while making the dev stack self-contained.
- **One image, two roles:** `web` and `poller` build from the same `Dockerfile`; the command selects
  the role. Keeps build/versioning trivial.
- **Config via environment** (12-factor), surfaced through a `.env` file consumed by compose and a
  typed settings object in code. No secrets baked into the image. A `.env.example` documents every
  key (Jenkins base URL + token, Oracle DSN/creds, `DATABASE_URL`, SMTP, tuning knobs, default
  `actor`).

```
┌─────────────────────────── docker-compose (on the VM) ───────────────────────────┐
│  web  (FastAPI/uvicorn)  ──┐                                                       │
│  poller (scheduler+ingest)─┤── DATABASE_URL ──▶  db (Postgres + pg_trgm, volume)   │
└────────────┬───────────────┴───────────────────────────────────────────────────┘
             │ outbound (network)
             ▼
   Jenkins API  +  Oracle ut_ref (read-only)
```

## Execution gate — inputs required before coding the load-bearing layer

Per the requirements manifest, the parser + clock-discipline layer cannot be coded against guesses.
Before Slice 0 starts, obtain and **validate** these (BLOCKING `A` / HIGH `B` from the manifest).
**Status (2026-06-27): A1–A4 and B1 are validated against the live systems** (see the two RESOLVED
sections below); B2/B3 carry sane defaults and don't block Slice 0.

| # | Input | Needed for | Validate by |
|---|-------|-----------|-------------|
| A1 | **Jenkins base URL + read-only API token/account**, scoped to the UT job, reachable from the VM's Docker network | all ingest | fetch the UT job + a build's metadata/artifacts from inside a container |
| A2 | **≥2 real merged UT reports** + their exact format (JUnit XML / custom XML / JSON / DB) — how suite/class/method, **shard**, status, duration, message, stack trace are carried; how shards merge | parser, data model | retrieve and identify the format explicitly *before* writing the parser |
| A3 | **SVN-update step output** format — revisions, authors, changed paths; new-revisions-only vs full WC state | code-change candidates | parse a real sample, confirm fields present |
| A4 | **Run metadata** — build #, build/console URLs, **overall + per-shard start/finish + their timezone/clock**, and how "all expected shards reported" is known | clock discipline, complete-run baseline | confirm timestamps + source clock are retrievable per shard |
| B1 | **Oracle `ut_ref` tracking schema** — table(s), change-timestamp column, author column, change→entity mapping; read-only DSN + driver (`oracledb`) | data-change candidates | connect read-only, read a few tracking rows |
| B2 | **PostgreSQL** — confirm `CREATE EXTENSION pg_trgm` permitted (trivially true for the `db` container; **re-confirm against the external server** before that cutover) | KB similarity (§4) | run `CREATE EXTENSION` in a migration |
| B3 | **Scale** — # tests, runs/day, history retention | indexing/partitioning | sizing note in Milestone 1 |

If any input is missing, malformed, or contradicts a design assumption, **stop and report** rather
than guess — this layer is silently corrupting when wrong.

### ✅ Jenkins side RESOLVED (A1–A4) — confirmed live against build #1702 (2026-06-27)

Job `Development/lsdevbuild-build-release-permanent` (declarative pipeline). Anonymous read works;
an API token is also available. Confirmed formats (full detail in the `jenkins-ingest-format`
memory):

- **Merged UT report = JUnit `TestResultAction`** at `/<n>/testReport/api/json` (no file artifact).
  Two suites, both `nose2-junit`; the **shard/track** (`permanent` vs `permanent_py39`) comes from
  `enclosingBlockNames`. The same test runs in **both tracks** → a result is keyed by
  `(run, test, track)`.
- **Per-test fields:** `className` + `name` (identity), `status` ∈
  {PASSED, FAILED, REGRESSION, FIXED, SKIPPED}, `duration`, `age`, `failedSince`, `errorDetails`,
  `errorStackTrace`. Test **file path** + line are inside the stack trace
  (`/opt/ls/lx/release/<track>/tests/dev/<pkg>/<mod>.py:<line>`). Stack traces also carry
  **`ZEPHYR TEST CASE INFO`** with owner initials (e.g. `(kam)`) → an ownership signal for §1.
  *(Jenkins' own REGRESSION/FIXED are vs its previous build; we still compute our own
  complete-run baseline.)*
- **SVN changes** via `/<n>/api/json?tree=changeSets[items[commitId,timestamp,author[fullName],msg,paths[editType,file]]]`
  + module revisions (`trunk/{web_modules,python_libraries,lx,tool}`). This is the candidate-code-changes source.
- **Per-shard timing & completeness** via `/<n>/wfapi/describe` (`stages[].{name,status,startTimeMillis,durationMillis}`);
  UT stages `devUTs: Execute - permanent[_py39]`. Expected shards = the 2 tracks (configurable).
- **Clock:** all Jenkins times are **epoch millis (UTC)** → Jenkins side is clock-safe. (The Oracle
  `ut_ref` clock is local UTC+2 — see the Oracle section.)

**Scope = devUTs (nose2) only for v1.** The pipeline reports tests two ways; v1 ingests only the
first:
1. **Structured JUnit (v1)** — the `devUTs` (nose2) via `testReport/api/json`. Clean, ~25k tests,
   both tracks. This is the entire v1 ingest surface.
2. **unittest console-log (DEFERRED, post-v1)** — `SMB Pricing/Transform`, `ITF Highlevel`, `LXS`,
   `Uniface deploy unit tests` run Python `unittest` inside **Shell Script** steps; results exist
   **only in the stage console log** (`execution/node/<id>/wfapi/log`, parseable unittest text).
   This needs a *second* parser, so it is **left aside for now** and added later behind the same
   ingest interface — no redesign required. *(A cleaner long-term option, if their pipeline can
   change: have these stages emit JUnit XML via a `junit` step, unifying ingest.)*

> **Track model (decided):** **test-level identity, track as an attribute.** One lifecycle per
> `suite/class/method`; the track(s) (`permanent` / `permanent_py39`) it failed in are recorded as
> an attribute on the result, not as separate identities.

### ✅ Oracle `ut_ref` side RESOLVED (B1) — connected & introspected live (2026-06-27)

Service `lsdb04pdb` @ `lsdb04:1521`, user `utestref01` (read-only), `oracledb` **thin mode** works.
DB timezone = UTC; **server OS clock = UTC+2** (Europe/Luxembourg). Full detail in the
`ut-ref-tracking` memory.

- **Data-change feed = the `V_TRACKING` view** — consolidated/normalized, **author already
  resolved**. Columns: `LXTABLECODE`/`PKLST` (changed entity + key), `LXTABLECODEREF`/`PKLSTREF`,
  `TYPE` (normalized **C/U/D**), `COMPONENTNAME`, `MODDATA` (NCLOB), `CREDATIM`/`UPDDATIM`,
  `USRIDCRE` + `USRCODE`, `SESSIONLOGID`. Actively populated (~2818 rows/last 7d). UNIONs 9 source
  trace tables (BFLOG, LORDERTR, RESLOG, ACIOLLOG, MICBLOG, ACINVORDTR, CONTAINERTR, PATLOG,
  ACINVTR).
- **Tracking-table audit shape** (the curated `tracking_tables/*.json` meta — BFLOG, BFLOGLINK,
  LORDERTR, PATLOG, PFLOG, RESLOG): common columns `CREDATIM`/`UPDDATIM`, `USRIDCRE`/`USRIDUPD`
  (FK→`USR`), `LXTABLECODE(REF)`/`PKLST(REF)`, `TYPE`, `MODDATA`, `SESSIONLOGID`, `COMPONENTNAME`.
  **`BFLOGLINK`** fans a `BFLOG` entry out to additional related entities (join on `BFLOGID`) — use
  it to capture the *complete* set of entities a logged change touched.
- **Author resolution:** `USRIDCRE → USR.USRID` (USR has `USRCODE`, `VALNAMELONG`); `V_TRACKING`
  already exposes `USRCODE`.
- **Feed source-of-truth (decided): `V_TRACKING` as-is** (its 9 sources). `PFLOG` and the
  `BFLOGLINK` fan-out are **deferred post-v1** — the curated `tracking_tables/*.json` stay as
  reference, and the feed sits behind an interface so they can be added later without redesign.
- **Timestamp timezone (decided): `CREDATIM`/`UPDDATIM` are local UTC+2** (naive `DATE`, server
  clock = Europe/Luxembourg). **Normalize via the named tz `Europe/Luxembourg` (DST-aware), not a
  fixed +2 offset**, then compare to Jenkins UTC. Still **verified empirically in Slice 0** against
  a known run (windowing stays provisional until proven).
- **Data-change correlation (v1):** convert the run's UTC window to a `CREDATIM` predicate, then
  `SELECT … FROM V_TRACKING WHERE CREDATIM BETWEEN :win_start AND :win_end ORDER BY CREDATIM` →
  candidate data changes for the run window (entity, C/U/D, author `USRCODE`, component), presented
  chronologically like the SVN candidates. No per-test relevance mapping in v1 (deferred).

**Oracle side fully specified — no remaining blockers for Slice 0.**

Remaining non-blocking inputs — defaulted, refined during the build, none gate Slice 0:
**SMTP** (Milestone 4 only), **production Postgres target + `pg_trgm` re-confirm** (B2, external
cutover only), **scale** (B3, tunes indexing; ~25k tests/run known), **tuning thresholds** (Q4/Q5),
**LLM provider** (stubbed), **Keycloak** (Phase 2).

## Technology stack

- **Language/runtime:** Python 3.12 (pinned in the image).
- **Web (decided):** FastAPI + uvicorn. Server-rendered views with **HTMX + Jinja2** (light JS, no
  SPA build step) — matches the manifest's "FastAPI + light JS" and keeps the container lean.
- **ORM/migrations:** SQLAlchemy 2.x + **Alembic**.
- **Postgres driver:** `psycopg` (v3). **Oracle driver:** `oracledb` (thin mode, no client install).
- **Scheduler:** APScheduler in the `poller` process (cron-style poll), plus a Typer/Click CLI
  entrypoint for the on-demand back-fill.
- **Email:** stdlib `smtplib` / `email`, behind a small sender interface.
- **LLM:** a `HypothesisProvider` interface with a **no-op stub** for v1 (manifest decision).
- **Testing:** pytest; golden-file parser tests against anonymized real artifacts.
- **Quality:** ruff + a formatter; type hints throughout.

## Project structure (target)

```
.
├── docker-compose.yml          # web + poller + db
├── Dockerfile                  # single image, role via command
├── .env.example                # every config key documented
├── alembic/                    # migrations
├── pyproject.toml
├── src/uta/
│   ├── config.py               # typed settings from env
│   ├── db.py                   # engine/session, DATABASE_URL
│   ├── models/                 # SQLAlchemy models (Information model §)
│   ├── ingest/
│   │   ├── jenkins.py          # API client (testReport, changeSets, wfapi)
│   │   ├── ut_report.py        # JUnit report parser    (A2)  ── golden-tested
│   │   ├── svn_update.py       # SVN changeSets parser  (A3)  ── golden-tested
│   │   ├── clock.py            # UTC normalization (Jenkins UTC, ut_ref Europe/Luxembourg) + tolerance (A4)
│   │   └── pipeline.py         # poll → parse → persist → diff → classify
│   ├── domain/
│   │   ├── lifecycle.py        # FAILING/FIXED/REMOVED state machine + episodes
│   │   ├── baseline.py         # most-recent-complete-run selection + diff
│   │   ├── classify.py         # deterministic CODE/DATA/INFRA/UNKNOWN
│   │   ├── flakiness.py        # oscillation/transition scoring
│   │   └── signature.py        # normalization mask set + hash (named, tested)
│   ├── kb/                     # signatures, pg_trgm recurrence/similarity, RAG hook
│   ├── refdb/oracle.py         # ut_ref read-only access — V_TRACKING window (B1)
│   ├── llm/provider.py         # HypothesisProvider interface + no-op stub
│   ├── web/                    # FastAPI app, routers, Jinja templates, HTMX
│   └── cli.py                  # back-fill / one-off commands
└── tests/
    ├── fixtures/               # anonymized real artifacts (golden files)
    └── ...
```

## Phased build

### Slice 0 — end-to-end spike (de-risk the load-bearing layer)
**Goal:** ingest **one real run** end-to-end and render it, proving the formats + clock model.
- Stand up the **docker-compose skeleton** (`web`, `poller`, `db`) and a one-table-ish minimal
  schema — enough to persist a run + its test results.
- Implement `jenkins.py` (fetch one build's report + SVN changeSets + per-shard timings via
  `wfapi`), minimal `ut_report.py` + `svn_update.py` parsers, and `clock.py` (UTC normalization,
  recorded source clock, tolerance margin).
- Implement minimal `refdb/oracle.py` to query `V_TRACKING` for the run window — **converting the
  `Europe/Luxembourg`-local `CREDATIM` to UTC** — and **empirically verify the timezone** by
  checking the returned changes line up with the run (this is the single riskiest clock assumption).
- Persist; render **one read-only view** listing that run's tests + the windowed candidate code
  **and** data changes.
- **Exit criteria:** `docker compose up`, back-fill build **#1702**, see correct data in the view;
  per-shard timestamps UTC-normalized with source clock retained; `V_TRACKING` window returns
  plausible data-change candidates with the tz conversion proven correct.

### Milestone 1 — full schema + migrations
- Alembic migrations for the complete **Information model** (`PLAN.md` §"Information model"): runs,
  test results, test identity + aliases, lifecycle (state + `FLAKY` + `reopen_count` +
  acknowledgement attribute), failure episodes, signals, classifications, users (`actor`), human
  input (cause/reason/triage/provenance tier + original AI value + validator), failure history,
  KB signatures (normalized text + hash + `pg_trgm` GIN index).
- `CREATE EXTENSION pg_trgm` in a migration; assert availability on startup.
- Indexing/partitioning sized from B3 (scale).

### Milestone 2 — ingest pipeline + classification
- Scheduled Jenkins poll (APScheduler) → parse → persist; idempotent re-ingest.
- **Complete-run baseline** selection (skip incomplete/aborted, configurable expected-shard count)
  + diff (regressions / newly-fixed / still-failing / flaky), recording which run was the baseline.
- Lifecycle state machine + episodes (reopen clears acknowledgement, increments `reopen_count`).
- Deterministic `CODE_CHANGE / DATA_CHANGE / INFRASTRUCTURE / UNKNOWN` from **time-windowed**
  candidates: SVN-update revisions in window; `ut_ref` changes in window **with tolerance margin**
  (B1). No confidence number yet (deferred per design).

### Milestone 3 — dashboard (FastAPI + HTMX)
- **Main triage queue (§0)** as the landing view: new-unacknowledged / still-failing / recently-fixed.
- **Per-test record (§1)** with **Acknowledge**, one-click **Confirm** on AI suggestions, editable
  **causing person** / **reason**, triage status — each stamped with the **Phase-1 self-declared
  `actor`** (default `test-user`, stored client-side, shown in header).
- **Run summary (§2)** with baseline diff and links into per-test records.

### Milestone 4 — flakiness, knowledge base, email
- **Oscillation-based flakiness (§3)**: transitions ÷ runs over the window, gaps = missing data
  (not flips); shard-correlation; **flaky leaderboard** view.
- **Knowledge base (§4)**: `signature.py` (the normalization mask set — named, **test-covered**),
  exact recurrence via signature hash, fuzzy "similar past cases" via `pg_trgm` (+ `tsvector`),
  provenance-weighted retrieval.
- **Regression-only email (§5)**: send **only** when a processed run introduces ≥1 new failing
  test; optional recovery notice toggle.

### Milestone 5 — LLM hypothesis
- Wire a real provider behind the already-stubbed `HypothesisProvider`, RAG over the KB's top-k
  similar past cases. Provider/key location confirmed then (manifest item 6).

### Post-v1 (per design, not in scope now)
Automatic **alias suggestion** (manual "merge identities" ships in v1), **relevance ranking +
confidence**, and **Keycloak/Kerberos auth** (Phase 2 — swaps the `actor` source, no data-model
change).

## Verification approach
- **Parsers:** golden-file unit tests against captured real artifacts (A2/A3). **Data sensitivity:**
  the LIMS data is medical — error text / `MODDATA` / stack traces may contain patient data, so
  golden fixtures are **anonymized/redacted before commit** (and never include raw `MODDATA`).
- **Ingest/windowing:** feed a known run + known `ut_ref`/SVN change, assert the candidate set and
  UTC/tolerance handling.
- **Signature:** dedicated tests that the mask set collapses same-bug variants and separates
  distinct bugs.
- **DB:** Alembic up/down against the `db` container; assert `pg_trgm` present.
- **End-to-end:** back-fill several historical runs via the CLI, open the dashboard, verify
  buckets / diff / flakiness against a hand-computed expectation.
- **Container:** `docker compose up` from a clean checkout reaches Jenkins + Oracle + Postgres with
  only `.env` supplied.

## Open tuning defaults (refine during build — `PLAN.md` Q4/Q5)
- Flaky transition threshold (flips ÷ runs over 30 days) — start conservative, tune on real data.
- `pg_trgm` similarity cutoff for "similar past cases."
- Normalization mask set + stack frames kept for signatures.

## Immediate next step
The **Execution gate** inputs (A1–A4, B1) are validated against the live systems — **Slice 0 is
unblocked.** First concrete action: scaffold the compose skeleton (`web`/`poller`/`db`) and ingest
build **#1702** end-to-end (JUnit report + SVN changeSets + per-shard timing + `V_TRACKING` window)
into one read-only view, proving the parsers and the UTC ↔ `Europe/Luxembourg` clock model.
