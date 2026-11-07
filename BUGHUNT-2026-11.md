# Bug hunt 2026-11 — handover for re-applying on Bitbucket

This file records a bug-hunt session that ran in a cloud session which could only reach the **GitHub
mirror**, not Bitbucket. All the work sits on the mirror branch **`ccr-ef99268a-xrgr9w`**
(`github.com/palmkevin/Jenkins-UT-Analyzer`). Below: how to bring it across, what was found and fixed,
what is still open, and what the code review flagged.

> **Delete this file once the work has landed on Bitbucket.** It is a handover note, not product
> documentation. The lasting record is `docs/OPEN-WORK.md` plus the commit history.

---

## 1. How to re-apply on Bitbucket

**Base commit:** the branch starts at `d13a331` ("Merged in chore/naming-alignment (pull request #7)").
On 2026-11-07 the mirror's `main` was still that same commit, so the branch should apply cleanly if
Bitbucket `main` hasn't moved.

**Option A — carry the branch over as-is (recommended).** This keeps 56 commits, one per fix, each with
its regression test, and each deleting its own `docs/OPEN-WORK.md` entry.

```bash
# inside the devcontainer, in the lx-ci-monitor clone (origin = Bitbucket)
git remote add github https://github.com/palmkevin/Jenkins-UT-Analyzer.git   # once
git fetch github ccr-ef99268a-xrgr9w
git switch -c fix/bughunt-2026-11 github/ccr-ef99268a-xrgr9w

# if Bitbucket main has moved past d13a331:
git fetch origin && git rebase origin/main     # conflicts most likely in docs/OPEN-WORK.md

# lint and test before pushing
ruff check . && ruff format --check .
pytest -m "not live" tests/integration
pytest -m "not live" tests/unit   # in batches if it OOMs (see CLAUDE.md)

git push -u origin fix/bughunt-2026-11
# then open the PR with /ls-atlassian:bitbucket — the Pipelines build will also run the
# 4 Postgres-only migration tests that were skipped in the cloud session
```

Afterwards, delete the branch on the GitHub mirror. It is a receive-only mirror, and this branch was
pushed there only because the session had no other remote. It doesn't touch `main`, so the mirror sync
is unaffected.

```bash
git push github --delete ccr-ef99268a-xrgr9w
```

**Option B — one PR per area.** The commits are grouped by area (see §3). If you'd rather review
smaller PRs, cherry-pick ranges onto separate branches off `main`. Commit `89b48fa` (adds the
OPEN-WORK entries) must come first, because every fix commit deletes an entry it added. The six
"review follow-up" commits (§4) depend on the earlier commit with the same slug.

**Option C — if the branch is ever gone.** Use §3 and §5 as the spec and re-implement. Each entry
names the file, the failure scenario and the acceptance check.

**Note on tooling.** Use the CI-pinned `ruff==0.15.20` from the project venv. The newer ruff 0.16
also formats Python blocks inside Markdown and flags the snippet in `CLAUDE.md`; CI doesn't.

---

## 2. How the session ran

1. **Search.** Five read-only agents each took a different area: ingest/refdb, analysis/KB/LLM, web
   layer, persistence/poller/control, and delivery/demo/docs drift. Most findings were reproduced with
   scratch scripts against the real code. Two findings came up twice (`testreport-404…` and
   `nan-tunable…`); after merging those, **65 findings** were left.
2. **Tickets.** One `docs/OPEN-WORK.md` entry per finding (commit `89b48fa`). There is no issue tracker.
3. **Fix.** Five fixer agents, one per area, each in its own git worktree, fixed **45** findings. Each
   fix is one commit with a regression test, and the commit deletes its entry.
4. **Docs.** `docs-overview-maintainer` updated OVERVIEW.html, help.html, README and CONTEXT.md
   (`f01dda0`). CLAUDE.md now describes the demo store as a temp-file SQLite, not in-memory (`4f561e0`).
