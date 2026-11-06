# Open work

This file **is** the tracker. There is no issue tracker for this repo: Bitbucket Cloud's is being
sunset (see [BITBUCKET-MIGRATION.md](BITBUCKET-MIGRATION.md) → *Where the tracker went*), and moving
to Jira was declined. Open work is tracked here, in-tree, and the record of *completed* work is the
git history plus the merged PR.

Conventions:

- **One heading = one shippable unit.** State the intent and an acceptance check.
- **Reference items by their slug**, e.g. `incident-aggregate`, and use that in the branch name
  (`feat/incident-aggregate-…`) and the PR title. There are no numbers to cite — deliberately, since
  a fresh numbering would collide with the ~110 commit messages already citing GitHub's `#N`.
- **`#N` in git history means the GitHub archive**, never anything here. See
  [history/github-issues.md](history/github-issues.md).
- **Delete the entry in the PR that finishes it** — the diff is the closing record.

---

## `incident-aggregate` — idea/spike: an "Incident" as the triage & documentation unit

`area: analysis` · carried over from **GH#194**, the only issue still open at the migration ·
full text: [history/github-issues.md](history/github-issues.md#issue-194)

**Status: idea / exploration, NOT a committed proposal.** Captured from a grilling session so it can
be resumed. Nothing is decided; the point is to preserve the idea and the open questions.

Cross-test signature grouping is surfaced only in the triage queue's **New** bucket. Once tests are
acknowledged they fall into **Still failing**, which carries no signature grouping — so after acking
a batch as "one outage", you can no longer see or act on that group. The narrow fix is a
signature-grouped view in Still-failing; the broader question is whether a first-class **Incident**
aggregate should become the documentation locus (carrying Cause Ticket, Assignee, Attribution and
Triage Status), with the per-test **Failure Episode** demoted to linked evidence.

Gating tension: `CONTEXT.md` already defines **Build Incident** as build-level and explicitly
orthogonal to Failure Episodes. Whether the new concept unifies with it or is separate is the fork
that decides everything else.

**Acceptance:** a `/domain-modeling` session that either names the concept and lands an ADR (it
reshapes the triage aggregate and is hard to reverse), or records the decision not to build it.

---

## `classify-candidate-blowup` — classification re-ranks every data change, per episode

`area: analysis` · observed on a cold-start ingest (empty store, build #2035)

`classify_build` loops over every newly-opened episode and, for each, calls `rank_candidates`, which
builds a `RankedDataChange` for **all** of the build's data-change candidates and then sorts the full
list (`src/uta/analyze/relevance.py:270-271`). The candidate set is identical for every episode of a
build, so both the scoring and the sort are redone per episode.

Measured on the first ingest into an empty store: 14,166 `data_change_candidates` (cold start has no
previous build, so the correlation window falls back to the 30-day `data_change_max_lookback_days`
cap) × 734 opened episodes ≈ 10.4M ranked objects and 734 sorts of a 14k list — **509 s of the
build's 1134 s**, one core pegged, all inside the ingest transaction so nothing is visible in the
dashboard until it finishes. Steady state is far smaller (few new episodes, window bounded by the
previous build's start), which is why this only bites on a cold start or after a wipe — but a bad
build day plus a wide window reproduces it in production.

Fix direction: the per-episode work that actually varies is the *score*, not the candidate list —
rank once per build and keep only what differs per episode, and/or stop materializing+sorting the
whole list when only the top match is consumed (`top_code` / `top_data`, `_top_evidence`).

**Acceptance:** cold-start ingest of a build with ~700 opened episodes and ~14k data candidates
spends seconds, not minutes, in `classify`; a unit test pins the candidate-ranking cost as a function
of episodes (i.e. it no longer scales with episodes × candidates), and the ranking output for a given
episode is unchanged.

---

## `ci-ownership` — decide between Bitbucket Pipelines and DevOps' Jenkins

`area: infra` · raised by the Bitbucket migration

`DEPLOYMENT-HANDOVER-uta-filled.md` states the internal target is Bitbucket + a **DevOps-owned
Jenkins** pipeline on RKE2. `bitbucket-pipelines.yml` is currently the pre-merge gate and works
(pipeline #1: 739 passed, 0 skipped, 210 s). If Jenkins takes over CI, Pipelines becomes a second CI
billing build minutes — the free tier is 50 min/month and this suite costs ~3.5 min per build, so
roughly 14 builds a month before it bites.

Pipelines now also carries the **GitHub mirror sync** (the `mirror main to the GitHub mirror` step on
`main`), so it is no longer only the test gate: dropping it silently strands the mirror, and with it
the public Render demo. Whatever replaces Pipelines has to take that step over — and the mirror
credential (a GitHub deploy key held as a Bitbucket repository SSH key) would have to be re-issued
wherever CI lands.

**Acceptance:** either Pipelines is kept deliberately as the pre-merge gate with Jenkins doing
post-merge deploy, or `bitbucket-pipelines.yml` is dropped and both the gate **and the mirror sync**
move to Jenkins. Whichever, update the *Testing contract* in `CLAUDE.md`.

---

<!-- Bug-hunt 2026-11: one entry per finding. Entries without **Needs owner input** are being fixed on the same branch; each fix commit deletes its entry. -->

## `data-change-lower-bound-uses-devuts-start` — data-change window lower bound starts at devUTs, not at the build

`area: ingest` · found by the 2026-11 bug hunt · **needs owner input**

`Build.started_at` is the devUTs Execute start (`timing.window[0]`), and the next build's data-change lower bound is the previous build's `started_at` (ADR-0004). The console-log suites (ITF/LXS/SMB/Uniface) run ~5 min earlier, so a data change made between N-1's ITF stage and its devUTs is never a candidate for N.

**Needs owner input:** changing what `started_at` means (or adding a separate build-start column) touches the build page, durations and ADR-0004 — decide which.

**Acceptance:** a data change made during N-1's console-log stages is a candidate for build N.

---

## `wfapi-log-truncated-hasmore` — stage logs truncated by wfapi (`hasMore`) are parsed as if complete

`area: ingest` · found by the 2026-11 bug hunt · **needs owner input**

`wfapi/log` returns `hasMore`/`consoleUrl` and caps the text; nothing in `src/` reads `hasMore`. Verbose stages could lose early `... ok` lines and the build is still complete → console-log tests flicker as removed/fixed.

**Needs owner input:** confirm against a real stage log whether `hasMore: true` occurs and how large the cap is; then fetch the full `/execution/node/<id>/log` when it does.

**Acceptance:** a stage log with `hasMore: true` is either fetched in full or marks the build incomplete.

---

## `execute-stage-failed-semantics` — does a FAILED devUTs Execute stage count as finished?

`area: ingest` · found by the 2026-11 bug hunt · **needs owner input**

Completeness treats a FAILED `devUTs: Execute` stage as finished. The #1702 fixture suggests FAILED there may mean a crash rather than test failures (results are published by separate Collect stages).

**Needs owner input:** real job semantics of FAILED on the Execute stage.

**Acceptance:** documented decision, and `complete` reflects it.

---

## `enrichment-source-outage-policy` — an Oracle or stage-log outage fails (and eventually quarantines) the whole build

`area: ingest` · found by the 2026-11 bug hunt · **needs owner input**

An `oracledb.DatabaseError` or a stage-log fetch error propagates out of `ingest_build`; three ticks later the build is quarantined and its (fine) devUTs results are lost. SVN blame and incident-log fetch are already best-effort.

**Needs owner input:** degrade (store devUTs results, mark incomplete/skip the source) vs. fail-and-retry.

**Acceptance:** documented policy, implemented in `ingest_build`.

---

## `not-executed-log-stage-blocks-analysis` — a when-skipped console-log stage makes every build incomplete

`area: ingest` · found by the 2026-11 bug hunt · **needs owner input**

Any selected console-log stage reported NOT_EXECUTED marks the build incomplete; declarative `when`-skipped stages report NOT_EXECUTED too. If a listed suite is conditionally skipped on every build, no build is ever complete and lifecycle/alerts stop silently.

**Needs owner input:** does the real job conditionally skip any `UNITTEST_SUITES` stage?

**Acceptance:** conditionally-skipped stages don't block completeness.

---

## `first-shell-script-step-only` — only the first `Shell Script` step of a log stage is parsed

`area: ingest` · found by the 2026-11 bug hunt · **needs owner input**

`wfapi.find_log_step_node` picks the first `Shell Script` step; a setup `sh` before the test `sh` would yield 0 cases while the build stays complete.

**Needs owner input:** do any real log stages run more than one `sh` step?

**Acceptance:** multi-step stages parse every step's output.

---

## `testreport-tree-filter` — testReport fetched without a `tree=` filter

`area: ingest` · found by the 2026-11 bug hunt · **needs owner input**

`test_report` pulls stdout/stderr for ~25k cases — a large payload that may carry patient text (not persisted, but transferred and held in memory). A `tree=suites[...]` filter would cut it.

**Needs owner input:** none for the idea, but the exact field list must be verified against a live Jenkins before shipping (it's a `live`-only check).

**Acceptance:** ingest requests only the fields the parser reads; a live test confirms parity.

---

## `svn-password-on-argv` — SVN password passed on the command line

`area: ingest` · found by the 2026-11 bug hunt · **needs owner input**

`refdb/svn.py` passes `--password` on argv, visible in `ps` on the host. Use `--password-from-stdin` (svn ≥ 1.10).

**Needs owner input:** confirm the svn client version in the deployed image supports it.

**Acceptance:** the password is never on argv.

---

## `llm-hypotheses-per-build-cap` — no cap on LLM hypotheses per build

`area: llm` · found by the 2026-11 bug hunt · **needs owner input**

`hypothesize_build` calls the model once per new episode, sequentially, inside the ingest transaction — a mass regression means hundreds of calls (cost + a long-held transaction).

**Needs owner input:** what cap, and should hypotheses move after commit?

**Acceptance:** decided cap implemented.

---

## `llm-raw-error-text-to-third-party` — raw error text (possibly patient data) is sent to the external LLM

`area: llm` · found by the 2026-11 bug hunt · **needs owner input**

Episode hypotheses send raw `error_details`/`error_stack_trace` (and commit messages) to Anthropic/OpenAI, unfenced; incidents send only masked text. The prompt docstring's "only already-redacted fields" holds for fixtures, not production. Also a prompt-injection channel.

**Needs owner input:** is sending raw LIMS error text to an external provider an accepted risk? If not: send the masked signature text + a masked exception line, and fence untrusted fields.

**Acceptance:** decision recorded (ADR) and the prompt matches it.

---

## `signature-mask-gaps` — signature masking misses `SMP_000123`-style ids and temp paths

`area: kb` · found by the 2026-11 bug hunt · **needs owner input**

`kb/signature.py` `\b\d+\b` can't mask digits after `_`/letters and there's no `/tmp/...` mask (the docstring claims there is) → the same bug gets distinct signatures and identifier-like values are persisted unmasked.

**Needs owner input:** fixing changes every affected signature hash — re-hash existing signatures via a backfill migration, or let old/new coexist?

**Acceptance:** masks fixed and the backfill decision applied.

---

## `kb-occurrence-count-per-track` — "seen N×" counts each track separately

`area: kb` · found by the 2026-11 bug hunt · **needs owner input**

`kb/store.py` counts result rows, so one failing build in two tracks shows "seen 2×" (pinned by `test_kb.py:44`).

**Needs owner input:** should occurrences count builds or (build, track) results?

**Acceptance:** decided semantics shown consistently.

---

## `confirm-clobbers-human-reason` — Confirm erases a human-entered reason

`area: dashboard` · found by the 2026-11 bug hunt

`web/actions.py` `confirm` / `confirm_incident` always overwrite both `causing_person` and `reason_text` from the AI, even when the AI value is `None`, and stamp AI_CONFIRMED on a null reason.

**Acceptance:** Confirm only overwrites (and stamps) fields the AI actually suggested.

---

## `save-restamps-provenance` — saving any field re-derives attribution provenance

`area: dashboard` · found by the 2026-11 bug hunt

The edit form pre-fills `causing_person`/`reason_text`, so every Save resubmits them and `set_attribution` re-derives provenance against the *current* AI suggestion — an assignee-only change turns AI_CONFIRMED into HUMAN_CORRECTED and restamps `validated_by`.

**Acceptance:** submitting unchanged values leaves provenance and validation stamps untouched.

---

## `triage-status-unvalidated` — triage status accepted as an arbitrary string

`area: dashboard` · found by the 2026-11 bug hunt

The attribute routes write `triage_status` unvalidated into a `String(16)` column: garbage is saved on SQLite, >16 chars is a 500 on Postgres.

**Acceptance:** invalid values are rejected with a flash error.

---

## `unbounded-form-input` — form inputs longer than their columns 500 on Postgres

`area: dashboard` · found by the 2026-11 bug hunt

Tickets are `String(32)`, assignee/person/actor `String(128)`; no `maxlength` and no server check. A pasted Jira URL as cause ticket → 500 on Postgres and a broken link on SQLite.

**Acceptance:** over-long input is rejected (or a ticket key extracted from a pasted URL) with a flash; inputs carry `maxlength`.

---

## `format-ts-mislabels-non-utc` — timestamps are labelled UTC without being converted

`area: dashboard` · found by the 2026-11 bug hunt

`format_ts`/`format_reltime` append " UTC" without `astimezone(UTC)`; on a Postgres with a non-UTC `TimeZone`, 12:00 UTC renders as "14:00:00 UTC".

**Acceptance:** aware datetimes are converted to UTC before formatting.

---

## `auth-actor-falls-back-to-cookie` — with auth on, a session without username falls back to the self-declared actor cookie

`area: dashboard` · found by the 2026-11 bug hunt

`auth_callback` stores a user even without `preferred_username`; `current_actor` then uses the `uta_actor` cookie and `/identity` stays routable.

**Acceptance:** login without a username is rejected; with auth on the cookie is never used.

---

## `auth-callback-error-500` — a stale/replayed OIDC callback is a raw 500

`area: dashboard` · found by the 2026-11 bug hunt

`authorize_access_token` errors (state mismatch, user cancelled) are uncaught in `web/auth.py`.

**Acceptance:** callback errors redirect to login instead of 500.

---

## `nan-tunable-accepted` — `nan` passes tunable bounds checks

`area: dashboard` · found by the 2026-11 bug hunt

`control/tunables.coerce`: `float("nan")` passes `min <= v <= max` (all NaN comparisons are False), silently disabling flaky/KB/overrun detection.

**Acceptance:** non-finite values are rejected.

---

## `bulk-ids-int-parse-500` — non-numeric ids in bulk forms are a 500

`area: dashboard` · found by the 2026-11 bug hunt

`int(v)` on form values in `/tests/bulk/acknowledge` and `/episodes/bulk/attribute`.

**Acceptance:** bad ids get a 400/flash, not a 500.

---

## `path-id-overflow-500` — huge path ids are a 500

`area: dashboard` · found by the 2026-11 bug hunt

`/tests/99999999999999999999` → OverflowError / out-of-range.

**Acceptance:** out-of-range ids 404.

---

## `incident-kb-ignores-tunables` — incident similar-cases ignore the KB tunables

`area: dashboard` · found by the 2026-11 bug hunt

`views._incident_dict` hardcodes `k=5, cutoff=0.3` instead of the effective `kb_top_k`/`pgtrgm_similarity_cutoff`.

**Acceptance:** control-panel overrides apply to incident pages too.

---

## `incident-tickets-not-linked` — incident tickets aren't rendered as Jira links

`area: dashboard` · found by the 2026-11 bug hunt

`_macros.incident_summary` takes `jira`/`fisheye` but never uses them; incident cause/resolution tickets appear only inside form inputs.

**Acceptance:** incident tickets render as Jira deep-links like episodes do.

---

## `attribute-by-signature-blank-claims-update` — signature-wide attribute reports updates when nothing changed

`area: dashboard` · found by the 2026-11 bug hunt

Unlike the bulk route (GH#150), the signature route counts every matched episode and creates empty `Attribution` rows on a blank submit.

**Acceptance:** a blank submit changes nothing and says so.

---

## `search-like-wildcards` — `_` and `%` in search act as wildcards

`area: dashboard` · found by the 2026-11 bug hunt

`/search` uses `ilike(f"%{q}%")` unescaped; `_` is in every `ut_…` name.

**Acceptance:** search matches `_`/`%` literally.

---

## `backfill-paths-drop-incidents` — back-fill paths skip Build Incidents, SVN blame and DB overrides

`area: infra` · found by the 2026-11 bug hunt

`uta backfill`, `uta bootstrap` and the control-panel job don't pass `ingest_build_incidents` (and two don't pass the blame client); the CLI ignores DB setting overrides.

**Acceptance:** all ingest entry points use the same effective settings and enrichers as the poller.

---

## `config-int-validation` — zero/negative poller settings break every tick

`area: infra` · found by the 2026-11 bug hunt

`POLL_RETRY_ATTEMPTS=0` raises `AssertionError("unreachable")` every tick; same lack of bounds on `QUARANTINE_AFTER_ATTEMPTS`, `POLL_INTERVAL_SECONDS`, `BACKFILL_DEPTH`.

**Acceptance:** these settings are validated `>= 1` at startup.

---

## `migration-drift-nullable-timestamps` — migrations leave model-NOT-NULL timestamps nullable

`area: infra` · found by the 2026-11 bug hunt

`created_at`/`updated_at` on `setting_overrides`, `ingest_jobs`, `poller_heartbeats`, `build_quarantines`, `build_incidents` are nullable in Postgres but NOT NULL in the models → autogenerate isn't empty.

**Acceptance:** a migration tightens them; autogenerate against the upgraded schema is empty.

---

## `health-stale-during-long-tick` — /health reports stale while a long tick is working

`area: infra` · found by the 2026-11 bug hunt

The heartbeat is stamped only at tick end; a catch-up tick over 5 min raises a false "poller is stale" alert.

**Acceptance:** liveness is stamped per ingested build.

---

## `post-commit-error-leaves-stale-attempt` — an error after a build commits leaves a phantom "retrying" row

`area: infra` · found by the 2026-11 bug hunt

`clear_failure` and `prune` run outside the per-build try in `poll_once`; a blip there records the tick as failed with nothing processed and leaves the attempt row.

**Acceptance:** post-commit bookkeeping failures are contained and logged.

---

## `worktree-rm-discards-work` — `make worktree-rm` force-deletes dirty worktrees and unmerged branches

`area: infra` · found by the 2026-11 bug hunt

`scripts/worktree.sh` uses `worktree remove --force` + `branch -D`.

**Acceptance:** refuses on a dirty worktree / unmerged branch unless `force=1`.

---

## `cold-start-poll-alerts-history` — a fresh deploy mails alerts for the whole back-fill window

`area: alert` · found by the 2026-11 bug hunt · **needs owner input**

On an empty store the poller ingests the last `BACKFILL_DEPTH` builds with live channels and the LLM; `uta bootstrap` deliberately doesn't. Up to 10 regression alerts + LLM spend on day one.

**Needs owner input:** desired cold-start alert behaviour (silent, or only the newest build?).

**Acceptance:** decided behaviour implemented.

---

## `inprogress-build-below-lastcompleted` — a still-running build below `lastCompletedBuild` is ingested partial and never revisited

`area: infra` · found by the 2026-11 bug hunt · **needs owner input**

Selection is `range(highest+1, lastCompletedBuild+1)` with no `building` check.

**Needs owner input:** can the job run concurrent builds?

**Acceptance:** running builds are not ingested (or are re-ingested on completion).

---

## `unbounded-catch-up-after-outage` — no per-tick build cap after a poller outage

`area: infra` · found by the 2026-11 bug hunt · **needs owner input**

After a long outage one tick ingests everything, with live alerts and LLM spend.

**Needs owner input:** cap per tick, and should old builds alert?

**Acceptance:** decided cap/alert policy implemented.

---

## `alembic-rename-leftover-constraint-names` — renamed tables keep `runs_*` constraint/sequence names

`area: infra` · found by the 2026-11 bug hunt

The `runs → builds` renames left `runs_pkey`, `test_results_run_id_fkey`, `runs_id_seq`, `run_shards_pkey`. A future migration that names them conventionally fails on Postgres only. Deferred: needs a real Postgres to verify the rename migration, which this cloud session didn't have.

**Acceptance:** a migration renames them; verified on Postgres.

---

## `demo-links-into-real-internal-systems` — public demo deep-links to real internal Jira/FishEye/Jenkins hosts

`area: demo` · found by the 2026-11 bug hunt · **needs owner input**

`render.yaml` sets no link env vars, so the demo renders `labsolution.atlassian.net/browse/LX-8842`, `fisheye.labsolution.lu/…` and the real Jenkins host for synthetic data.

**Needs owner input:** acceptable, or point them at `*.example.invalid`?

**Acceptance:** decision applied in the demo app or `render.yaml`.

---

## `demo-unittest-log-suites` — the demo never shows console-log suites

`area: demo` · found by the 2026-11 bug hunt · **needs owner input**

`seed.py` passes `ingest_unittest_logs=False`, so LXS/SMB/ITF/Uniface suites never appear in the public demo.

**Needs owner input:** worth seeding?

**Acceptance:** decision recorded / suites seeded.

---

## `public-repo-personal-email` — a personal email address sits in a public doc

`area: docs` · found by the 2026-11 bug hunt · **needs owner input**

`docs/BITBUCKET-MIGRATION.md` contains a real work email address.

**Needs owner input:** keep or redact?

**Acceptance:** decision applied.

---

## `mirror-pipeline-race` — two quick merges can make the mirror step fail non-fast-forward

`area: infra` · found by the 2026-11 bug hunt · **needs owner input**

The older `main` pipeline's `git push … HEAD:main` to the GitHub mirror fails when a newer one already pushed; spurious red `main` build, no data harm.

**Needs owner input:** acceptable, or switch the step to push only when HEAD is the branch tip?

**Acceptance:** decision applied.
