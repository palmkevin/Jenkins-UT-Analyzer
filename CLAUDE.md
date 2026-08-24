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
- **[docs/OPEN-WORK.md](docs/OPEN-WORK.md)** — the **source of truth for status**. There is **no
  issue tracker**: Bitbucket Cloud's is being sunset and could not be enabled on this repo (see
  **Git hosting** below), so open work is tracked in-tree and the record of completed work is the
  git history plus the merged PR. Items are referenced by **slug**, never by number.
  The pre-migration GitHub tracker (issues #15–#194 and 110 PRs) is frozen in
  [docs/history/](docs/history/) — a bare `#N` anywhere in this repo means *that* numbering.

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
because `main` only advances through a Bitbucket PR whose Pipelines build passed, and the mirror is
fed by a Pipelines step that runs *after* that build on `main`, deploys stay test-gated by
construction. The free
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
- **The mirror syncs itself; you never push to it.** A `mirror main to the GitHub mirror` step in
  [`bitbucket-pipelines.yml`](bitbucket-pipelines.yml) runs after `test` on every `main` build and
  pushes `main` to GitHub from Atlassian's runners. It exists because `main` only advances through a
  **server-side PR merge** — no workstation is in the loop, so before this the mirror silently fell
  behind and the Render demo stopped updating. Fetches come from Bitbucket only. Never push to
  GitHub by hand — it is a receive-only mirror, and a manual push is how it diverges and starts
  rejecting the automated one.
- **Only `main` was carried over.** The ~110 merged feature branches were squash-merged, so their
  content is in `main`'s history; the branch *tips* remain on the GitHub mirror if ever needed.
- **There is no issue tracker.** Bitbucket Cloud's is being sunset and could not be enabled on this
  repo (`410 Gone` on `/issues`); moving to Jira was declined. Open work is tracked in-tree in
  [docs/OPEN-WORK.md](docs/OPEN-WORK.md) — see **Task workflow** above and
  [docs/BITBUCKET-MIGRATION.md](docs/BITBUCKET-MIGRATION.md) → *Where the tracker went*.
- **A bare `#N` always means the GitHub archive.** GitHub shared one sequence across issues *and*
  PRs (#193 is a PR, #194 an issue), and ~110 commit messages already cite it. Since no new
  numbering exists to collide with it, every `#N` in this repo resolves in
  [docs/history/](docs/history/). Write `GH#194` in new prose to keep that explicit. The only
  numbers minted after the migration are **Bitbucket PR IDs** (from 1, cited as `PR #1`).

## Task workflow (docs/OPEN-WORK.md + PR)
Open work lives in **[docs/OPEN-WORK.md](docs/OPEN-WORK.md)**, in-tree. There is **no issue tracker**
(see **Git hosting** below for why), so that file *is* the backlog and the merged PR *is* the record
of completed work. It's a hand-maintained status doc — keep it honest, it can't self-correct.
- **One heading = one shippable unit.** Imperative slug + title; body states intent and an
  acceptance check. Big efforts nest their children under one heading.
- **Items are referenced by slug, never by number** — `incident-aggregate`, not `#12`. Deliberate:
  any fresh numbering would collide with the ~110 commit messages already citing GitHub's `#N`.
- **`area:` stays the classifier**, as the entry's first line: `area: ingest` (ingest/analysis/
  dashboard/flakiness/kb/email/llm/infra/docs). The Conventional-Commit prefix carries what the old
  `type:*` label did, so it isn't restated in the entry.
- **Branch = Conventional prefix + slug:** `feat/incident-aggregate`, `fix/…`, `docs/…`, `chore/…`,
  `perf/…`, off `main`. Same slug in the PR title.
- **The PR that finishes an item deletes its entry** from OPEN-WORK.md — the diff is the closing
  record, and it makes the doc self-cleaning rather than a graveyard. Partial progress edits the
  entry instead. Merge once the Pipelines build is green (`main`'s branch restrictions require a
  passing build **and** an up-to-date branch — the equivalent of GitHub's `strict` required check).
  Admins can still push directly — the hotfix escape hatch survives the move.
- **Interaction verbs I honor directly:** "open an issue for …"/"add an item for …" → new entry in
  OPEN-WORK.md; "start `<slug>`" → branch off `main`; "update `<slug>` …" → edit the entry; "close
  `<slug>`" → PR that implements it **and** deletes the entry.
- **Public repo hygiene:** treat OPEN-WORK.md entries as world-readable (they are — it's in the
  repo) — no LIMS / `MODDATA` / patient strings and no secrets, same discipline as the fixtures.
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
- **Auth is flag-gated** (`AUTH_ENABLED`, default off): Keycloak OIDC (GH#17) is wired only when
  the flag is on, so local dev, the demo, and the offline gate run the Phase-1 self-declared-actor
  app with zero Keycloak access. `current_actor` stays the single identity choke point (and the
  seam for future role gating); auth-on tests seed a signed session cookie, never a live Keycloak.
- **Drive Bitbucket through the [`ls-atlassian:bitbucket`](https://bitbucket.org/labsolutionlu/ai-marketplace)
  skill, not hand-written `curl`.** Bitbucket has no `gh`-equivalent CLI, but the skill is the
  stand-in: it covers the whole PR lifecycle (create / list / diff / comment / approve / merge /
  decline) plus branches, files and commits. The devcontainer installs it —
  [`post-create.sh`](.devcontainer/post-create.sh) adds the `labsolution-plugins` marketplace and
  installs `ls-atlassian` at **user** scope. Invoke it by name (`/ls-atlassian:bitbucket`, or let the
  skill description match); if you shell out to its `scripts/bitbucket.py` directly, run it via
  `python3 …` — the file is **not** executable, so calling it by path fails with `Permission denied`.
  Pull requests are the only thing driven this way; there is no issue tracker (`/issues` answers
  `410 Gone`; see **Git hosting**).
- **Bitbucket credentials live in `.claude/settings.local.json`, not the shell.** The skill reads
  `BITBUCKET_WORKSPACE` + `BITBUCKET_EMAIL` + `BITBUCKET_API_TOKEN`, taking real env vars first and
  otherwise reading the settings file **directly** — nearest project `.claude/` walking up, then
  `~/.claude/`. They currently sit in **`~/.claude/settings.local.json`** (user scope, outside the
  repo), which is why `echo $BITBUCKET_API_TOKEN` in a shell prints nothing while the skill works
  fine. Editing the settings file takes effect without restarting the session.
  - Note the name: the skill wants **`BITBUCKET_API_TOKEN`**. Older notes here said
    `BITBUCKET_TOKEN`, which nothing reads.
  - Auth is HTTP Basic with an **Atlassian API token** (app passwords were retired); the token must
    be paired with the Atlassian *account email*, not the Bitbucket username. These are
    **developer-shell credentials, not app config** — deliberately *not* in `config.py`/`.env.example`
    (nothing in `src/uta/` reads them). Never inline a token in a command that gets committed or logged.
- **The skill has no build/pipeline-status command** — that gap is real and worth naming, because
  checking whether a PR's build passed (or why a `main` build failed) is routine here. For those, call
  `/2.0/repositories/…/pipelines/` directly, but reuse the skill's credential resolution rather than
  assuming env vars:

  ```python
  import sys; sys.path.insert(0, "<ls-atlassian>/lib")
  from atlassian_common import load_settings_env, require_env
  load_settings_env(("BITBUCKET_WORKSPACE", "BITBUCKET_EMAIL", "BITBUCKET_API_TOKEN"))
  auth = (require_env("BITBUCKET_EMAIL"), require_env("BITBUCKET_API_TOKEN"))
  ```

  When filtering pipelines by branch, note the two target shapes: **branch**-triggered runs carry it in
  `target.ref_name` and **PR**-triggered runs in `target.source`, so filtering on `ref_name` alone
  silently misses every PR build. Matching `target.commit.hash` sidesteps it.
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