5. **Review.** A code-review agent read the whole diff and ran Postgres-specific checks against a
   throwaway Postgres 16:
   - all 5 migration tests passed, including the new NOT-NULL migration and the single-head test;
   - the advisory lock was shown to serialise ingests;
   - the `ilike` escape was confirmed to work.

   It found nothing serious. Its six findings were fixed (§4), and two became new open entries.
6. **Final state.**
   - Lint and format are clean.
   - Unit tests: 905 passed, 4 skipped (Postgres-only, here).
   - Integration tests: 46 passed.

---

## 3. Fixed — 45 findings (commit → slug → what changed)

### Ingest / refdb
| Commit | Slug | Fix |
|---|---|---|
| 432f383 | `testreport-404-quarantines-failed-builds` | A testReport 404 (a build that died before devUTs) is now an empty report. The build is stored and its Build Incident recorded. Only a `build_meta` 404 counts as rotated out / quarantined. |
| 30e0aee | `complete-without-junit-tracks` | A build is complete only if the JUnit report contains every expected track (the old rule only checked wfapi stage status). |
| ff6cc0b, ee86fbb | `unittest-log-subtests-and-printing-tests` | The console-log parser handles tests that print before their outcome and subTest failures (`FAIL: … (i=1)`). A test still pending at end of log (crash or truncation) is FAILED, not SKIPPED. New fixtures from real py3.12 and py3.13 output. |
| e4726b0 | `unknown-junit-suite-fails-every-ingest` | Unknown-track suites are skipped with a warning instead of raising. Raising failed and quarantined every build. |
| ae094a3, 66845c8 | `oracle-call-timeout` | Oracle `call_timeout` is 300 s and the connect timeout 20 s (the driver default, pinned on purpose). Host, port and service are now passed as separate connect kwargs. |

### Analysis / flakiness / LLM
| Commit | Slug | Fix |
|---|---|---|
| 67c25c6 | `flaky-single-transition` | A test is flaky only with ≥2 transitions, so P,P,F and F,P are no longer flaky. This matches CONTEXT.md. |
| 3dcb294 | `flaky-leaderboard-tie-order` | Leaderboard ties are broken deterministically by `identity_id`. |
| 62b0a07 | `error-type-5xx-false-infra` | 502/503/504 counts as INFRA only in HTTP context, so `12.504 ` is no longer INFRA. |
| 0c9ffe2 | `error-type-timeout-in-path` | `File "…timeout…"` frame lines no longer type an error as TIMEOUT. |
| a007535 | `incident-reingest-double-extend` | Re-applying the same build to its open incident is a no-op. |
| 14fe81e | `incident-infra-masked-away` | The incident error type comes from the raw stage-log tail, so `ORA-03113` and HTTP 502 are recognised again. |
| b18c314 | `prompt-stack-head-truncation` | The LLM prompt keeps the tail of long stacks, where the exception line is. |
| 1aaff59 | `llm-call-timeout` | Anthropic and OpenAI clients use a 30 s timeout and 1 retry. |
| e282168 | `relevance-third-party-frames-match` | Only in-tree stack frames anchor data/code relevance. Stdlib and site-packages frames are ignored. |

