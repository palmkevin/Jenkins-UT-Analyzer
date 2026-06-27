# PROGRESS — Jenkins UT Analyzer

The **durable, committed checklist** of what's done and what's open. Source of truth for status;
update it as part of every change (it diffs in PRs). The phased plan lives in
[IMPLEMENTATION-PLAN.md](./IMPLEMENTATION-PLAN.md); this file tracks execution against it.

_Last updated: 2026-06-27_

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

## Milestone 1 — full schema + migrations  ·  `[ ]`
Alembic migrations for the full Information model; `CREATE EXTENSION pg_trgm`; indexing from scale.

## Milestone 2 — ingest pipeline + classification  ·  `[ ]`
Scheduled poll (APScheduler); complete-run baseline + diff; lifecycle state machine + episodes;
deterministic CODE/DATA/INFRA/UNKNOWN from time-windowed candidates.

## Milestone 3 — dashboard (FastAPI + HTMX)  ·  `[ ]`
Triage queue (§0), per-test record (§1) with acknowledge/confirm/edit, run summary (§2).

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
