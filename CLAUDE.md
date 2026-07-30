# CLAUDE.md — Jenkins UT Analyzer

Operating contract for this repo. [docs/OVERVIEW.html](docs/OVERVIEW.html) is the source-of-truth
concept/architecture doc; this file captures the invariants and conventions that are easy to get
wrong or re-derive.

## Read these first
- [CONTEXT.md](CONTEXT.md) — the **ubiquitous-language catalogue**: the single authority for what
  domain terms mean (with `_Avoid_` synonyms). A glossary and nothing else; when it and any other
  doc disagree on a *term*, CONTEXT.md wins. Maintained live during domain-modeling sessions and
  guarded as a doc surface (see **Keep the docs in sync**); decisions land in `docs/adr/`
  (per ADR-0001).
- [docs/OVERVIEW.html](docs/OVERVIEW.html) — the **authoritative concept/architecture overview**:
  purpose, the parts involved (Jenkins, Oracle `ut_ref`, the containers, PostgreSQL, LLM, email), the
  ingest → analysis → triage → learning → alert workflows with a schematic system map, and a
  **Reference** section (the persisted information model + the load-bearing invariants). Start here for
  "what is this and how does it fit together," and for what the tool outputs.
- **[Help page](src/uta/web/templates/help.html)** (served at `/help` in the running dashboard) —
  the **end-user-facing** counterpart: the daily triage workflow, what every status/badge means,
  what the LLM contributes versus the deterministic classifier, and how to act on (confirm/correct)
  an AI suggestion. Same freshness contract as OVERVIEW.html — see below.