### Dashboard / auth / control
| Commit | Slug | Fix |
|---|---|---|
| 67afbde, d694775 | `confirm-clobbers-human-reason` | Confirm writes only the fields the AI suggested. A human-entered reason is no longer erased. If the AI suggested nothing, no row is written and the flash says "Nothing to confirm". |
| cbcdd57 | `save-restamps-provenance` | Resubmitting an unchanged cause or reason keeps its provenance and `validated_by`. |
| adfc264 | `triage-status-unvalidated` | Triage status is validated against the enum ("Unknown triage status" flash). Before, it caused a 500 on Postgres when over 16 chars. |
| d45513f | `unbounded-form-input` | Server-side length checks use the column lengths, and inputs get `maxlength`. A pasted Jira URL is reduced to the ticket key. |
| 04b602f | `format-ts-mislabels-non-utc` | Timestamps are converted to UTC before the "UTC" label is added. |
| 3f5ab45 | `auth-actor-falls-back-to-cookie` | With `AUTH_ENABLED`, a login without `preferred_username` is rejected, the `uta_actor` cookie is never used, and `/identity` is not registered. |
| 10bf923 | `auth-callback-error-500` | OIDC callback errors redirect to `/login`. A second consecutive failure shows a 400 page, not a redirect loop. |
| c6bfed7 | `nan-tunable-accepted` | Tunables reject NaN and ±inf. |
| 75ea862 | `bulk-ids-int-parse-500` | Bad ids in bulk forms get a flash instead of a 500. |
| 8287fec | `path-id-overflow-500` | Path ids are bounded to 1..2³¹−1. Out-of-range or non-numeric ids return 404. Note: `/tests/abc` used to return 422. |
| 8e9574c | `incident-kb-ignores-tunables` | Incident "similar cases" use the effective `kb_top_k` and similarity cutoff. |
| eec3552 | `incident-tickets-not-linked` | Incident tickets and assignee are rendered as Jira deep links. The demo already seeds LX-9001/LX-9002. |
| c8ec9ee | `attribute-by-signature-blank-claims-update` | A blank signature-wide submit changes nothing and flashes "Nothing to apply". |
| 172b2e0 | `search-like-wildcards` | `/search` matches `_` and `%` literally. |

### Poller / persistence / infra
| Commit | Slug | Fix |
|---|---|---|
| 3637080 | `ondemand-ingest-jumps-high-water` | A control-panel ingest, `uta backfill` or `uta bootstrap` is refused if its range starts more than one above the high-water mark (`IngestGapError`). This prevents a permanent gap. |
| d98e861 | `compose-no-restart-policy` | db, web and poller have `restart: unless-stopped`. The startup tick, override load and heartbeat writes are guarded. |
| 6d020ba | `job-poller-no-mutual-exclusion` | `pg_advisory_xact_lock` is taken around the ingest transaction (no-op on SQLite). Verified on real Postgres. |
| 0fb2681 | `backfill-paths-drop-incidents` | All back-fill paths record Build Incidents and SVN blame, and the CLI honours DB overrides. |
| 5201199 | `config-int-validation` | `POLL_RETRY_ATTEMPTS`, `QUARANTINE_AFTER_ATTEMPTS`, `POLL_INTERVAL_SECONDS` and `BACKFILL_DEPTH` must be ≥ 1. |
| 8ad206f | `migration-drift-nullable-timestamps` | New Alembic revision **`e7f8a9b0c1d2`** makes `created_at`/`updated_at` NOT NULL on 5 tables, after backfilling NULLs. **This is a production schema migration and runs on deploy.** |
| 88fb8a8 | `health-stale-during-long-tick` | Liveness is stamped after each ingested build. "Last successful poll" now means last successful progress. |
| ced88b6, d58a8dc | `post-commit-error-leaves-stale-attempt` | A failure in post-commit bookkeeping is contained. Leftover attempt rows for already-stored builds are cleaned up on the next tick. |
| 2d9cfc0 | `worktree-rm-discards-work` | `make worktree-rm` refuses a dirty worktree or unmerged branch unless `force=1`. |
| ee5fe77 | `seed-demo-prints-db-password` | The DB password is masked in `uta seed-demo` output. |

