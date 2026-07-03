# Jenkins UT Analyzer

Ingests the nightly **devUTs** unit-test runs from Jenkins, tracks each test's failure **lifecycle**
across runs, correlates regressions with **code** (SVN) and **reference-data** (Oracle `ut_ref`)
changes, and surfaces it all in a triage dashboard — with flakiness detection, a failure **knowledge
base**, regression-only **email** alerts, and an optional **LLM root-cause hypothesis**.

> **Source of truth for behaviour and status** lives in [`docs/`](docs/) and [`CLAUDE.md`](CLAUDE.md):
> - [docs/PLAN.md](docs/PLAN.md) — *what* the tool outputs (the §0–§5 views).
> - [docs/IMPLEMENTATION-PLAN.md](docs/IMPLEMENTATION-PLAN.md) — *how / in what order* it was built.
> - **[GitHub Issues](https://github.com/palmkevin/Jenkins-UT-Analyzer/issues)** — status source of
>   truth (open todos + closed-issue/PR history). Milestones 1–5 are done; see `CLAUDE.md` → *Task
>   workflow* for the branch + `Closes #N` convention.
> - [CLAUDE.md](CLAUDE.md) — load-bearing invariants (clocks, test identity, medical-data handling)
>   and the testing contract.

## Stack
Python 3.12 · FastAPI + HTMX/Jinja · SQLAlchemy 2.x + Alembic · PostgreSQL (`psycopg`, with
`pg_trgm`) · Oracle read-only (`oracledb` thin) · APScheduler · `anthropic` / `openai` (optional) ·
ruff. Packaged under `src/uta/`.

## Quickstart (Docker)

```bash
cp .env.example .env          # then edit — at minimum nothing is required to boot the web UI
docker compose up             # starts db + web (http://localhost:8000) + poller
```

The single image runs in two roles selected by the compose `command`: **web** (dashboard) and
**poller** (scheduled ingest). Postgres is "container now, external later" — the app only ever
reaches it via `DATABASE_URL`, so production points at an external server with no code change
(disable the `db` service, set `DATABASE_URL`).

### Back-fill / run from the CLI

```bash
uta migrate                   # bring the schema to head (Alembic) + assert pg_trgm   (alias: init-db)
uta backfill 1702             # ingest one build…
uta backfill 1700 --to 1710   # …or a range
uta poll                      # run the scheduled poller (live path: email + LLM hypothesis)
```

Only `uta poll` (the live path) sends email and calls the LLM; **`uta backfill` does neither**, so
re-processing history never re-alerts or re-hypothesises.

## Develop in a devcontainer

For a reproducible dev environment, open the repo in a VS Code **devcontainer** ([`.devcontainer/`](.devcontainer/)).
It must run **on the VM** (via **Remote-SSH** → *Reopen in Container*) so it keeps the network route to
Jenkins/Oracle that live `uta poll` / `uta backfill` need.

```
Remote-SSH to the VM  →  Reopen in Container  →  pytest -m "not live"
```

The devcontainer reuses [`docker-compose.yml`](docker-compose.yml) plus
[`.devcontainer/docker-compose.dev.yml`](.devcontainer/docker-compose.dev.yml), which adds a `dev`
workspace service (Python 3.12) alongside a fresh `db`. It runs under an **isolated compose project**
(`jenkins-ut-analyzer-dev`), so it never touches a separately-running `docker compose up` deployment.
`postCreateCommand` runs `pip install -e '.[dev]'` (matching CI) and `uta migrate`. Only `db` auto-starts;
bring the full prod-like stack up from inside on demand:

```bash
docker compose -f docker-compose.yml -f .devcontainer/docker-compose.dev.yml up web poller
```

## Configuration

All configuration is **12-factor environment variables**, parsed into a typed settings object
([`src/uta/config.py`](src/uta/config.py)). Copy [`.env.example`](.env.example) to `.env` (gitignored)
and edit. **Every default below lets the app boot**; features turn on as you fill in their keys.

### Jenkins (test reports + SVN change sets)
| Variable | Default | Purpose |
|---|---|---|
| `JENKINS_BASE_URL` | `https://jenkins2.labsolution.lu` | Jenkins root URL. |
| `JENKINS_JOB_PATH` | `job/Development/job/lsdevbuild-build-release-permanent` | Path to the nightly job. |
| `JENKINS_USER` | *(empty)* | Optional — anonymous read works on the target job. |
| `JENKINS_API_TOKEN` | *(empty)* | Optional API token (paired with `JENKINS_USER`). |
| `EXPECTED_SHARDS` | `2` | Shards a run must report to count as **complete** (the 2 tracks). |

### Oracle `ut_ref` (reference-data change feed, read-only)
| Variable | Default | Purpose |
|---|---|---|
| `UT_REF_HOST` | `lsdb04` | Oracle host. |
| `UT_REF_PORT` | `1521` | Oracle port. |
| `UT_REF_SERVICE` | `lsdb04pdb` | Service name. |
| `UT_REF_USER` | `utestref01` | Read-only user. |
| `UT_REF_PASSWORD` | *(empty)* | **Enables the data-change feed when set.** Empty ⇒ data candidates are skipped. |
| `UT_REF_THICK` | `false` | Use `oracledb` thick mode (wallet/client); thin by default. |

### PostgreSQL (the app store)
| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://uta:uta@db:5432/uta` | The **only** way the app reaches Postgres. |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `uta` / `uta` / `uta` | **Compose-only** — initialise the `db` container (not read by the app). |

### Email (regression-only alert, §5)
| Variable | Default | Purpose |
|---|---|---|
| `SMTP_HOST` | *(empty)* | SMTP server. **Email is enabled only when host *and* recipients are set.** |
| `SMTP_PORT` | `25` | SMTP port. |
| `SMTP_FROM` | *(empty)* | From address. |
| `SMTP_RECIPIENTS` | *(empty)* | Comma-separated recipients; empty disables email. |
| `SMTP_USER` / `SMTP_PASSWORD` | *(empty)* | Reserved — not yet used by `SmtpEmailSender` (no auth wired today). |
| `EMAIL_RECOVERY_NOTICE` | `false` | Also send a "back-to-green" notice when a run recovers. |

### LLM hypothesis (§4 — optional)
| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | *(empty)* | `anthropic`, `openai`, or empty to **auto-pick** whichever key is set (Anthropic wins if both). |
| `ANTHROPIC_API_KEY` | *(empty)* | Anthropic **Developer Console** key — pay-as-you-go, **separate from any Claude.ai subscription**. |
| `ANTHROPIC_MODEL` | `claude-opus-4-8` | Claude model used when the provider is Anthropic. |
| `OPENAI_API_KEY` | *(empty)* | OpenAI **Platform** key (platform.openai.com) — pay-as-you-go, **separate from a ChatGPT subscription**. |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model used when the provider is OpenAI. |

With no key the deterministic predicted cause still works; `llm_hypothesis` simply stays blank. A
chosen provider with no key falls back to a no-op. Only the live `uta poll` path calls the model.

### App tuning
| Variable | Default | Purpose |
|---|---|---|
| `APP_DEFAULT_ACTOR` | `test-user` | Default acting user (phase-1 self-declared identity via the `uta_actor` cookie). |
| `FLAKY_TRANSITION_THRESHOLD` | `0.3` | Oscillation score (`transitions ÷ runs`) at/above which a test is flagged **flaky** (§3). |
| `FLAKY_WINDOW_DAYS` | `30` | Window for the flaky score and failure-history counts. |
| `PGTRGM_SIMILARITY_CUTOFF` | `0.3` | Minimum trigram similarity for KB "similar past cases" (§4). |
| `KB_TOP_K` | `5` | How many similar past cases to surface per failure. |
| `RECENTLY_FIXED_DAYS` | `7` | How long a fixed test stays in the §0 "recently fixed" bucket. |

### Ingest / correlation windows
| Variable | Default | Purpose |
|---|---|---|
| `DATA_CHANGE_LOOKBACK_HOURS` | `12` | How far **before** a run's start to look for `ut_ref` changes (they precede the nightly run). |
| `DATA_CHANGE_TOLERANCE_MINUTES` | `5` | Margin (B1) widening both ends of the window for Jenkins↔Oracle clock skew. |
| `POLL_INTERVAL_SECONDS` | `300` | Cadence of the `uta poll` scheduler. |

### Compose-only
| Variable | Default | Purpose |
|---|---|---|
| `WEB_PORT` | `8000` | Host port mapped to the web container. |

> ⚠️ **Clocks & medical data** are load-bearing invariants — Jenkins timestamps are epoch-millis UTC;
> Oracle `ut_ref` times are naive local (`Europe/Luxembourg`, DST-aware); raw `MODDATA` is never
> committed or sent to an LLM. See [CLAUDE.md](CLAUDE.md) before touching ingest.

## Dashboard surfaces
- `/` — §0 triage queue (New / Still-failing / Recently-fixed).
- `/tests/{id}` — §1 per-test record: lifecycle, episodes, latest error, candidate changes,
  flakiness & history, KB matches, and the predicted cause + LLM hypothesis.
- `/runs/{build}` — §2 run summary: totals, per-shard timing, baseline diff, results.
- `/flaky` — flaky leaderboard (§3). `/kb?q=` — knowledge-base search (§4).

## Testing
Two tiers (see the testing contract in [CLAUDE.md](CLAUDE.md)):

```bash
pip install -e ".[dev]"       # needs Python 3.12
pytest                         # the offline gate: pytest -m "not live", zero external systems
ruff check . && ruff format --check .
```

- **Offline suite is the merge gate** — no Jenkins / Oracle / real Postgres / LLM. Parsers run
  against committed golden fixtures; external clients sit behind interfaces exercised with fakes;
  DB-touching tests use in-memory SQLite (or an ephemeral Postgres in CI).
- **`live`-marked tests are local-only** (they hit the gated external systems / a real API key) and
  never run in CI: `pytest -m live`.

CI (`.github/workflows/ci.yml`): ruff → `pytest -m "not live"` → coverage, with a `services:` Postgres.
