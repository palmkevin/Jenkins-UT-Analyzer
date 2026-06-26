# Next Phase — Information & Access Requirements (to write a solid Implementation Plan)

## Context

`docs/PLAN.md` is a finished **output-focused design**: it defines *what* the Jenkins UT
Analyzer tracks and presents (triage queue, per-test records, run summaries, flakiness,
knowledge base, email). It deliberately defers the **execution/implementation plan** to a
separate "next document" — that is the phase this document opens.

This document is **not** the implementation plan itself. It is the **requirements manifest**:
the ground truth — real data formats, real schemas, infra access — that must be in hand before
a phased implementation plan can be written as anything better than guesswork. `PLAN.md` itself
warns that the parsing and clock-discipline pieces are exactly where guessing silently corrupts
everything downstream, so those inputs gate the work.

> **Decisions made:**
> - **Formats sourced via _live Jenkins access_** (API token / read-only account) rather than
>   static sample files — the real merged UT reports, SVN-update output, and per-shard timings
>   are pulled directly. This *is* the answer to `PLAN.md` blocking open question #3.
> - **`ut_ref` schema/sample** will be provided.
> - **Web stack: FastAPI + light JS** (HTMX or minimal SPA).
> - **LLM: stubbed for v1** — ship the swappable interface with a no-op; deterministic
>   classification stands alone. Wire a real provider later.
> - **Build order: thin vertical slice first** — one real run ingested end-to-end into a
>   minimal view, to de-risk the parsers + clock discipline before broadening.

---

## Execution gate (read before starting implementation)

The inputs below are **provided at execution time, not now**. When the user asks to *execute*
this plan:

1. **First ask for the needed inputs** — start with the BLOCKING (A) and HIGH (B) items below.
   Do not begin coding parsers or the schema until they are supplied.
2. **Validate each input before proceeding** — confirm it is well-formed and sufficient:
   - Jenkins access actually reaches the UT job and can fetch a build's artifacts/metadata.
   - A real merged UT report and SVN-update output can be retrieved and the format matches an
     expected, parseable shape (identify it explicitly before writing the parser).
   - The `ut_ref` schema names a real change-timestamp column and author column.
   - PostgreSQL is reachable and `CREATE EXTENSION pg_trgm` is permitted.
3. **Only then proceed** to Slice 0 and the milestones. If an input is missing, malformed, or
   contradicts the design assumptions, stop and report back rather than guessing — the
   parsing/clock layer is load-bearing and a wrong assumption here is silently corrupting.

---

## A. BLOCKING — the plan cannot be concrete without these

These map to `PLAN.md` open question #3 ("first execution milestone") and the load-bearing
ingest/clock concerns. Everything downstream (data model, parsers, windowing) is shaped by
the real formats. **Resolution path: live Jenkins access** — obtain the real artifacts
directly rather than from hand-curated samples.

1. **Jenkins API access** — base URL + auth model (API token / read-only service account),
   reachable from the dev environment, scoped to the UT job.

2. From live access, capture for ≥2 real runs (and confirm the format before coding parsers):
   - **Merged UT execution report** — exact format (JUnit XML / custom XML / JSON / DB table);
     how a test row carries suite/class/method identity, the **shard** it ran in, status,
     duration, failure message, stack trace; how shards are merged (is shard identity kept?).
   - **SVN-update step output** — how revisions, authors, changed paths appear; whether it
     lists only *new* revisions for the run or full working-copy state.
   - **Run metadata** — build #, build/console URLs, **overall + per-shard start/finish
     timestamps and their timezone/clock** (clock discipline is load-bearing), and how
     "all expected shards reported" is determined (for the complete-run baseline rule).

## B. HIGH — needed to design the data model & correlation correctly