### Alerts / demo / docs
| Commit | Slug | Fix |
|---|---|---|
| 2315991, e13ee4b | `teams-webhook-secret-logged` | Errors are cleaned of the URL, and the `httpx`/`httpcore` loggers are set to WARNING in both the CLI and the web app. httpx was logging the full `?sig=` URL at INFO. |
| 24ebccc, 611d130 | `teams-card-markdown-injection` | Card text is capped at 1000 chars. Only link syntax is neutralised (a zero-width space between `]` and `(`). Backslash escaping was dropped because Teams would likely show the backslashes. |
| 2a1ca51 | `email-null-sender` | Email is enabled only when `SMTP_FROM` is set, and messages carry `Date` and `Message-ID`. **Behaviour change:** a deployment without `SMTP_FROM` stops sending email (a warning is logged). |
| 2852f73 | `stale-health-alert-race` | The stale-poller alert latch is claimed atomically before dispatch. |
| 5dba492 | `demo-import-side-effect` | The demo app is built lazily, seeded once per process, and its temp store removed at exit. `uvicorn uta.demo.app:app` still works. |
| 5b2c81c | `env-example-defaults-diverge` | `.env.example` `JENKINS_JOB_PATH` now matches config. `WEB_PORT=8088` is kept and explained (devcontainer port forwarding). |
| 6679cf9 | `readme-config-table-missing-settings` | README has rows for all 17 missing settings, plus a test that every `config.py` field has a README row. |

**Doc commits:** `89b48fa` and `ec1f92d` (OPEN-WORK), `4f561e0` (CLAUDE.md demo wording), `f01dda0`
(docs-agent sync), `848f8ab` (help.html Confirm wording).

### Deploy-relevant behaviour changes (check before merging)
- **Migration `e7f8a9b0c1d2`** runs on deploy (NOT NULL timestamps).
- **`SMTP_FROM`** is now required for email. Make sure the deployed `.env` sets it.
- **Compose restart policy:** containers now come back after a reboot.
- **"Last successful poll"** semantics changed (see `health-stale-during-long-tick`).
- **Completeness is stricter.** A build missing a JUnit track is now incomplete, which pauses
  lifecycle analysis for that build. See open item `track-rename-stalls-silently`.
- **Path-id errors** return 404 instead of 422.
- **Auth on:** the self-declared actor form and cookie are gone entirely.

---

## 4. Code-review follow-ups (already applied on the branch)

| # | Finding | Resolution |
|---|---|---|
| 1 | httpx still logged the Teams `sig` token at INFO | `e13ee4b`: http client loggers set to WARNING |
| 2 | Backslash-escaped Markdown would show literally in Teams (`CODE\_CHANGE`) | `611d130`: neutralise only links |
| 3 | A failed `clear_failure` still left a phantom "failing" row | `d58a8dc`: self-healing sweep at tick start |
| 4 | Crashed or truncated test reported as SKIPPED | `ee86fbb`: settled as FAILED |
| 5 | 60 s Oracle call timeout might kill the 30-day lookback query; connect timeout was a no-op | `66845c8`: 300 s; connect timeout pinned explicitly |
| 6 | Confirm flash said "AI suggestion confirmed" with the human's value / created empty rows | `d694775` + `848f8ab` |
| 7 | Renamed tracks now stall analysis silently | new open entry `track-rename-stalls-silently` |
| 8 | Python 3.9 subTest output glues the next test onto the same line (pre-existing) | new open entry `unittest-log-py39-subtests-glued` |

Minor review notes, accepted as-is:
- `worktree.sh` refuses to remove a squash-merged branch whose remote was deleted. This is the safe
  direction, and `force=1` overrides it.
- `_msgid_domain` uses the whole sender as the domain when `SMTP_FROM` has no `@`.

**Still worth a manual check:** post one real Teams card after deploy to confirm the zero-width-space
link neutralising looks right.

---

## 5. Still open — 22 entries from the hunt in `docs/OPEN-WORK.md` (plus the 3 that existed before)

Full text, file pointers and acceptance checks are in `docs/OPEN-WORK.md` on the branch.

