# CLAUDE.md — Jenkins UT Analyzer

Operating contract for this repo. The **plan documents are the source of truth**; this file
captures only the invariants and conventions that are easy to get wrong or re-derive.

## Read these first
- [docs/PLAN.md](docs/PLAN.md) — **what** the tool outputs (information model, the §0–§5 views).
- [docs/IMPLEMENTATION-PLAN.md](docs/IMPLEMENTATION-PLAN.md) — **how / in what order** it gets built
  (phased: Slice 0 spike → Milestones 1–5). Start here for sequencing.
- [docs/NEXT-PHASE-REQUIREMENTS.md](docs/NEXT-PHASE-REQUIREMENTS.md) — the **inputs** the build needs.
- [docs/PROGRESS.md](docs/PROGRESS.md) — the **durable status checklist** (done / in-progress / open).
  **Update it as part of every change** — it is the source of truth for status and diffs in PRs.

The execution gate (Jenkins A1–A4, Oracle B1) is **validated against live systems** — Slice 0 is
unblocked. Live findings live in the plan's two "RESOLVED" sections.

## Load-bearing invariants (silently corrupting if wrong)
- **Clocks.** Jenkins timestamps are **epoch millis, UTC** (`timestamp`, `startTimeMillis`). Oracle
  `ut_ref` `CREDATIM`/`UPDDATIM` are **naive local** wall-clock — server OS clock is UTC+2.
  Normalize them via the named tz **`Europe/Luxembourg`** (DST-aware), **never** a fixed `+2`.
  Verified empirically: `SYSDATE` returns local time while `DBTIMEZONE=+00:00`.
- **Test identity is test-level.** One lifecycle per `suite/class/method`. The **track**
  (`permanent` / `permanent_py39`) is an **attribute**, not a separate identity. A result is keyed by
  `(run, test, track)` — the same test runs in both tracks. Track comes from the JUnit suite's
  `enclosingBlockNames`.
- **Ingest scope.** The primary source is **devUTs (nose2) JUnit**, via `/<n>/testReport/api/json`
  (the authoritative ~25k-test surface). The unittest **console-log** stages (SMB Pricing/Transform,
  ITF Highlevel, LXS, Uniface) were the v1-deferred second source; they are now ingested **behind
  the same interface** by `ingest/unittest_log.py`, which parses each stage's
  `…/execution/node/<id>/wfapi/log` into the same per-`(test, track)` `TestCaseResult`. Gated by
  `INGEST_UNITTEST_STAGES` (default on); `UNITTEST_SUITES` is the suite allowlist (a
  `"<suite> - <track>"` stage name → suite), keeping non-test `"… - permanent"` stages out.
- **Data-change feed = Oracle `V_TRACKING` view as-is** (author already resolved as `USRCODE`).
  PFLOG / BFLOGLINK fan-out are deferred. Correlation needs a **lookback window** (changes precede
  the nightly run), not just the run's own start/finish window.
- **Medical data.** LIMS error text, stack traces, and especially `MODDATA` may contain patient
  data. Golden fixtures are **anonymized/redacted before commit**, and **raw `MODDATA` is never
  committed**. See `tests/fixtures/` — values redacted, structure (paths, line numbers, exception
  classes, ZEPHYR owner initials) preserved because the parser needs it.

## Testing contract (the merge gate)
Two tiers — see the plan's "Hosting & testing strategy":
- **Offline suite is the default and the gate.** `pytest -m "not live"` must be green with **zero**
  access to Jenkins, Oracle, or a real Postgres. Parsers test against committed golden fixtures;
  external clients (Jenkins/Oracle/LLM/SMTP) sit behind interfaces and are exercised with fakes.
  DB-touching tests use an ephemeral Postgres (CI provides one via `services:`).
- **`live`-marked tests are local-only**, never in CI (they hit the gated external systems).
- **Every step ships with its unit tests.** A milestone isn't done until its new logic is covered.
- CI (`.github/workflows/ci.yml`): lint (ruff) → `pytest -m "not live"` → coverage; **required
  status on protected `main`**.

## Reference: the build #1702 facts the fixtures came from
- Job `Development/lsdevbuild-build-release-permanent`, anonymous read works (token optional).
- Endpoints: report `/<n>/testReport/api/json`; SVN `/<n>/api/json?tree=changeSets[...]`; per-shard
  timing `/<n>/wfapi/describe` (UT stages `devUTs: Execute - permanent[_py39]`).
- Oracle: service `lsdb04pdb` @ `lsdb04:1521`, user `utestref01` (read-only), `oracledb` thin mode.
- Expected shards = the 2 tracks (`EXPECTED_SHARDS`, configurable).

## Conventions
- Python **3.12** (Docker image pin; host also has `python3.12`). Package root `src/uta/`.
- Stack: FastAPI + HTMX/Jinja, SQLAlchemy 2.x + Alembic, `psycopg` (PG), `oracledb` (thin), ruff.
- Config via env (12-factor) → typed settings object; `.env` is gitignored, `.env.example` documents
  every key. Postgres reached only via `DATABASE_URL` ("container now, external later").
- Run: `docker compose up` (services `web` / `poller` / `db`); back-fill via the CLI.
- Secrets never committed. Don't add a `live` dependency to the default test path.
</content>