3. **Oracle `ut_ref` tracking-table schema** (`PLAN.md` open question #1).
   - Table name(s), the **change-timestamp** column, the **author** column.
   - How a change maps to a table/entity (so a future relevance step can relate it to a test).
   - Read-only connection details / driver (`oracledb`?), or a sample export of tracking rows.

4. **PostgreSQL target** (the app's own store).
   - Version, and whether `CREATE EXTENSION pg_trgm` is permitted (the §4 similarity design
     depends on it). Confirm full-text/`tsvector` is acceptable too.
   - Connection model (dedicated DB/schema for this app? migration tooling — Alembic?).

5. **Scale expectations** — number of tests, runs/day, and how long history is retained.
   Drives indexing, partitioning, and whether full-history queries need care.

## C. MEDIUM — shapes specific components, can be tuned during build

6. **LLM provider** — *decided: stubbed for v1.* Confirm only where a real key/endpoint would
   live later; v1 ships the swappable interface with a no-op implementation.

7. **Web stack** — *decided: FastAPI + light JS.* Confirm any house preference for the JS
   layer (HTMX vs. a minimal SPA framework) and a component/CSS baseline.

8. **Email/SMTP** — relay host, from-address, and recipient list for the "regression-only"
   alert (§5).

9. **Tuning starting points** (`PLAN.md` open questions #4, #5) — can default and refine:
   - Flaky transition threshold (flips ÷ runs over 30 days).
   - `pg_trgm` similarity cutoff for "similar past cases."
   - The normalization mask set + how many stack frames to keep for signatures.

## D. LOWER — Phase-2 / future, only need to confirm assumptions

10. **Keycloak/Kerberos details** — *not* needed for Phase 1 (self-declared `test-user`).
    Only confirm the `actor`-string design won't conflict with the eventual principal format.

11. **Deployment/runtime environment** — where the poller + web app run (container? VM?),
    Python version available, and whether outbound access to Jenkins/Oracle/LLM is permitted
    from that host.

---

## What gets produced once the inputs land

The actual "next document" — a phased implementation plan. Ordered as a **thin vertical slice
first**, so the load-bearing parsers + clock discipline are proven against real data before any
breadth is built:

- **Slice 0 — end-to-end spike (de-risk):** with live Jenkins access, ingest **one real run**:
  parse the merged UT report + SVN-update output (UTC-normalized, per-shard timing) → persist a
  minimal schema → render one read-only view. Proves the formats and the clock model early.
- **Milestone 1 — full schema + migrations** (Alembic) for the §"Information model": runs,
  results, identity/aliases, lifecycle, episodes, signals, classifications, users, KB sigs.
- **Milestone 2 — ingest pipeline:** scheduled Jenkins poll → parse → persist; complete-run
  baseline + diff; deterministic `CODE/DATA/INFRA/UNKNOWN` from time-windowed candidates
  (SVN window + `ut_ref` window with tolerance margin).
- **Milestone 3 — dashboard (FastAPI + light JS):** triage queue (§0), per-test record (§1)
  with Acknowledge / Confirm / causing-person / reason, run summary (§2). Phase-1 self-declared
  `actor` (default `test-user`).
- **Milestone 4 — flakiness/oscillation + leaderboard (§3); knowledge base signatures +
  `pg_trgm` recurrence/similarity (§4); regression-only email (§5).**
- **Milestone 5 — LLM hypothesis** wired in behind the (already-stubbed) swappable interface,
  RAG over the KB.
- Manual "merge identities" ships in v1; alias *suggestion*, relevance ranking/confidence, and
  Keycloak auth are post-v1 per the design.

## Verification approach (for the eventual implementation)

- Parsers: unit tests against the real (anonymized) artifacts (golden-file tests).
- Ingest/windowing: feed a known run + known `ut_ref`/SVN change and assert the candidate set.
- DB: migration up/down on the real PostgreSQL; assert `pg_trgm` available.
- End-to-end: back-fill a few historical runs via the on-demand command, open the dashboard,
  verify buckets/diff/flakiness match a hand-computed expectation.