### Needs your decision (20)
| Slug | Area | The question |
|---|---|---|
| `llm-raw-error-text-to-third-party` | llm | **Most important.** Raw error text and stack traces, which may contain patient data, are sent unfenced to Anthropic/OpenAI. Is that an accepted risk? If not: send masked signature text plus a masked exception line, and fence untrusted fields. Deserves an ADR. |
| `demo-links-into-real-internal-systems` | infra | The public demo deep-links to `labsolution.atlassian.net`, `fisheye.labsolution.lu` and the real Jenkins host. Should these point to `*.example.invalid` instead? |
| `cold-start-poll-alerts-history` | email | A fresh deploy mails regression alerts and spends LLM calls for the whole `BACKFILL_DEPTH` window. Silent cold start, or only the newest build? |
| `track-rename-stalls-silently` | ingest | Which ops signal when JUnit tracks stop matching: alert on skipped suites with cases, or after N incomplete builds? |
| `wfapi-log-truncated-hasmore` | ingest | Does a real stage log return `hasMore: true`, and how big is the cap? If it happens, fetch the full `/execution/node/<id>/log`. |
| `execute-stage-failed-semantics` | ingest | Does FAILED on `devUTs: Execute` mean crashed or tests failed? This decides whether the build counts as finished. |
| `enrichment-source-outage-policy` | ingest | During an Oracle or stage-log outage: degrade (store devUTs results, mark incomplete) or fail and eventually quarantine? |
| `not-executed-log-stage-blocks-analysis` | ingest | Is any `UNITTEST_SUITES` stage `when`-skipped in the real job? If so, the build is never complete. |
| `first-shell-script-step-only` | ingest | Do any log stages run more than one `sh` step? |
| `testreport-tree-filter` | ingest | Add a `tree=` filter to testReport (large payload, may carry patient stdout). Needs a live check of the field list. |
| `svn-password-on-argv` | ingest | Does the deployed svn client support `--password-from-stdin` (≥1.10)? |
| `data-change-lower-bound-uses-devuts-start` | ingest | `Build.started_at` is the devUTs start, so data changes during the earlier console-log stages are missed. Redefine `started_at` or add a build-start column? This touches ADR-0004. |
| `inprogress-build-below-lastcompleted` | infra | Can the Jenkins job run concurrent builds? If so, a running build below `lastCompletedBuild` is ingested partial and never revisited. |
| `unbounded-catch-up-after-outage` | infra | After a long poller outage, cap builds per tick? Should old builds send alerts? |
| `llm-hypotheses-per-build-cap` | llm | Cap on LLM calls per build, and should hypotheses run after commit? |
| `signature-mask-gaps` | kb | Masking misses `SMP_000123`-style ids and `/tmp/…` paths. Fixing it changes signature hashes: backfill existing signatures, or let old and new coexist? |
| `kb-occurrence-count-per-track` | kb | Should "seen N×" count builds or (build, track) results? |
| `demo-unittest-log-suites` | infra | Should the demo seed console-log suites (LXS/SMB/ITF/Uniface)? |
| `public-repo-personal-email` | docs | A personal work email is in `docs/BITBUCKET-MIGRATION.md`. Keep or redact? |
| `mirror-pipeline-race` | infra | Two quick merges can make the older mirror push fail non-fast-forward (spurious red `main` build). Accept, or push only when HEAD is the branch tip? |

### No decision needed, just not done (2)
| Slug | Why not done |
|---|---|
| `alembic-rename-leftover-constraint-names` | `runs_pkey`, `test_results_run_id_fkey`, `runs_id_seq` and `run_shards_pkey` still carry the old names after the `runs → builds` renames. A rename migration needs verifying on real Postgres. |
| `unittest-log-py39-subtests-glued` | Found by the review; it's a pre-existing gap. Needs real Python 3.9 `-v` output as a fixture. |

### Already open before the hunt (unchanged)
`incident-aggregate`, `classify-candidate-blowup`, `ci-ownership`.

---

## 6. Environment notes from the session
- Run tests in batches (`tests/unit` split in 3, then `tests/integration`). The whole suite at once
  can OOM.
- `tests/unit/test_worktree_helper.py::test_url_for_db_swaps_only_the_database_name` fails unless the
  venv's `python` is first on `PATH`, because it shells out to a bare `python`. That's an environment
  issue, not a regression.
