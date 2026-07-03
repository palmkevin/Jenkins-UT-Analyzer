# CLAUDE.md — Jenkins UT Analyzer

Operating contract for this repo. The **plan documents are the source of truth**; this file
captures only the invariants and conventions that are easy to get wrong or re-derive.

## Read these first
- [docs/PLAN.md](docs/PLAN.md) — **what** the tool outputs (information model, the §0–§5 views).
- [docs/IMPLEMENTATION-PLAN.md](docs/IMPLEMENTATION-PLAN.md) — **how / in what order** it gets built
  (phased: Slice 0 spike → Milestones 1–5). Start here for sequencing.
- [docs/NEXT-PHASE-REQUIREMENTS.md](docs/NEXT-PHASE-REQUIREMENTS.md) — the **inputs** the build needs.
- **[GitHub Issues](https://github.com/palmkevin/Jenkins-UT-Analyzer/issues)** — the **source of
  truth for status** (open todos, in-progress work) and, once closed, the record of completed changes.
  Every change is a branch + PR that `Closes #N`; see **Task workflow** below. (The old
  `docs/PROGRESS.md` checklist is retired — its design-rationale notes moved to IMPLEMENTATION-PLAN.md.)
- [docs/OVERVIEW.html](docs/OVERVIEW.html) — the **hand-maintained concept/architecture overview**
  (purpose, the parts involved — Jenkins, Oracle `ut_ref`, the containers, PostgreSQL, LLM, email —
  and the ingest → analysis → triage → learning → alert workflows), with a schematic system map.
  The reader-facing "what is this and how does it fit together" page.

The execution gate (Jenkins A1–A4, Oracle B1) is **validated against live systems** — Slice 0 is
unblocked. Live findings live in the plan's two "RESOLVED" sections.

## Live demo (public, synthetic)
A public, fully-synthetic **demo** is hosted on Render: **<https://jenkins-ut-analyzer-demo.onrender.com>**.
It runs the `uta.demo.app:app` entrypoint — an **ephemeral in-memory SQLite** store seeded on startup
from `src/uta/demo/` (fake Jenkins + `ut_ref` payloads fed through the *real* `ingest_build`
pipeline), with **no** connection to Jenkins/Oracle/FishEye/Jira/SMTP/LLM and **no** real data
(never LIMS/patient/`MODDATA`/real names — same discipline as the fixtures). Deploy is via
[`render.yaml`](render.yaml): Render auto-deploys `main` on every push, and because `main` is a
protected branch requiring the CI `test` check, deploys are test-gated by construction. The free
instance sleeps after ~15 min idle (cold start ~30–50 s). Locally: `uta demo` (or
`uvicorn uta.demo.app:app`). The store is stateless — a restart rebuilds the same dataset.

## Task workflow (GitHub Issues + PR)
Work is tracked in **GitHub Issues**, driven conversationally via `gh` (available and authed in the
devcontainer — see Conventions). There is **no status doc** to hand-maintain; the issue *is* the unit
of work and the closed issue + merged PR *is* the record.
- **One issue = one shippable unit.** Imperative title; body states intent + an acceptance check.
  Big efforts get a `Tracking:` issue listing children. Label with a `type:*` (feat/fix/perf/chore/
  test) and an `area:*` (ingest/analysis/dashboard/flakiness/kb/email/llm/infra/docs).
- **Branch = Conventional prefix + issue number:** `feat/42-…`, `fix/57-…`, `docs/…`, `chore/…`,
  `perf/…`, off `main`.
- **PR body must contain `Closes #N`** (or `Refs #N` for partial) so the merge auto-closes the issue.
  Merge with `gh pr merge` once CI is green (`main` requires the CI `test` check; it's `strict`, so
  rebase/update the branch first). `enforce_admins` is off — a direct-push hotfix escape hatch exists.
- **Interaction verbs I honor directly:** "open an issue for …" → `gh issue create`; "start #N" →
  branch off `main`; "update #N …" → `gh issue edit`/comment; "close #N" → PR that `Closes #N`, or
  `gh issue close` for non-code items.
- **Public repo hygiene:** issue titles/bodies are world-readable — no LIMS / `MODDATA` / patient
  strings and no secrets, same discipline as the fixtures.
- Parallel **git worktrees** are deferred (single checkout for now); revisit when parallel work is
  wanted (each worktree needs its own `.venv` + copied `.env`).

## Keep the concept overview in sync (required, every change)
After any change that could alter **what parts the app involves, how they communicate, or its
workflows** — a new/removed external system or integration, a container/service change, a change to
the ingest/analysis/triage/learning/alert flow, or a shift in what the tool outputs (PLAN §0–§5) —
you **must invoke the [`docs-overview-maintainer`](.claude/agents/docs-overview-maintainer.md)
agent** to check whether [docs/OVERVIEW.html](docs/OVERVIEW.html) needs updating (it edits the page,
including its system-map SVG, or reports "no update needed"). Pure bug fixes, refactors, perf work,
and test/CI/dependency changes that leave the depicted parts, communications and workflows unchanged
do **not** require it. When in doubt, invoke it — deciding materiality is the agent's job.

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
- Run: `docker compose up` (services `web` / `poller` / `db`); back-fill via the CLI. On a **fresh
  (empty) store** the poller does **not** ingest from build #1 — `builds_to_ingest` floors the
  cold-start window to the last `BACKFILL_DEPTH` builds (default 10), oldest-first; `uta bootstrap
  [--depth N]` does the same on demand. Once the store is non-empty, selection is incremental above
  the high-water mark.
- Secrets never committed. Don't add a `live` dependency to the default test path.
- **`gh` CLI is available in the devcontainer** (the `github-cli` devcontainer feature, authed as
  `palmkevin` via a persisted `gh-config` volume) — use it for GitHub PR / branch-protection work
  (`gh pr create`, `gh api …/branches/main/protection`). Note the **bare VM host still has no `gh`**:
  if you're not in the devcontainer, fall back to pushing the branch and merging locally
  (`git merge --no-ff`) or opening the PR via the web URL git prints.

## Shell-command hygiene (avoid needless permission prompts)
The allow-list uses **prefix rules** (`Bash(docker *)`, `Bash(curl *)`, …). A prefix rule only
auto-approves a command Claude Code can prove is a **single, simple invocation**. Any shell-control
character makes the command "complex" and it will prompt **even though the prefix matches**:
- pipes `|`, chains `;` `&&` `||`, redirections (`2>&1`, `2>/dev/null`, `>`);
- subshell/glob characters `(` `)` `*` — **even inside quotes** (e.g. a `count(*)` in piped SQL).

So prefer **one bare command at a time**:
- Don't append `2>&1 | tail`/`| grep`/`| head` to trim output — the harness truncates already; run
  the bare command (`docker compose logs web`, `docker compose build web`).
- Avoid glob/paren metacharacters in arguments when a plain form exists (`count(1)` not `count(*)`).
- Chain only when every segment is independently allow-listed — and expect it may still prompt.
- Hand-editing `.claude/settings.json` mid-session may **not** hot-reload; add live rules via the
  prompt's "always allow" option or `/permissions`, not a manual file edit.
</content>