- **[Bitbucket Issues](https://bitbucket.org/labsolutionlu/lx-ci-monitor/issues)** — the **source
  of truth for status** (open todos, in-progress work) and, once resolved, the record of completed
  changes. Every change is a branch + PR that says `Closes #N`; see **Task workflow** below.
  Issues #15–#194 predate the move off GitHub and are archived in
  [docs/history/](docs/history/) — a bare `#N` in the commit history refers to *that* numbering,
  **not** to a Bitbucket issue ID (see **Git hosting** below).

The original planning docs (`PLAN.md` / `IMPLEMENTATION-PLAN.md` / `NEXT-PHASE-REQUIREMENTS.md`) were
the pre-build requirements. The tool is built, so they've been retired — their durable content lives
in OVERVIEW.html's **Reference** section and in the invariants below, and the full history remains in
git.

## Live demo (public, synthetic)
A public, fully-synthetic **demo** is hosted on Render: **<https://jenkins-ut-analyzer-demo.onrender.com>**.
It runs the `uta.demo.app:app` entrypoint — an **ephemeral in-memory SQLite** store seeded on startup
from `src/uta/demo/` (fake Jenkins + `ut_ref` payloads fed through the *real* `ingest_build`
pipeline), with **no** connection to Jenkins/Oracle/FishEye/Jira/SMTP/LLM and **no** real data
(never LIMS/patient/`MODDATA`/real names — same discipline as the fixtures). Deploy is via
[`render.yaml`](render.yaml): Render auto-deploys `main` on every push. Since the migration to
Bitbucket, Render still watches the **GitHub mirror** — which is exactly why the mirror is kept — and
because `main` only advances through a Bitbucket PR whose Pipelines build passed, and `origin` pushes
to both hosts at once, deploys stay test-gated by construction. The free
instance sleeps after ~15 min idle (cold start ~30–50 s). Locally: `uta demo` (or
`uvicorn uta.demo.app:app`). The store is stateless — a restart rebuilds the same dataset.

**Keep the demo dataset showcasing every feature (consider it, every change).** The demo is the
public shop-window: any change that adds or alters a **user-visible signal or surface** (a new parsed
field, a new dashboard/record element, a new deep-link, a new bucket/state) should also **seed a
representative example** into `src/uta/demo/dataset.py` so the live demo actually exercises it —
including edge cases worth showing (e.g. the *plural* form of something that can occur once or many
times). The dataset is a deliberately small-but-complete story, so grow it thoughtfully rather than
piling on. Pure refactors/bug-fixes/perf/infra work that change no visible surface don't need it.
When in doubt, add the example — a feature the demo can't show is a feature reviewers can't see.

## Git hosting (Bitbucket Cloud, with a GitHub mirror)
The canonical remote is **Bitbucket Cloud**; the old GitHub repo is kept as a **read-only push
mirror** so the Render demo (which auto-deploys from GitHub) and the archived issue/PR history keep
working. See [docs/BITBUCKET-MIGRATION.md](docs/BITBUCKET-MIGRATION.md) for the runbook and the
one-time settings.
- **`origin` pushes to both hosts.** `git remote -v` shows two push URLs on `origin` (Bitbucket
  first, GitHub second), so a single `git push origin main` updates both. Fetches come from
  Bitbucket only. Never push to GitHub as the source of truth — it is a mirror.
- **Only `main` was carried over.** The ~110 merged feature branches were squash-merged, so their
  content is in `main`'s history; the branch *tips* remain on the GitHub mirror if ever needed.
- **`#N` is ambiguous by construction — mind which numbering you mean.** GitHub shared one sequence
  across issues *and* PRs (#193 is a PR, #194 an issue); Bitbucket numbers issues and PRs
  separately, both from 1. Every `#N` written **before** the migration means the GitHub sequence
  (archived in [docs/history/](docs/history/)); every `#N` written **after** means a Bitbucket
  issue. When citing a pre-migration item, write it as `GH#194` to remove the ambiguity.

## Task workflow (Bitbucket Issues + PR)
Work is tracked in **Bitbucket Issues**, driven conversationally via the Bitbucket Cloud REST API
(there is no `gh`-equivalent CLI — see Conventions for the `curl` recipe). There is **no status doc**
to hand-maintain; the issue *is* the unit of work and the resolved issue + merged PR *is* the record.
- **One issue = one shippable unit.** Imperative title; body states intent + an acceptance check.
  Big efforts get a `Tracking:` issue listing children.
- **Classification is lossier than GitHub's labels.** Bitbucket has a fixed `kind`
  (`bug`/`enhancement`/`proposal`/`task`) and no free-form labels, so the old `type:*` maps onto
  `kind` (`type:fix`→`bug`, `type:feat`/`type:perf`→`enhancement`, `type:chore`/`type:test`→`task`)
  and the **`area:*` tag goes in the body's first line** as `area: ingest` (ingest/analysis/
  dashboard/flakiness/kb/email/llm/infra/docs) so it stays greppable and searchable.
- **Branch = Conventional prefix + issue number:** `feat/42-…`, `fix/57-…`, `docs/…`, `chore/…`,
  `perf/…`, off `main`.
- **PR body must contain `Closes #N`** (or `Refs #N` for partial). Bitbucket does **not** auto-close
  issues from a PR body, so closing is a deliberate step: resolve the issue via the API (or the UI)
  after the merge. Merge once the Pipelines build is green (`main`'s branch restrictions require a
  passing build **and** an up-to-date branch — the equivalent of GitHub's `strict` required check).
  Admins can still push directly — the hotfix escape hatch survives the move.
- **Interaction verbs I honor directly:** "open an issue for …" → `POST …/issues`; "start #N" →
  branch off `main`; "update #N …" → `PUT …/issues/N` or a comment; "close #N" → PR that
  `Closes #N` **plus** resolving the issue.
- **Public repo hygiene:** treat issue titles/bodies as world-readable regardless of the Bitbucket
  repo's visibility — no LIMS / `MODDATA` / patient strings and no secrets, same discipline as the
  fixtures.
- Parallel **git worktrees** (in-container, single devcontainer): run multiple sessions/branches at
  once with `make worktree name=<x>` (teardown: `make worktree-rm name=<x>`; `scripts/worktree.sh`
  does the work). Each worktree lives under `.worktrees/<x>` (gitignored; inside the bind mount, so
  it persists on the host and shares the one `.git` — no mount change, no rebuild), gets its **own
  `.venv`** (the editable install pins a single source path, so worktrees can't share one) and its
  **own throwaway `uta_<x>` database** on the shared compose `db` server. `source
  .worktrees/<x>/.venv/bin/activate` activates the venv **and** exports that worktree's
  `DATABASE_URL` (needed because the devcontainer exports a container-wide `DATABASE_URL` that
  outranks the `.env` file in pydantic-settings). Per-worktree DBs let concurrent `pytest -m "not
  live"` runs — including the destructive migration test — proceed without contention; the
  in-memory-SQLite tests never contended anyway. Set a distinct `WEB_PORT` only when running two
  live `web`/`poller` stacks at once. A **container-per-task** model is deferred (it would also need
  the hardcoded `name: jenkins-ut-analyzer-dev` and the published ports in
  `.devcontainer/docker-compose.dev.yml` parametrized).

## Keep the docs in sync (required, every change)
Four hand-maintained doc surfaces describe the product but aren't generated from it, so they rot
silently, and **one agent owns all four**:
[docs/OVERVIEW.html](docs/OVERVIEW.html) (architecture, for contributors), the in-app
**[Help page](src/uta/web/templates/help.html)** at `/help` (the daily workflow, statuses, badges,
and the LLM feedback loop, for end users), the **[README.md](README.md) Configuration
reference + [.env.example](.env.example)** (the settings reference, for operators), and
**[CONTEXT.md](CONTEXT.md)** (the ubiquitous-language catalogue — the terminology authority, per
ADR-0001). You **must
invoke the [`docs-overview-maintainer`](.claude/agents/docs-overview-maintainer.md) agent** to check
whether any of the four needs updating (it edits the surface(s), including OVERVIEW.html's
system-map SVG, or reports "no update needed" per surface) after any change that could alter:
- **what parts the app involves, how they communicate, or its workflows** — a new/removed external
  system or integration, a container/service change, a change to the ingest/analysis/triage/
  learning/alert flow, or a shift in what the tool outputs (the triage queue, per-test record, build
  summary, flakiness, knowledge base, or email surfaces);
- **what an end user sees or does in the dashboard** — a new/renamed status or enum value, a new
  badge, a new/changed triage bucket or dashboard page, or a change to how the LLM hypothesis /
  Confirm / correct feedback loop works;
- **the settings surface** — a [`config.py`](src/uta/config.py) field or `.env.example` key added,
  removed, renamed, or re-gated, or a changed default/effect (every var needs both a README table
  row and a documented `.env.example` line);
- **the domain language** — a domain concept added, renamed, or re-defined (an entity, an enum's
  meaning, a canonical term or its `_Avoid_` synonyms): CONTEXT.md must still match the code.

Pure bug fixes, refactors, perf work, and test/CI/dependency changes that leave the depicted parts,
communications, workflows, user-visible surfaces **and** the settings surface unchanged do **not**
require it. When in doubt, invoke it — deciding materiality is the agent's job.

## Load-bearing invariants (silently corrupting if wrong)
- **Clocks.** Jenkins timestamps are **epoch millis, UTC** (`timestamp`, `startTimeMillis`). Oracle
  `ut_ref` `CREDATIM`/`UPDDATIM` are **naive local** wall-clock — server OS clock is UTC+2.
  Normalize them via the named tz **`Europe/Luxembourg`** (DST-aware), **never** a fixed `+2`.
  Verified empirically: `SYSDATE` returns local time while `DBTIMEZONE=+00:00`.
- **Test identity is test-level.** One lifecycle per `suite/class/method`. The **track**
  (`permanent` / `permanent_py39`) is an **attribute**, not a separate identity. A result is keyed by
  `(build, test, track)` — the same test runs in both tracks. Track comes from the JUnit suite's
  `enclosingBlockNames`.
- **Ingest scope.** The primary source is **devUTs (nose2) JUnit**, via `/<n>/testReport/api/json`
  (the authoritative ~25k-test surface). The unittest **console-log** stages (SMB Pricing/Transform,
  ITF Highlevel, LXS, Uniface) were the v1-deferred second source; they are now ingested **behind
  the same interface** by `ingest/unittest_log.py`, which parses each stage's
  `…/execution/node/<id>/wfapi/log` into the same per-`(test, track)` `TestResult`. Gated by
  `INGEST_UNITTEST_STAGES` (default on); `UNITTEST_SUITES` is the suite allowlist (a
  `"<suite> - <track>"` stage name → suite), keeping non-test `"… - permanent"` stages out.
- **Data-change feed = Oracle `V_TRACKING` view as-is** (author already resolved as `USRCODE`).
  PFLOG / BFLOGLINK fan-out are deferred. Correlation needs a **lookback window** (changes precede
  the build), not just the build's own start/finish window.
- **Medical data.** LIMS error text, stack traces, and especially `MODDATA` may contain patient
  data. Golden fixtures are **anonymized/redacted before commit**, and **raw `MODDATA` is never
  committed**. See `tests/fixtures/` — values redacted, structure (paths, line numbers, exception
  classes, ZEPHYR owner initials) preserved because the parser needs it.

## Testing contract (the merge gate)
Two tiers — offline (the gate) and `live` (local-only):
- **Offline suite is the default and the gate.** `pytest -m "not live"` must be green with **zero**
  access to Jenkins, Oracle, or a real Postgres. Parsers test against committed golden fixtures;
  external clients (Jenkins/Oracle/LLM/SMTP) sit behind interfaces and are exercised with fakes.
  DB-touching tests use an ephemeral Postgres (CI provides one as a Pipelines `services:` container).
- **`live`-marked tests are local-only**, never in CI (they hit the gated external systems).
- **Every step ships with its unit tests.** A milestone isn't done until its new logic is covered.
- CI ([`bitbucket-pipelines.yml`](bitbucket-pipelines.yml)): lint (ruff) → `pytest -m "not live"` →
  coverage; **required passing build on restricted `main`**. Two Pipelines-specific wrinkles the
  GitHub Actions version didn't have: there are **no service health-checks**, so
  [`scripts/wait_for_db.py`](scripts/wait_for_db.py) stands in for `pg_isready` (without it the
  destructive migration test would *skip* on a startup race and silently weaken the gate), and there
  is **no per-step `env:`**, so `DATABASE_URL` is exported inside a single `- |` shell block.
  A step is 4 GB by default; if pytest starts getting OOM-killed, uncomment `size: 2x`.
  `.github/workflows/ci.yml` is retained **only** for the read-only GitHub mirror — it is not the
  gate. The lint step runs **both** `ruff check .` **and**
  `ruff format --check .`, so run **both before every commit** — `ruff check .` alone passes while a
  formatting-only diff still fails CI (a green `ruff check` is *not* enough). `ruff format .` fixes
  it in place. Also run `pytest -m "not live"` **in batches** in the devcontainer — the whole suite
  at once OOM-kills (exit 137); that's the environment, not a failure.

## Reference: the build #1702 facts the fixtures came from
- Job `Development/lsdevbuild-build-release-permanent`, anonymous read works (token optional).
- Endpoints: report `/<n>/testReport/api/json`; SVN `/<n>/api/json?tree=changeSets[...]`; per-track
  timing `/<n>/wfapi/describe` (UT stages `devUTs: Execute - permanent[_py39]`).
- Oracle: service `lsdb04pdb` @ `lsdb04:1521`, user `utestref01` (read-only), `oracledb` thin mode.
- Expected tracks = 2 (`EXPECTED_TRACKS`, configurable).

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
- **Auth is flag-gated** (`AUTH_ENABLED`, default off): Keycloak OIDC (issue #17) is wired only when
  the flag is on, so local dev, the demo, and the offline gate run the Phase-1 self-declared-actor
  app with zero Keycloak access. `current_actor` stays the single identity choke point (and the
  seam for future role gating); auth-on tests seed a signed session cookie, never a live Keycloak.
- **Bitbucket has no `gh`-equivalent CLI** — drive it with the REST API over `curl`. Auth is HTTP
  Basic with an **Atlassian API token** (app passwords were retired), read from `BITBUCKET_EMAIL` +
  `BITBUCKET_TOKEN`. These are **developer-shell credentials, not app config** — they are deliberately
  *not* in `config.py`/`.env.example` (nothing in `src/uta/` reads them), so export them from your
  shell profile rather than `.env`. A repository/workspace access token works as
  `Authorization: Bearer` instead. Never inline a token in a command that gets committed or logged:

  ```bash
  # list open issues
  curl -sS -u "$BITBUCKET_EMAIL:$BITBUCKET_TOKEN" \
    "https://api.bitbucket.org/2.0/repositories/$BB_WS/$BB_REPO/issues?q=state=\"new\""
  # open a PR
  curl -sS -u "$BITBUCKET_EMAIL:$BITBUCKET_TOKEN" -X POST -H 'Content-Type: application/json' \
    "https://api.bitbucket.org/2.0/repositories/$BB_WS/$BB_REPO/pullrequests" \
    -d '{"title":"…","source":{"branch":{"name":"feat/42-…"}},"destination":{"branch":{"name":"main"}}}'
  ```
- **`gh` CLI is still available in the devcontainer** (the `github-cli` devcontainer feature, authed
  as `palmkevin` via a persisted `gh-config` volume) — but its scope is now **the mirror only**:
  re-exporting the archived issue/PR history and inspecting the old repo. Don't open PRs there.
- The **bare VM host is deployment-only** (it runs the deployed stack; it has no `gh`, no `curl`
  credentials, and no baked permission config) — see below.

## Development happens only in the devcontainer
All development runs **inside the devcontainer**, never on the bare VM host. The devcontainer image
bakes `bypassPermissions` into `/etc/claude-code/managed-settings.json` (the Linux *managed-settings*
path — highest precedence, and **not** shadowed by the workspace bind mount or the `~/.claude` named
volume, unlike those paths), so Claude Code runs **prompt-free** — **in the terminal CLI**, which
reads managed-settings directly. Consequences:
- **There is no `permissions.allow` list to maintain** in `.claude/settings.json` — it is
  intentionally empty. Don't re-add prefix rules; the managed mode already covers everything.
- The `deny` rules (`rm -rf /`, `git push --force`) and the built-in `rm -rf /` / `rm -rf ~`
  circuit-breakers **still apply** even under bypass.
- The mode is baked at **build** time, so a **Rebuild Container** is needed after changing it.
- **The VS Code extension needs a per-machine opt-in** — managed-settings alone does *not* make it
  prompt-free (only the terminal CLI is). The extension has its own gate: enable **"Allow dangerously
  skip permissions"** in VS Code Settings → Extensions → Claude Code, then either pick "Bypass
  permissions" in the mode indicator or set `"claudeCode.initialPermissionMode": "bypassPermissions"`.
  These are per-user VS Code settings, so the image can't bake them the way it bakes managed-settings;
  without them the extension keeps prompting (Bash + most non-edit tools) despite the managed mode.
- **Don't develop on the bare VM host**: it has no managed-settings file (so it would prompt) and no
  `gh`. It exists to run the deployed `web`/`poller`/`db` stack, not to author changes.
</content>
