# GitHub issue archive

Frozen record of the GitHub issue tracker as of the migration to Bitbucket Cloud.
Commit messages and PR bodies throughout this repo's history cite these numbers as
bare `#N`; **those refer to this file**, not to Bitbucket issue IDs (Bitbucket
renumbers from 1 and cannot reproduce GitHub's shared issue/PR sequence).

1 open, 83 closed, 84 total.

## Index

| # | State | Labels | Title |
| --- | --- | --- | --- |
| [15](#issue-15) | Closed | area:infra, documentation, type:chore | Adopt GitHub Issues + PR workflow |
| [16](#issue-16) | Closed | area:dashboard, type:feat | In-app control panel — runtime settings + on-demand ingest |
| [17](#issue-17) | Closed | area:infra, type:feat | Add Keycloak OIDC authentication (Phase-2 auth) |
| [19](#issue-19) | Closed | — | Enhance the UI in order to handle more efficiently long lists. |
| [20](#issue-20) | Closed | area:ingest, type:fix | fix(poller): tolerate 404 on a build detail endpoint instead of crashing |
| [23](#issue-23) | Closed | — | enhance ui with css framework  |
| [25](#issue-25) | Closed | — | create a dummy dataset and host the app online on GitHub on this dataset  |
| [31](#issue-31) | Closed | area:infra, type:chore | Support parallel in-container git worktrees for local dev |
| [32](#issue-32) | Closed | area:infra, type:chore | Run the devcontainer prompt-free; make development devcontainer-only |
| [34](#issue-34) | Closed | — | the flaky leaderboard is missing a total |
| [35](#issue-35) | Closed | — | enahnce timestamp display |
| [36](#issue-36) | Closed | — | add error information of failing tests in failure episodes |
| [37](#issue-37) | Closed | — | make a new page "Job runs" |
| [38](#issue-38) | Closed | area:infra, type:chore | Add VS Code run configs for rebuild/restart and debug loops |
| [44](#issue-44) | Closed | area:docs, type:chore | docs: note baked bypassPermissions is CLI-only; VS Code extension needs its own toggle |
| [46](#issue-46) | Closed | — | Add new concept: ZEPHYR TEST CASE INFO |
| [49](#issue-49) | Closed | area:analysis, type:feat | Populate suggested_contact from change-candidate authors |
| [50](#issue-50) | Closed | area:analysis, type:feat | Rank change candidates per failing test and feed change details to the LLM prompt |
| [51](#issue-51) | Closed | area:infra, type:feat | Harden the poller: retries, build quarantine, real /health, staleness alerting, job recovery |
| [52](#issue-52) | Closed | area:dashboard, type:perf | Add data retention/pruning and fix dashboard scale (pagination, N+1 queries) |
| [53](#issue-53) | Closed | area:dashboard, type:feat | Add trend visualization: run-health timeline and per-test flakiness sparklines |
| [54](#issue-54) | Closed | area:ingest, type:fix | Enable TLS verification for the Jenkins client by default |
| [55](#issue-55) | Closed | area:ingest, type:fix | Unittest log parser: stop defaulting unknown outcomes to PASSED |
| [63](#issue-63) | Closed | area:dashboard, type:feat | Make the triage queue a real work surface: filters, search, and bulk actions |
| [65](#issue-65) | Closed | area:ingest, type:perf | Parallelize the per-build Jenkins fetch path in ingest |
| [68](#issue-68) | Closed | area:dashboard, type:feat | Add a light/dark theme toggle to the dashboard |
| [72](#issue-72) | Closed | area:dashboard, type:feat | Show last ingested Jenkins run on Triage screen |
| [73](#issue-73) | Closed | area:analysis, type:feat | Close the learning loop: score AI-suggestion accuracy and populate classification confidence |
| [75](#issue-75) | Closed | area:dashboard, type:feat | Add flash feedback for every mutating action |
| [76](#issue-76) | Closed | area:dashboard, type:feat | Bulk-selection ergonomics on the triage queue (select-all, live count, disabled at zero) |
| [77](#issue-77) | Closed | area:dashboard, type:feat | Make triage filters instant and self-describing (auto-submit, filter chips, sortable columns) |
| [78](#issue-78) | Closed | area:dashboard, type:feat | Auto-refresh control-panel ingest jobs (vendored HTMX polling + progress bar) |
| [79](#issue-79) | Closed | area:dashboard, type:feat | Orientation polish: active nav state, triage-count navbar badge, relative timestamps |
| [80](#issue-80) | Closed | area:infra, type:fix | Poller schedules its interval job paused — never polls again after the startup tick |
| [81](#issue-81) | Closed | area:email, type:fix | Move the regression alert email out of the ingest transaction |
| [82](#issue-82) | Closed | area:analysis, type:fix | Guard apply_run against out-of-order re-ingest of historical builds |
| [83](#issue-83) | Closed | area:ingest, type:fix | Consult shard status in run completeness — an aborted run must not become a baseline |
| [84](#issue-84) | Closed | area:dashboard, type:fix | Triage rows drop the second failing track — track filter hides tests failing in both tracks |
| [85](#issue-85) | Closed | area:ingest, type:fix | Let a FAIL/ERROR traceback block override a garbled verbose status line in the unittest-log parser |
| [86](#issue-86) | Closed | area:analysis, type:fix | Anchor _INFRA_RE tokens on word boundaries — IOError is misclassified as infrastructure |
| [87](#issue-87) | Closed | area:ingest, type:fix | Make the Oracle local-time conversion DST-fold-safe |
| [88](#issue-88) | Closed | area:dashboard, type:fix | CSRF-protect the state-changing POST endpoints |
| [89](#issue-89) | Closed | area:dashboard, type:fix | Demo app must not expose the live control-panel mutation endpoints |
| [106](#issue-106) | Closed | area:dashboard, type:feat | Add signature-level bulk attribution |
| [108](#issue-108) | Closed | area:email, type:feat | Add dashboard deep links to alert emails |
| [112](#issue-112) | Closed | area:docs, type:feat | docs: add Auth/Keycloak config subsection + activation runbook to README; add a config-docs-maintainer check |
| [114](#issue-114) | Closed | area:ingest, type:feat | Redefine 'owner' as the test's main developer (SVN blame), not the ZEPHYR test-case author |
| [115](#issue-115) | Closed | area:ingest, type:fix | Make an unfinished unittest console-log stage mark the run incomplete |
| [116](#issue-116) | Closed | area:kb, type:fix | Fix stale FailureSignature aggregates when a re-ingest orphans a signature |
| [117](#issue-117) | Closed | area:analysis, type:fix | Close the open episode when a REMOVED test reappears passing |
| [118](#issue-118) | Closed | area:email, type:fix | Send the recovery notice only on the red-to-green transition, not on every green run |
| [119](#issue-119) | Closed | area:ingest, type:fix | Stop stringifying NULL Oracle V_TRACKING columns to the literal "None" |
| [120](#issue-120) | Closed | area:email, type:fix | Wire SMTP_USER/SMTP_PASSWORD into SmtpEmailSender (STARTTLS + login) |
| [121](#issue-121) | Closed | area:infra, type:fix | Make send_ops_alert best-effort so SMTP outages can't break /health or erase the poller tick record |
| [122](#issue-122) | Closed | area:infra, type:fix | Make demo control-state seeding idempotent so re-running `uta seed-demo` doesn't crash |
| [123](#issue-123) | Closed | area:dashboard, type:fix | Fix navbar test search returning no results when ui_row_limit is 0 |
| [124](#issue-124) | Closed | area:flakiness, type:fix | Require same-track consistency for the shard_correlated flakiness flag |
| [125](#issue-125) | Closed | area:infra, type:fix | Keep the demo's /health at 200 for the process's whole lifetime (seeded heartbeat goes stale) |
| [126](#issue-126) | Closed | area:kb, type:fix | Rank and label KB similar cases by the strongest of both provenance columns |
| [127](#issue-127) | Closed | area:infra, type:fix | Make /health report a never-succeeded poller stale instead of ok forever |
| [132](#issue-132) | Closed | area:dashboard, type:fix | Make the triage "Load all N Tests" expand link preserve active filters and sort |
| [143](#issue-143) | Closed | area:dashboard, type:feat | Keep your place: back-links on detail pages + episode anchors after actions |
| [144](#issue-144) | Closed | area:dashboard, type:fix | Make pass/fail status readable without color and label timestamps as UTC |
| [145](#issue-145) | Closed | area:dashboard, type:feat | Surface one-line error snippets in the triage queue and tame long traces on the test record |
| [150](#issue-150) | Closed | area:dashboard, type:fix | Make triage actions trustworthy: ack anchors, truthful bulk flash, disable-on-submit, live toast flashes |
| [151](#issue-151) | Closed | area:dashboard, type:fix | Finish URL-state coherence: keep ?expand= across filter/sort changes; cap run-diff lists with counts |
| [152](#issue-152) | Closed | area:dashboard, type:feat | Show the blast radius on "Ack all w/ signature (N)" before the click |
| [157](#issue-157) | Closed | area:dashboard, type:feat | Turn inert facts into pivots: linkify owner/suite/cause, clickable failed-count, cross-referring search empty states |
| [158](#issue-158) | Closed | area:dashboard, type:feat | Cluster same-signature rows in the New bucket (T5 follow-up to #152) |
| [159](#issue-159) | Closed | area:dashboard, type:feat | Render the classification evidence on the test record ("Why this prediction") |
| [161](#issue-161) | Closed | area:dashboard, type:feat | Add in-app end-user documentation (Help page) |
| [166](#issue-166) | Closed | area:infra, type:fix | Owner blame is a no-op in production: svn CLI missing from the Docker image |
| [168](#issue-168) | Closed | area:dashboard, type:feat | Show test Owner in the still-failing triage bucket and as a pivot link on the per-test record page |
| [171](#issue-171) | Closed | — | Add monitoring of pipeline fails in the app |
| [172](#issue-172) | Closed | area:analysis, area:dashboard, area:ingest, type:feat | Tracking: Manage long-running pipelines |
| [174](#issue-174) | Closed | area:docs, type:chore | Rename shard → track: one term for the parallel lanes |
| [177](#issue-177) | Closed | area:analysis, area:ingest, type:perf | Revisit retention volume estimate and data-change lookback window for per-commit build cadence |
| [178](#issue-178) | Closed | area:docs, type:chore | Accept "Jenkins run"/"pipeline run" as prose synonyms for Build in CONTEXT.md |
| [181](#issue-181) | Closed | area:email, type:feat | Notify build incidents / alerts to a Microsoft Teams channel |
| [184](#issue-184) | Closed | area:dashboard, area:ingest, type:feat | feat: visualize overrunning in-progress pipelines |
| [185](#issue-185) | Closed | area:analysis, type:feat | feat: flag & document abnormally slow successful builds |
| [189](#issue-189) | Closed | — | allow to search on failure |
| [191](#issue-191) | Closed | area:dashboard, type:chore | Remove the triage queue's Suite filter |
| [194](#issue-194) | Open | area:analysis, type:feat | Idea/spike: an "Incident" aggregate as the triage & documentation unit (grouping failing tests) |

## Issues

<a id="issue-15"></a>

### #15 — Adopt GitHub Issues + PR workflow

- **State:** Closed
- **Labels:** area:infra, documentation, type:chore
- **Opened:** 2026-07-03 · **Closed:** 2026-07-03
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/15

> # Proposal 4 — Task management via GitHub Issues (migrate off the docs checklist)
>
> > **Status:** planned, not started. Design/implementation plan for moving open todos and the
> > record of completed work out of the Markdown docs and into **GitHub Issues**, driven
> > conversationally through Claude Code with `gh`. See [PLAN.md](PLAN.md) (§0–§5 output model),
> > [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md) (phase narrative), and
> > [PROGRESS.md](PROGRESS.md) (the checklist this replaces).
>
> ## Context
>
> Today all task state lives in prose Markdown. [PROGRESS.md](PROGRESS.md) is the "durable, committed
> checklist" (`[x]/[~]/[ ]`) that "diffs in PRs"; [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md)
> carries the static phase sequence (Slice 0, Milestones 1–5, Post-v1); planned-but-unbuilt work sits
> in untracked hand-off docs (`PROPOSAL-3-CONTROL-PANEL.md`, `KEYCLOAK-INTEGRATION.md`). There is **no
> issue tracker** — the only `#NNNN` references are Jenkins build numbers, and the only real "tickets"
> are the in-app Jira feature and one DevOps provisioning request.
>
> This is friction for interactive, parallel development: open work isn't addressable (no stable IDs,
> no assignee/labels/state), a change and its record are coupled to one serially-edited file, and there
> is no clean unit to hand to a separate work session.
>
> **What changed and unblocks this:** the devcontainer is now the working environment and ships the
> **GitHub CLI** (`gh` v2.96.0, github-cli feature), authenticated as `palmkevin` (scopes incl. `repo`,
> `workflow`) with the token persisted across rebuilds via the `gh-config` named volume. `Bash(gh *)`
> is already in the `.claude/settings.json` allow-list. The repo (`palmkevin/Jenkins-UT-Analyzer`,
> public) has **Issues enabled and zero issues** — a clean slate. The old CLAUDE.md note "No `gh` CLI on
> this host" is therefore **stale** and is corrected by this proposal.
>
> Outcome: I create/update/close issues on your spoken instruction; each unit of work becomes a branch +
> PR that `Closes #N`; CI gates the merge; the closed issue + merged PR **become** the record of what was
> done, replacing the hand-maintained PROGRESS checklist.
>
> ### Decisions (confirmed with the user)
> 1. **Full migration.** GitHub Issues become the single source of truth for work **going forward** —
>    open todos *and*, as they close, the record of completed changes.
> 2. **Delete PROGRESS.md, don't freeze it.** It currently holds **zero open todos** (every item is
>    `[x]`; the last two open items — branch protection + first PR — were closed in commit `07eb9a4`),
>    so nothing needs extracting into a ticket first. Its one durable non-todo asset — the
>    `## Notes / decisions discovered during build` section (clock model, lifecycle-vs-baseline,
>    both-signal-UNKNOWN, flaky-as-oscillation, …) — is **relocated into
>    [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md)**; the rest is historical and lives in git
>    history + the design docs, so the file is then **deleted**.
> 3. **No historical backfill.** We do **not** recreate the completed Slice 0 / M1–M5 / Post-v1 work as
>    closed issues. Only current forward work is seeded (see below — all of it is *planned* work, since
>    nothing is open).
> 4. **Planned-work docs fold into tracking issues, then are deleted.** The untracked
>    `PROPOSAL-3-CONTROL-PANEL.md`, `KEYCLOAK-INTEGRATION.md`, and **this file** are never committed;
>    their content becomes the body of a `[tracking]` issue and the files are removed. (Optional
>    exception: a meaty, long-lived spec like Keycloak *may* instead be committed as a reference doc
>    that a short tracking issue links to — decide per doc.)
> 5. **Natural-language interaction, conventions in CLAUDE.md.** No custom slash-command files and no
>    `scripts/` helper. I run `gh`/`git` directly on your instruction ("open an issue for X", "start
>    #42", "close it"), following the conventions documented in CLAUDE.md.
> 6. **Worktrees deferred.** Establish the Issues + PR flow on the single checkout first. Parallel git
>    worktrees are documented as a **future step** (§ Deferred), not built now — the per-worktree
>    `.venv` (path-specific editable install) and `.env` copy, plus Docker/live-stack project-name
>    collisions, are real setup cost best paid once the ticket flow is proven.
> 7. **The two existing docs obligations survive the migration.** (a) `docs-overview-maintainer` must
>    still be invoked after any change that alters the app's parts/communications/workflows; (b)
>    design docs [PLAN.md](PLAN.md) and [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md) remain the
>    "what / how-in-what-order" source and are unchanged by this.
>
> > **Branch protection is already configured** (`gh api …/branches/main/protection`): required status
> > check = CI `test`, `strict: true`, `enforce_admins: false`, no required PR reviews. So the old
> > "make CI a required status" / "first PR" todos are **done**, not seed issues. Tightening (require
> > PRs, enforce on admins) is a later, optional step.
>
> ## The model going forward
>
> | Artifact | Before | After |
> |---|---|---|
> | Open todos / backlog | `[ ]`/`[~]` lines in PROGRESS.md | **GitHub Issues** (open) |
> | Record of completed work | `[x]` lines added in a PR diff | **Closed issues + merged PRs** |
> | "Diffs in PRs" review step | edit PROGRESS.md in the PR | PR body `Closes #N`; the issue *is* the item |
> | Status checklist file | PROGRESS.md (hand-maintained) | **deleted** (Notes section → IMPLEMENTATION-PLAN.md) |
> | Phase / milestone narrative | IMPLEMENTATION-PLAN.md | unchanged (gains the rescued Notes section) |
> | Output model vocabulary (§0–§5) | PLAN.md | unchanged |
> | Planned-but-unbuilt features | untracked `PROPOSAL-*`/hand-off docs | tracking **issue** (doc content moves in, file deleted) |
>
> The merge gate becomes: **branch → PR that `Closes #N` → CI green → merge (closing the issue).** The
> unit of work is the issue; the audit trail is the closed issue + its merged PR, not a checklist edit.
>
> ## Implementation
>
> Ordered so each step is independently useful and reversible.
>
> ### 1. Label taxonomy (`gh label create`)
> Map the repo's existing vocabulary onto labels. Keep the useful GitHub defaults (`bug`,
> `enhancement`, `documentation`, `duplicate`, `wontfix`); add **type** labels aligned to the
> Conventional-Commit prefixes already used in branch/commit names, and **area** labels aligned to the
> code packages / PLAN surfaces:
>
> - **type:** `type:feat`, `type:fix`, `type:perf`, `type:chore`, `type:test` (docs → reuse
>   `documentation`; bug → reuse `bug`).
> - **area:** `area:ingest`, `area:analysis`, `area:dashboard` (§0–§2), `area:flakiness` (§3),
>   `area:kb` (§4), `area:email`/`area:llm` (§5), `area:infra` (devcontainer/docker/CI),
>   `area:docs`.
> - **status:** `status:blocked` (WIP is signalled by an assignee + open state; add a
>   `status:in-progress` label only if you want it visible without opening the issue).
>
> ### 2. Milestones (`gh api …/milestones`)
> Milestones group issues toward a target (M1–M5 are already done, so these are forward-looking). Seed
> lazily — create one now for the immediate workstream and let feature milestones appear as needed:
>
> - **`Workflow & ops`** — this migration, branch protection, first PR.
> - (later, on demand) **`Control panel`** and **`Keycloak auth`** for those tracking issues.
>
> ### 3. Seed the forward work as tracking issues (`gh issue create`)
> There are **no open todos** to seed (all `[x]`; branch protection + first PR already done). The only
> forward work is the planned-but-unbuilt docs, each of which becomes a `[tracking]` issue whose **body
> is the doc's content** — then the file is deleted:
>
> 1. **Adopt the Issues + PR workflow** — body = this proposal's content; `area:infra`,
>    `documentation`. Closed when steps 1–7 land. Then delete `PROPOSAL-4-GITHUB-ISSUES-WORKFLOW.md`.
> 2. **[tracking] In-app Control Panel** — body = `PROPOSAL-3-CONTROL-PANEL.md`; `area:dashboard`,
>    `type:feat`. Then delete the file.
> 3. **[tracking] Keycloak OIDC integration** — body = `KEYCLOAK-INTEGRATION.md`; `area:infra`,
>    `type:feat`. Then delete the file — *or*, if you'd rather keep the live-verified hand-off spec as
>    an editable committed doc, commit it and have the issue link to it instead (per Decision 4).
>
> ### 4. Rescue the Notes section, then delete PROGRESS.md
> Move `## Notes / decisions discovered during build` into
> [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md) (a new "Notes / decisions" section), then `git rm`
> PROGRESS.md. No open todos remain in it, so nothing else needs preserving — the milestone "done"
> narrative is covered by git history and the design docs.
>
> ### 5. Rewrite the relevant CLAUDE.md sections
> - **Delete** the stale "No `gh` CLI on this host" bullet under *Conventions*; replace with: `gh` is
>   available and authenticated **inside the devcontainer** (persisted `gh-config` volume; one-time
>   `gh auth login` after a fresh volume). The bare VM host still lacks it — fall back to push + local
>   `git merge --no-ff` there.
> - **Remove** every reference to PROGRESS.md as the status source (in *Read these first*, the
>   "update it as part of every change" mandate, and the testing-contract "diffs in PRs" line): status
>   now lives in **GitHub Issues**; every change is a branch + PR that `Closes #N`. PROGRESS.md is
>   deleted, so the links to it must go too.
> - **Add** a short *"Task workflow (GitHub Issues)"* section documenting the conventions below so the
>   natural-language interaction is repeatable across sessions.
>
> ### 6. Conventions to document (the "how we talk about tickets" contract)
> - **Branch names** keep today's Conventional prefix + issue number: `feat/42-control-panel`,
>   `fix/57-poller-dedup`, `docs/…`, `chore/…`, `perf/…`.
> - **One issue = one shippable unit.** Title imperative ("Add …", "Fix …"); body states intent +
>   acceptance check. Larger efforts get a `[tracking]` issue that lists child issues.
> - **PR body must contain `Closes #N`** (or `Refs #N` for partial) so merge auto-closes the issue.
> - **Merge style:** PR merge on GitHub (`gh pr merge`) once branch protection is on; until then, the
>   repo's `git merge --no-ff` locally is still fine, but the PR/issue link is what records the work.
> - **Interaction verbs** I honor directly: *"open an issue for …"* → `gh issue create`; *"start
>   #N"* → branch off `main`; *"update #N …"* → `gh issue edit`/comment; *"close #N"* → open PR that
>   `Closes #N`, or `gh issue close` for non-code items.
>
> ### 7. (Optional, lightweight) A PR template
> `.github/pull_request_template.md` with a `Closes #` line + a one-line "docs-overview-maintainer
> considered? y/n" checkbox — cheap enforcement of the two obligations above. Issue templates are
> skipped (natural-language creation makes them low-value); add later if desired.
>
> ## Deferred — git worktrees (documented, not built)
>
> When parallel work is wanted, the intended shape (to build later): per-ticket worktree in a **sibling
> dir** outside `/workspaces/Jenkins-UT-Analyzer` (so Docker/tooling don't scan it), created off `main`
> for the issue's branch, with its **own `.venv`** (`pip install -e '.[dev]'` — the editable install is
> path-specific, so venvs can't be shared across worktrees) and a **copied `.env`** (gitignored, absent
> in a fresh worktree). Each worktree can host a separate Claude Code session. The **offline gate**
> (`pytest -m "not live"`, SQLite) runs fully per-worktree; **live/Docker** work stays single-at-a-time
> (compose project-name / port collisions). A thin `scripts/worktree.sh` would automate branch + `.env`
> copy + venv, but is out of scope until the single-checkout flow is proven.
>
> ## Tests / verification (end-to-end)
>
> This is a process + config change; "verification" is exercising the flow, not unit tests:
>
> 1. **`gh` reachable & authed:** `gh auth status` → logged in as `palmkevin`; `gh repo view --json
>    hasIssuesEnabled` → `true`.
> 2. **Labels/milestones created:** `gh label list` shows the `type:`/`area:` sets; `gh api
>    repos/palmkevin/Jenkins-UT-Analyzer/milestones` shows `Workflow & ops`.
> 3. **Seed issues exist:** `gh issue list` shows the 3 tracking issues with correct labels/milestone.
> 4. **Round-trip one real ticket:** pick a small change (e.g. the CLAUDE.md rewrite), branch
>    `docs/N-...`, open a PR whose body says `Closes #N`, watch CI go green, merge, and confirm the
>    issue **auto-closed**. This is the first exercise of the new flow end-to-end.
> 5. **Offline gate still green** on the branch: `pytest -m "not live"` (unchanged; nothing in this
>    proposal touches `src/`).
> 6. **Docs coherence:** CLAUDE.md no longer claims "no `gh`" and no longer points at PROGRESS.md;
>    PROGRESS.md is deleted; its Notes section now lives in IMPLEMENTATION-PLAN.md; the untracked plan
>    docs are gone (their content is in the tracking issues).
>
> ## Risks / notes
>
> - **Dual-source drift** is the main risk of a partial migration — avoided here by *freezing* (not
>   mirroring) PROGRESS.md: exactly one live source (Issues), one archive (PROGRESS.md).
> - **Public repo.** Issues, labels, and titles are world-readable. Keep the medical-data hygiene rule
>   from CLAUDE.md in issue text too — no LIMS/`MODDATA`/patient strings, no secrets, in titles or
>   bodies. (Reuse the fixtures' redaction discipline.)
> - **Branch protection is already on** (required status check `test`, `strict`, admins exempt, no
>   required PR). So there's nothing to sequence now. If you later *tighten* it (require PRs, enforce on
>   admins), do that **last** — once "require PR" is on you can't push straight to `main`, so the "we
>   use PRs now" convention in CLAUDE.md should already be in place to avoid locking yourself out.
> - **`gh` auth is per persisted home.** A brand-new `gh-config` volume needs one `gh auth login`; the
>   current one is already authed.
> - **This proposal is itself the first ticket.** Its content becomes the "Adopt Issues + PR workflow"
>   tracking issue, and this file is deleted (not committed) — the migration eats its own dog food.
>   Chicken-and-egg note: the very first issue/PR is created before the CLAUDE.md conventions land,
>   which is fine — the conventions are documented *by* this first PR.
> </content>
> </invoke>


<a id="issue-16"></a>

### #16 — In-app control panel — runtime settings + on-demand ingest

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-03 · **Closed:** 2026-07-04
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/16

> # In-app control panel
>
> ## Problem
>
> Today the monitor can only react per-test (acknowledge / confirm / attribute). Two operational levers live **outside** the running app:
>
> - **Tunable thresholds** (flaky threshold/window, similarity cutoff, KB top-k, recently-fixed days, expected shards, data-change lookback/tolerance, backfill depth) live in env and need an **edit + redeploy** to change. The monitor can't experiment with "what's the right flaky threshold?" in place.
> - **Ingest / re-analysis** is **CLI-only**, run by shelling into the container, with **no in-app visibility** into poller health (last poll, high-water mark, errors).
>
> ## Requirement
>
> Add an in-app control panel so the monitor can tune and operate the engine from the dashboard instead of redeploying:
>
> 1. **Tune thresholds at runtime.** Override any tunable threshold from the UI. Changes apply to dashboard views immediately and to the poller without a restart. Each override can be reverted to its env default.
> 2. **Trigger ingest / re-analysis on demand.** Kick off ingest or re-analysis of a build (or build range) from the UI, and see its status (running / done / error). Manual ingest must **not** send email or invoke the LLM (same semantics as `backfill` — a re-ingest must never re-mail historical regressions).
> 3. **See poller health.** Surface last poll time, high-water mark, and recent errors.
>
> ## Notes / constraints
>
> - **Access:** left open for now, consistent with the current honesty-system (no auth anywhere). Should be a single choke point to gate when auth lands.
> - Overrides are restricted to the whitelisted tunable thresholds — secrets and URLs must not be overridable.
>
> ## Acceptance check
>
> From the dashboard: change a threshold and see a view reflect it on next load without redeploying; trigger an ingest of a build and watch it go running → done with no email sent; view poller heartbeat and high-water mark.


<a id="issue-17"></a>

### #17 — Add Keycloak OIDC authentication (Phase-2 auth)

- **State:** Closed
- **Labels:** area:infra, type:feat
- **Opened:** 2026-07-03 · **Closed:** 2026-07-09
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/17

> ## Intent
>
> Replace the self-declared `uta_actor` cookie with a Keycloak-verified principal, behind a feature
> flag, so every write action (acknowledge / confirm / attribute) stamps a real authenticated
> username instead of a free-text label. No data-model change: `current_actor(request)` remains the
> single choke point, and the `actor` field keeps its existing shape — only where the string comes
> from changes.
>
> ## Decisions
>
> - **Authz = any realm user.** Anyone who can log in to the `labsolution` Keycloak realm may use the
>   whole tool; the verified username replaces the self-declared actor. Role/group gating is
>   out of scope for this issue — `current_actor` is left as the seam for it later.
> - **Runs behind Traefik/ingress.** TLS terminates at the proxy; the callback URL must be built from
>   the external URL, not the container's own scheme/host.
> - **Feature-flagged, off by default.** Local dev and the offline CI gate (`pytest -m "not live"`)
>   must keep working with zero Keycloak access; auth is enabled per-environment at deploy time.
> - **Confidential client, Authorization Code Flow + PKCE.** Standard OIDC client library only — no
>   hand-rolled token/ID-token validation.
> - **RP-initiated logout**, so logging out of this tool also ends the central Keycloak session
>   rather than just clearing a local cookie.
>
> ## Dependency on DevOps
>
> A confidential OIDC client must be provisioned in the `labsolution` Keycloak realm (standard
> auth-code flow, direct access grants off, no service account), with a registered redirect URI and
> post-logout URI per environment, and the client secret delivered via Vault. This is the only
> external dependency; the discovery endpoint and required scopes/claims (`openid profile email`,
> exposing `preferred_username`/`email`/`name`) have already been confirmed reachable and sufficient
> against the live realm — no custom claim mapper is needed.
>
> ## Acceptance
>
> - With the feature flag off (default), the app is behaviour-identical to today: no login is
>   required, the existing free-text actor cookie/form still works, and the offline test suite needs
>   no Keycloak access.
> - With the feature flag on:
>   - An unauthenticated request to a protected page is redirected to Keycloak login; after a
>     successful login the user lands back on the page they requested.
>   - `current_actor(request)` returns the authenticated user's Keycloak username, and that value is
>     what gets stamped on write actions (acknowledge / confirm / attribute).
>   - A health-check endpoint remains reachable without authentication.
>   - Logging out clears the local session **and** ends the Keycloak session (re-visiting the app
>     challenges for login again).
> - Offline suite (`pytest -m "not live"`) and lint stay green with the flag both off and on (auth-on
>   behaviour tested against a faked/seeded session, not a live Keycloak).
> - A `live`-marked test (never run in CI) confirms the real discovery endpoint is reachable.
> - [docs-overview-maintainer](.claude/agents/docs-overview-maintainer.md) has been invoked once this
>   is implemented, since adding Keycloak as an external system and a login/logout workflow is a
>   material change to [docs/OVERVIEW.html](docs/OVERVIEW.html).

**Comment — palmkevin, 2026-07-09:**

> Implemented and merged to `main` in PR #67 (commit 5a599d9) — that PR used `Refs #17`, so closing here after re-verifying the full acceptance list against current `main`:
>
> - **Flag off (default):** behaviour-identical Phase-1 app — no login, free-text `uta_actor` cookie/form intact, zero Keycloak access (`test_auth_off_serves_without_session`).
> - **Flag on:** unauthenticated GETs 303 to `/login` with the requested page stashed and restored after the callback (`test_unauthenticated_get_redirects_to_login`, `test_login_redirect_stashes_return_target`); non-GETs get an honest 401.
> - **`current_actor`** returns the Keycloak-verified `preferred_username`, and that's what write actions stamp — the Phase-1 cookie loses to the session (`test_actions_stamp_the_verified_username`).
> - **`/health`** (and `/static/`) stay reachable without a session.
> - **Logout** clears the local session *and* RP-initiated-logs-out of Keycloak via `end_session_endpoint` + `id_token_hint` (`test_logout_clears_session_and_hits_keycloak_end_session`).
> - **Offline gate:** `ruff` clean; `pytest -m "not live"` green — 514 passed, auth covered in both flag positions via a seeded signed session cookie (real `SessionMiddleware` format), no live Keycloak.
> - **Live test:** `tests/live/test_keycloak_live.py` asserts the realm's discovery document supports auth-code + PKCE, confidential-client token auth, `end_session_endpoint`, and the standard claims.
> - **OVERVIEW.html** was updated in the same PR (Keycloak as the fifth, flag-gated external system; system map + login/logout flow + config reference).
>
> Confidential client (auth-code + PKCE via Authlib), fail-closed middleware with an explicit allowlist, `SESSION_SECRET` required at startup when `AUTH_ENABLED=true`, and `--proxy-headers` so the callback URL is built from the external Traefik address. The only outstanding item is the DevOps-side client provisioning + Vault secret delivery, which is an external dependency, not code.
>
> ---
> _Generated by [Claude Code](https://claude.ai/code)_


<a id="issue-19"></a>

### #19 — Enhance the UI in order to handle more efficiently long lists.

- **State:** Closed
- **Labels:** —
- **Opened:** 2026-07-03 · **Closed:** 2026-07-03
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/19

> Ui is not responsive enough. I want to enhance this.
> The easiest solution might be to not render all the data in the UI. 
> My suggestion is to only render maximum 100 tests per chapter and display a hint that more are available. Here the user should have a possibility to click a link or button to load them all. The label should be "Load all {number} Tests".

**Comment — palmkevin, 2026-07-03:**

> @claude implement this


<a id="issue-20"></a>

### #20 — fix(poller): tolerate 404 on a build detail endpoint instead of crashing

- **State:** Closed
- **Labels:** area:ingest, type:fix
- **Opened:** 2026-07-03 · **Closed:** 2026-07-03
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/20

> ## Problem
> The poller crash-loops (exits 1, restarts, repeats) when Jenkins reports a `lastCompletedBuild` whose detail endpoint returns **404 Not Found**. Observed live: `lastCompletedBuild.number` pointed at a build whose `/<n>/api/json` had been rotated out of Jenkins build retention, so the pointer is valid but the detail resource is gone.
>
> ## Trace
> `build_meta()` in `src/uta/ingest/jenkins.py` calls `_get_json`, whose `resp.raise_for_status()` raises `HTTPStatusError`. Nothing between there and `run_scheduler` handles it:
>
> `run_scheduler` → `_tick` → `poll_once` (src/uta/poller.py) → `ingest_build` (src/uta/ingest/pipeline.py:168 `client.build_meta(build)`) → uncaught 404.
>
> Because the immediate startup `_tick()` runs before `scheduler.start()`, the exception kills the process before the scheduler is ever established — so it can never recover on the next interval.
>
> ## Desired behaviour
> A 404 on a single build's detail endpoint should be **skipped and logged (warning), not fatal**. The poll pass should continue to the next build, and the scheduler should keep running so subsequent ticks work. Consider: does a 404 on the *high-water/last-completed* build need any special handling (e.g. don't advance the mark on a build we couldn't fetch)?
>
> ## Acceptance check
> - With a Jenkins fake whose `build_meta` raises a 404 for one build number, `poll_once` skips that build, still processes the others, and does not propagate the error.
> - The poller process stays alive across the failing tick (no crash-loop).
> - Offline unit test covers the 404-skip path.


<a id="issue-23"></a>

### #23 — enhance ui with css framework 

- **State:** Closed
- **Labels:** —
- **Opened:** 2026-07-03 · **Closed:** 2026-07-03
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/23

> The UI is not very appealing.
> Bring in some css framework like tailwind or bootstrap.


<a id="issue-25"></a>

### #25 — create a dummy dataset and host the app online on GitHub on this dataset 

- **State:** Closed
- **Labels:** —
- **Opened:** 2026-07-03 · **Closed:** 2026-07-03
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/25

> The idea is to have an ephemeral in memory database with Dummy data.
> This data can be used to:
> - create Integration tests 
> - host this app online (no Jenkins/fisheye/ut_ref... Available here)
>
> The hosting goal: have the app running on main branch. Each PR should execute all unittests and deploy the latest of main to the online hosted app.


<a id="issue-31"></a>

### #31 — Support parallel in-container git worktrees for local dev

- **State:** Closed
- **Labels:** area:infra, type:chore
- **Opened:** 2026-07-04 · **Closed:** 2026-07-04
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/31

> ## Intent
>
> Enable multiple Claude Code / dev sessions to run **in parallel** on different branches, using **git worktrees inside a single devcontainer** (not a container per task).
>
> Rationale (from analysis of the current setup):
> - The default offline loop (`pytest -m "not live"`) runs almost entirely on **in-memory SQLite** (`tests/conftest.py`, `test_models`, `test_pipeline`, `test_web*`), so parallel test runs across worktrees **don't contend** on a database.
> - The only real collisions are (a) `tests/unit/test_migrations.py`, which **drops/recreates the `public` schema** on whatever `DATABASE_URL` points at, and (b) running the live `web`/`poller` stack (ports 8000/8088 + the `db` Postgres).
> - So a full container-per-task setup is unnecessary overhead. One container + worktrees is lighter and sufficient, provided each worktree gets an isolated venv and its own throwaway Postgres database.
>
> A container-per-task model is deferred; if ever needed it also requires parametrizing the hardcoded `name: jenkins-ut-analyzer-dev` in `.devcontainer/docker-compose.dev.yml` and the published ports.
>
> ## Scope
>
> - A helper (e.g. `make worktree name=<x>`) that, in one shot:
>   - `git worktree add .worktrees/<x> -b <branch> origin/main`
>   - creates a per-worktree venv and `pip install -e '.[dev]'` (the editable install pins a single source path, so worktrees can't share one)
>   - copies `.env` into the worktree with `DATABASE_URL` rewritten to a per-worktree throwaway DB (e.g. `uta_<x>` on the same `db` server)
>   - `createdb uta_<x>` + `uta migrate`
> - Add `.worktrees/` to `.gitignore` (worktrees live inside the bind-mounted workspace so they persist on the host and share the one `.git`; no mount change, no rebuild).
> - A teardown helper (`git worktree remove` + `dropdb`).
> - Update the CLAUDE.md worktree note from "deferred" to the chosen model (one container; per-worktree venv + throwaway DB; distinct `WEB_PORT` only when running two live stacks).
>
> ## Acceptance check
>
> - From a fresh devcontainer: `make worktree name=demo` produces a working `.worktrees/demo` on branch `demo`, with its own venv and `uta_demo` database, where `pytest -m "not live"` passes.
> - Two worktrees can run `pytest -m "not live"` **concurrently** without interfering (including the migration test, thanks to per-worktree DBs).
> - Every parallel session is prompt-free (the devcontainer's baked `bypassPermissions` managed-settings is container-wide).
> - `.worktrees/` is gitignored; the CLAUDE.md note reflects the in-container model.


<a id="issue-32"></a>

### #32 — Run the devcontainer prompt-free; make development devcontainer-only

- **State:** Closed
- **Labels:** area:infra, type:chore
- **Opened:** 2026-07-04 · **Closed:** 2026-07-04
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/32

> ## Intent
>
> Local devcontainer sessions get frequent permission prompts while cloud sessions run near-autonomous. Make the devcontainer prompt-free and standardize on devcontainer-only development.
>
> ## Scope
>
> - Bake `permissions.defaultMode: bypassPermissions` into the devcontainer image at `/etc/claude-code/managed-settings.json` (Linux managed-settings path — highest precedence, and not shadowed by the workspace bind mount or the `~/.claude` named volume, so the image copy is authoritative). Sanctioned for isolated containers; `rm -rf /`/`~` and the repo `deny` rules still act as circuit-breakers.
> - Empty the hand-maintained `permissions.allow` list in `.claude/settings.json` (redundant under the managed mode); keep the `deny` backstop and the `acceptEdits` default for non-devcontainer contexts.
> - Update CLAUDE.md: replace the "Shell-command hygiene / avoid permission prompts" section with a "Development happens only in the devcontainer" note, and reframe the bare VM host as deployment-only.
>
> ## Acceptance check
>
> - After a devcontainer rebuild, Claude Code runs without permission prompts.
> - `.claude/settings.json` has an empty `allow` list and retains the `deny` rules.
> - CLAUDE.md reflects the devcontainer-only model.


<a id="issue-34"></a>

### #34 — the flaky leaderboard is missing a total

- **State:** Closed
- **Labels:** —
- **Opened:** 2026-07-04 · **Closed:** 2026-07-05
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/34

> Add a total count at the top of the flaky leaderboard


<a id="issue-35"></a>

### #35 — enahnce timestamp display

- **State:** Closed
- **Labels:** —
- **Opened:** 2026-07-04 · **Closed:** 2026-07-05
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/35

> in all pages, the timestamps are shown like this:
> 2026-06-29 16:15:46.142000+00:00
>
> I only want the precision to the seconds.
> like this: 2026-06-29 16:15:46
>
> furthermore, i do not want the timestamp to be displayed as non breaking text
>
> to be adapted in all views


<a id="issue-36"></a>

### #36 — add error information of failing tests in failure episodes

- **State:** Closed
- **Labels:** —
- **Opened:** 2026-07-04 · **Closed:** 2026-07-05
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/36

> currently, there is in the test-view a dedicated section "latest failure".
> But I would prefer to see the failure details in the failure episodes (per episode)
>
> I want to have the failure detail expanded if the episode is "current" and "open". for all other episodes the failure section should be collapsed


<a id="issue-37"></a>

### #37 — make a new page "Job runs"

- **State:** Closed
- **Labels:** —
- **Opened:** 2026-07-04 · **Closed:** 2026-07-05
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/37

> Make a new page "Job runs" that list all the ingested runs.
> For each run, I expect to see:
> - the run number with a a link to the run detail (already existing in the app -> /runs/<run_number>)
> - the state of the run (green/orange/red)
> - a link to the Jenkins URL of this run
> - run start
> - run duration
> - an overview of the tests: I want to see 
>   - the total of failing/skipped/successfull tests + overall total count
>   - the number regrgessions: new failures that were added with this run (compared to the previous)
>   - the number of newly fixed tests (that were are fixed with this run and failed in the previous run)
>
>
> At the top I want to see the time of the last poller run + when the next will be started


<a id="issue-38"></a>

### #38 — Add VS Code run configs for rebuild/restart and debug loops

- **State:** Closed
- **Labels:** area:infra, type:chore
- **Opened:** 2026-07-04 · **Closed:** 2026-07-04
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/38

> Add `.vscode/tasks.json` and `.vscode/launch.json` so the app can be recompiled/restarted and debugged from the IDE.
>
> **tasks.json** — `Ctrl+Shift+B` rebuilds + recreates the `web`+`poller` containers (`docker compose up -d --build`), plus tasks for full-stack up, stop, tail web logs, and the offline test gate.
>
> **launch.json** — debugpy configs: uvicorn `--reload` for the web app (breakpoints + auto-restart, no image rebuild), the in-memory demo app (no external deps), and a CLI subcommand.
>
> **Acceptance:** both files present under `.vscode/`, valid JSON, and `Ctrl+Shift+B` runs the rebuild/restart task.


<a id="issue-44"></a>

### #44 — docs: note baked bypassPermissions is CLI-only; VS Code extension needs its own toggle

- **State:** Closed
- **Labels:** area:docs, type:chore
- **Opened:** 2026-07-05 · **Closed:** 2026-07-05
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/44

> ## Problem
> The image bakes `bypassPermissions` into `/etc/claude-code/managed-settings.json`, and CLAUDE.md ("Development happens only in the devcontainer") states this makes Claude Code run **prompt-free**. That is true for the **terminal CLI**, which reads managed-settings directly.
>
> It is **not** true for the **native VS Code extension**. The extension has a separate safety gate: it won't enter bypass mode until the per-machine **"Allow dangerously skip permissions"** toggle is enabled in the extension's VS Code settings (Extensions → Claude Code), even though managed-settings correctly outranks the project's `defaultMode: acceptEdits`. Until that toggle is flipped, the extension keeps prompting for Bash and most non-edit tools. These are per-user VS Code settings, so the image cannot bake them the way it bakes managed-settings.
>
> ## Fix
> Add a short note to CLAUDE.md's devcontainer section clarifying the CLI-vs-extension distinction, and how to make the extension prompt-free:
> 1. VS Code Settings → Extensions → Claude Code → enable "Allow dangerously skip permissions".
> 2. Select "Bypass permissions" in the mode indicator, or set `"claudeCode.initialPermissionMode": "bypassPermissions"`.
>
> ## Acceptance check
> CLAUDE.md's "Development happens only in the devcontainer" section explains that the baked `bypassPermissions` is prompt-free for the terminal CLI but the VS Code extension requires the per-machine toggle + mode selection.


<a id="issue-46"></a>

### #46 — Add new concept: ZEPHYR TEST CASE INFO

- **State:** Closed
- **Labels:** —
- **Opened:** 2026-07-05 · **Closed:** 2026-07-05
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/46

> When unittests fail, then might contain "ZEPHYR TEST CASE INFO" in their output,
> Analyse existing data to recognize the format.
> Here an example I took:
> `----------------------------------------------------------------------
>
> ZEPHYR TEST CASE INFO:
> Unit test referenced by following test case(s): LX-T4792
> 	LX-T4792 (tha): "Unit Test | SMB: Function and Display of function tests"
>
> ----------------------------------------------------------------------`
>
> The goal of this issue is to extract the zehpyr test case identifiers (example LX-T4792) from the failing test output and store it with the test.
>
>
> When a ZEPHYR test case was identified for a test, display it in the "lifecyle" box (my guess is that this is the best place. the developper should challenge this. The zephyr test case identifier (example: LX-T4792) should be a link that brings you to the detail page with this URL:
> https://labsolution.atlassian.net/projects/LX?selectedItem=com.atlassian.plugins.atlassian-connect-plugin:com.kanoah.test-manager__main-project-page#!/v2/testCase/LX-T4792 (this is an example URL. LX-T4792 needs to be replaced by the clicked test case identifier)


<a id="issue-49"></a>

### #49 — Populate suggested_contact from change-candidate authors

- **State:** Closed
- **Labels:** area:analysis, type:feat
- **Opened:** 2026-07-05 · **Closed:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/49

> ## Intent
>
> `Classification.suggested_contact` is plumbed everywhere but never written: it is read by the regression email (`src/uta/delivery/email.py:92`), the test record view (`src/uta/web/views.py:261`), and the one-click Confirm action (`src/uta/web/actions.py:104`) — but no code path in `classify.py` or `hypothesize.py` ever populates it. As a result, **Confirm currently attributes `causing_person = None`**, making the one-click confirm flow a silent no-op on the person field.
>
> The data to fix it is already captured: SVN author on `CodeChangeCandidate` and `USRCODE` on `DataChangeCandidate`. Derive the suggestion at classification time:
>
> - `CODE_CHANGE` → the SVN candidate author (when one author's changes dominate/are sole in the window)
> - `DATA_CHANGE` → the `V_TRACKING` `USRCODE` (same logic)
> - ambiguous (multiple authors, mixed signals) → leave `None` rather than guess
>
> ## Acceptance check
>
> - `classify_episode()` writes `suggested_contact` when exactly one author is in play for the winning cause; unit tests cover single-author, multi-author (→ `None`), and no-candidate cases.
> - One-click Confirm on an episode with a suggested contact stamps that contact as `causing_person` with `AI_CONFIRMED` provenance.
> - The regression email shows the suggested contact for new failures.
> - Demo dataset seeds at least one episode with a populated suggested contact so the live demo shows the feature.


<a id="issue-50"></a>

### #50 — Rank change candidates per failing test and feed change details to the LLM prompt

- **State:** Closed
- **Labels:** area:analysis, type:feat
- **Opened:** 2026-07-05 · **Closed:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/50

> ## Intent
>
> Attribution is run-windowed by design — `src/uta/models/signals.py:1-6` explicitly names per-test relevance ranking as the later enhancement; this is that enhancement. Today every failing test shows the same unranked candidate list, and `build_prompt()` (`src/uta/llm/prompt.py:60`) passes only integer *counts* of code/data candidates, so the LLM cannot name a likely culprit even though authors, changed paths, and changed entities are all in the store.
>
> Two parts:
>
> 1. **Per-test relevance ranking** — score each candidate against the failing test: changed SVN paths matched against the test's module / stack-frame paths (`ut_report.py` already extracts frame locations), changed `V_TRACKING` entities matched against the error text. Surface the ranked list on the test record instead of the flat run-wide list.
> 2. **Richer LLM context** — pass the top-ranked candidates (author, path/table, commit message) into the hypothesis prompt instead of bare counts, so hypotheses become concrete ("likely commit X by Y touching Z").
>
> This also sharpens `classify_episode()` (relevance can break the current "both code and data present → UNKNOWN" tie) and is the prerequisite for the deferred confidence score (`src/uta/analyze/classify.py:16`).
>
> ## Acceptance check
>
> - Test record shows candidates ordered by relevance to *that* test, with the match reason visible (path overlap / entity mention).
> - Unit tests cover path-match, entity-match, and no-match scoring against golden fixtures (offline, no live systems).
> - `build_prompt()` includes top-N candidate details; prompt-construction unit test asserts authors/paths appear and that redaction discipline holds (no raw `MODDATA`).
> - Demo dataset seeds a failure whose top-ranked candidate is visibly different from another failure in the same run.


<a id="issue-51"></a>

### #51 — Harden the poller: retries, build quarantine, real /health, staleness alerting, job recovery

- **State:** Closed
- **Labels:** area:infra, type:feat
- **Opened:** 2026-07-05 · **Closed:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/51

> ## Intent
>
> Several resilience gaps around the poller and ops surfaces:
>
> - A transient Jenkins/Oracle blip fails the whole tick with no retry/backoff (`src/uta/poller.py:116-121`, `poll_tick` swallow at `:167-170`) — the tick just waits for the next interval.
> - One malformed build wedges ingest indefinitely: e.g. `_track_of` raising `ValueError` (`src/uta/ingest/ut_report.py:84-86`) or a missing `startTimeMillis` (`src/uta/ingest/wfapi.py:75`) propagates as a non-404 error every tick, and the high-water mark never advances.
> - `GET /health` returns a static literal (`src/uta/web/app.py:136`) — no DB ping, no heartbeat freshness.
> - The heartbeat records everything needed to detect a stale poller, but nothing evaluates it — no "no successful poll in N intervals" alert.
> - On-demand ingest jobs run in raw daemon threads (`src/uta/control/jobs.py:150`); a restart leaves `QUEUED`/`RUNNING` rows stuck forever with no recovery.
>
> ## Scope
>
> 1. Retry with exponential backoff for transient HTTP/DB errors inside a tick.
> 2. Quarantine a persistently-failing build after K attempts: record it (visible on the control panel), advance past it — mirror of the existing 404-skip, but explicit and surfaced.
> 3. `/health` checks DB connectivity and heartbeat freshness; returns non-200 when stale.
> 4. Ops alert email when the poller goes stale or a build is quarantined/skipped (reuse the `EmailSender` seam).
> 5. On startup, mark orphaned `RUNNING`/`QUEUED` jobs as `ERROR` (or resume them).
>
> ## Acceptance check
>
> - Unit tests with fakes: transient failure → retried and succeeds within the same tick; persistent failure → build quarantined, high-water mark advances, alert sent.
> - `/health` returns 503 with a stale heartbeat or unreachable DB (ephemeral-Postgres test).
> - Restart with an in-flight job row → job is not left `RUNNING`.
> - Offline suite stays green with zero live access.


<a id="issue-52"></a>

### #52 — Add data retention/pruning and fix dashboard scale (pagination, N+1 queries)

- **State:** Closed
- **Labels:** area:dashboard, type:perf
- **Opened:** 2026-07-05 · **Closed:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/52

> ## Intent
>
> Nothing ever prunes: at ~25k `TestCaseResult` rows per nightly run that is roughly 9M rows/year, plus unbounded signatures, heartbeat error history, and completed `IngestJob` rows. Meanwhile the UI degrades with size: the `?expand=` link on a run renders all ~25k rows in one page (`src/uta/web/views.py:441`, `_cap` at `:46`), and the triage/runs pages have per-row lazy-load N+1 patterns (`views.py:101`, `_latest_classification` per episode).
>
> ## Scope
>
> 1. **Retention policy** (tunable): drop raw per-test *passing* results older than N days; keep runs, episodes, lifecycles, attributions, and KB signatures/aggregates forever — the KB aggregates carry the long-term value, and `kb/store.py` already recomputes counts from linked results, so the pruning boundary must not corrupt occurrence counts (recompute or freeze aggregates before deletion).
> 2. Prune completed ingest jobs and cap heartbeat history.
> 3. Server-side **pagination** on the run results table and runs list, replacing the all-or-nothing expand link.
> 4. Eager-load / batch the N+1 patterns on triage and runs pages.
>
> ## Acceptance check
>
> - Pruning runs as part of the poll tick (or a CLI command), is idempotent, and a unit test proves KB occurrence counts and episode history survive pruning of old results.
> - Run page with >`ui_row_limit` results paginates; no route loads all results into memory unbounded.
> - Query count on the triage page is O(1)-ish in the number of rows (asserted with a SQLAlchemy statement counter in tests).
> - Offline suite green; no visible-surface change beyond pagination controls (demo dataset: verify pagination is exercised or explicitly not needed at demo size).


<a id="issue-53"></a>

### #53 — Add trend visualization: run-health timeline and per-test flakiness sparklines

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-05 · **Closed:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/53

> ## Intent
>
> Every dashboard surface is a point-in-time table, but the data is trend-rich: run pass/fail totals and regression counts over time, flakiness score history per test, KB signature recurrence over months. Add a small set of charts so the dashboard answers "is the suite getting healthier?":
>
> - **`/runs`**: a run-health timeline (failed/regression counts per run over time).
> - **`/flaky` + test record**: a per-test pass/fail sparkline over the flakiness window, making oscillation visible at a glance.
>
> Implementation should stay within the current stack discipline: server-rendered inline SVG from Jinja (no JS framework, no CDN — the app vendors its assets).
>
> ## Acceptance check
>
> - `/runs` shows a timeline chart driven by the same data as the table; test record and `/flaky` rows show a sparkline of recent run outcomes.
> - Rendering is covered by offline unit tests (template renders expected SVG elements from a fixture history).
> - Demo dataset seeds enough run history for the charts to show a visible trend and at least one oscillating (flaky) sparkline — per the CLAUDE.md rule that every user-visible surface has a representative demo example.


<a id="issue-54"></a>

### #54 — Enable TLS verification for the Jenkins client by default

- **State:** Closed
- **Labels:** area:ingest, type:fix
- **Opened:** 2026-07-05 · **Closed:** 2026-07-05
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/54

> ## Intent
>
> The Jenkins HTTP client is created with `verify=False` (`src/uta/ingest/jenkins.py:38,43`), silently disabling TLS certificate verification for all Jenkins traffic. Verification should be **on by default**, with an explicit opt-out env setting (e.g. `JENKINS_VERIFY_TLS=false`, documented in `.env.example`) for the internal-CA case — and ideally a CA-bundle path setting as the proper fix instead of the opt-out.
>
> ## Acceptance check
>
> - Default client verifies TLS; `verify` is driven by a typed setting, documented in `.env.example`.
> - Unit test asserts the client is constructed with verification on by default and off when the setting is set.
> - Deployment note: confirm the real Jenkins cert chain (or configure the CA bundle) before rollout so the poller doesn't break on upgrade.


<a id="issue-55"></a>

### #55 — Unittest log parser: stop defaulting unknown outcomes to PASSED

- **State:** Closed
- **Labels:** area:ingest, type:fix
- **Opened:** 2026-07-05 · **Closed:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/55

> ## Intent
>
> The console-log stage parser defaults an unrecognized outcome tail to `PASSED` (`src/uta/ingest/unittest_log.py:76`). The parser is regex-based over console text, so a nose2/logging format change would silently turn real failures **green** — the worst possible failure mode for this tool (silent corruption, per the CLAUDE.md invariants spirit).
>
> Change the default to a loud path: map unrecognized tails to a non-green outcome (e.g. `SKIPPED`/`UNKNOWN`) **and** log a warning with the unmatched line; optionally count unmatched lines per stage and surface the count on the run summary so a format drift is noticed immediately rather than months later.
>
> ## Acceptance check
>
> - Golden-fixture unit test: a line with an unrecognized outcome tail does not produce a `PASSED` result and emits a warning.
> - Existing fixtures for the four unittest stages still parse identically (no regression on known formats).
> - If a per-stage unmatched-count is surfaced on the run summary, seed a demo example; if kept log-only, no demo change needed.


<a id="issue-63"></a>

### #63 — Make the triage queue a real work surface: filters, search, and bulk actions

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-06 · **Closed:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/63

> ## Intent
>
> The triage queue (`GET /`) is the daily-action surface, but today it offers no way to narrow or act on the list at scale:
>
> - **No filtering or search** — no filter by owner, suite, track, predicted cause, triage status, flaky flag, or age; sorting is hardcoded in `views.triage_queue` (`src/uta/web/views.py:262`). The run-results table (`/runs/{build}`) similarly can't be filtered by status (e.g. failures only), and there is no global "jump to test by name" search in the navbar.
> - **No bulk actions** — when one root cause breaks 50 tests, each must be acknowledged/attributed one full-page reload at a time (`src/uta/web/actions.py`).
>
> ## Scope
>
> 1. **Filter/sort bar on the triage queue**: filter by owner initials, suite, track, predicted cause, triage status, flaky flag; selectable sort (age, name, owner). Filters live in query params so views stay server-rendered and bookmarkable.
> 2. **Status filter on the run-results table** (`/runs/{build}`): at minimum "failures only" — paging through ~25k rows to find failures is the current reality.
> 3. **Global test search** in the navbar (name/suite substring → per-test record, or a short result list).
> 4. **Bulk acknowledge / bulk attribute** on the triage queue via row checkboxes. Since failing results already carry a shared KB signature, include a one-click **"acknowledge/attribute all tests with this signature"** — that's the high-leverage form of bulk action for the one-cause-many-tests case.
> 5. Interactions may be plain form POSTs (existing PRG pattern) or HTMX partial updates — the stack is described as HTMX but currently has none; this is the natural place to introduce it if it pulls its weight.
>
> ## Acceptance check
>
> - On the triage queue, filtering by e.g. owner or suite reduces the visible buckets accordingly, and the filter state survives an acknowledge round-trip.
> - On a run summary, a "failures only" filter shows only non-passing results with correct pagination counts.
> - Selecting multiple New tests and acknowledging them in one action moves all of them to Still failing, stamped with the current actor.
> - "Acknowledge all with this signature" acknowledges every unacknowledged FAILING test sharing that failure signature.
> - Offline suite (`pytest -m "not live"`) covers the new filter/bulk paths; demo dataset seeds enough variety (multiple owners/suites, a shared-signature multi-test failure) that the live demo exercises the filters and bulk-by-signature action.


<a id="issue-65"></a>

### #65 — Parallelize the per-build Jenkins fetch path in ingest

- **State:** Closed
- **Labels:** area:ingest, type:perf
- **Opened:** 2026-07-06 · **Closed:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/65

> ## Intent
>
> `ingest_build` (`src/uta/ingest/pipeline.py:170`) fetches everything for a build **sequentially** on a sync `httpx.Client`: `build_meta`, `wfapi/describe`, `testReport/api/json`, `changeSets`, plus — when `ingest_unittest_logs` is on — a `stage_describe` + `stage_log` pair per unittest stage (5 suites × 2 tracks ⇒ 10+ extra calls). That's 20+ serial round-trips per build. Fetch time is already logged separately per phase (`pipeline.py:331`), and it's the dominant cost now that the DB side (bulk identity resolution, single Core `insert()`) is already optimized.
>
> ## Scope
>
> - Parallelize the independent Jenkins HTTP calls within `ingest_build`'s fetch phase — the 4 base endpoints are mutually independent, and each unittest stage's `stage_describe`/`stage_log` pair is independent of the others. Use a thread pool (simplest given the existing sync `httpx.Client` behind the `JenkinsClient` Protocol) or move to an async client — either is fine as long as the `JenkinsClient` Protocol/fake-based test seam in `src/uta/ingest/jenkins.py` is preserved so offline tests keep working with zero real network access.
> - Preserve current error handling/semantics: a failure on any one fetch must still propagate the same way it does today (so poller retry/quarantine behavior in `src/uta/poller.py` is unaffected).
> - No change to parsing, dedup, persistence, or analysis — this is fetch-phase only.
>
> ## Explicitly out of scope
>
> - Metrics/observability improvements (poller lag, tick duration, `/metrics`, etc.) — tracked separately.
> - Any change to the on-demand ingest path's retry behavior (`src/uta/control/jobs.py`) beyond what falls out naturally from the shared fetch code.
>
> ## Acceptance check
>
> - Offline suite (`pytest -m "not live"`) stays green with fakes; add/adjust tests asserting the parallel fetch still produces identical `IngestResult` output as the serial version for a multi-stage build fixture.
> - Per-phase fetch-time log (`pipeline.py:331`) shows reduced wall-clock on a build with unittest-log stages enabled, verified locally against real or fixture-backed timing (not just fewer calls).
> - A single-endpoint failure (e.g. `testReport` 5xx) still surfaces as the same exception type/behavior the poller's transient-retry/quarantine logic (`src/uta/poller.py`) already expects.


<a id="issue-68"></a>

### #68 — Add a light/dark theme toggle to the dashboard

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-06 · **Closed:** 2026-07-06
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/68

> The dashboard is styled with Bootstrap 5.3 (`bootstrap.min.css`), which ships built-in dark-mode
> support via `data-bs-theme` on `<html>`, but the app never sets it — the UI is always light.
>
> ## What
> Add a theme toggle button to the navbar (`base.html`) that lets a user switch between light and
> dark Material-style themes.
>
> - Default to the visitor's OS/browser preference (`prefers-color-scheme: dark` media query) on
>   first visit, when no explicit choice has been saved.
> - Let the user override the default via a button in the navbar; persist the explicit choice
>   (`localStorage`) so it survives reloads/navigation.
> - Apply the theme by setting `data-bs-theme` on `<html>`, and extend the domain-specific CSS
>   overrides already layered on top of Bootstrap in `base.html` (status colors, badges, cards,
>   timeline chart, sparkline, etc.) so they hold up in dark mode instead of just Bootstrap's own
>   chrome.
> - Avoid a flash of the wrong theme on load (apply the stored/detected theme before first paint).
>
> ## Acceptance check
> - Visiting with no saved preference and an OS/browser dark-mode setting renders the dashboard in
>   dark theme; with a light setting, it renders light.
> - Clicking the toggle switches theme immediately and the choice persists across page loads/routes.
> - All existing pages (triage, runs, run detail, flaky, KB, control, search, test record) remain
>   readable in both themes — no unreadable text-on-background combinations.


<a id="issue-72"></a>

### #72 — Show last ingested Jenkins run on Triage screen

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-07 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/72

> Add a small info element to the Triage screen showing the last ingested Jenkins run:
>
> - Build number, linked to that run's detail page
> - Run start time
>
> ## Acceptance check
> The Triage screen displays the most-recently-ingested run's number (as a link to its detail page) and its start time. When no runs have been ingested yet, it degrades gracefully (no broken element).


<a id="issue-73"></a>

### #73 — Close the learning loop: score AI-suggestion accuracy and populate classification confidence

- **State:** Closed
- **Labels:** area:analysis, type:feat
- **Opened:** 2026-07-07 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/73

> ## Intent
>
> Scaffolding for learning from triage verdicts already exists but nothing consumes it:
>
> - `Attribution.original_ai_cause` / `original_ai_reason` are retained on human correction specifically to measure AI quality (`src/uta/models/attribution.py:42`), but nothing ever compares them against the corrected values.
> - `Classification.confidence` is deliberately left `None` ("pending a learning loop", `src/uta/models/classification.py:31`) — it has never been populated.
> - The classifier's code-vs-data tie-break is boolean rather than magnitude-aware (`src/uta/analyze/classify.py:125`): when both a code and a data candidate are "relevant" (score > 0), the result is `UNKNOWN` regardless of how much stronger one candidate is than the other. A tier-3 module-level code match tied against a tier-2 component data mention should not collapse to `UNKNOWN`.
>
> ## Scope
>
> 1. **AI-accuracy metric**: using `original_ai_cause`/`original_ai_reason` vs the human-corrected `causing_person`/`reason`/predicted cause, compute a confirmed-vs-corrected precision signal over time (e.g. "AI suggestions confirmed vs corrected in the last N days/attributions"). Surface it somewhere visible — a small panel on `/control` or a new lightweight view is fine; this doesn't need to be elaborate.
> 2. **Fix the classifier tie-break** in `classify.py`: compare `ranked.top_code.score` vs `ranked.top_data.score` (with a margin) instead of the current boolean "both relevant → UNKNOWN" check, so a clear score winner is chosen over the weaker candidate.
> 3. **Populate `Classification.confidence`**: derive it from the relevance-tier gap between the winning and losing candidate plus the KB provenance weight of any matching signature (per `kb/retrieval.py`'s existing provenance ranking: HUMAN_CORRECTED > HUMAN_ENTERED > AI_CONFIRMED > AI_UNCONFIRMED). Keep the derivation deterministic and simple — no new ML model, just a documented scoring formula.
>
> ## Explicitly out of scope
>
> - Any change to the LLM hypothesis provider/model choice or prompting.
> - Building a general analytics/BI page — the accuracy metric can be minimal.
>
> ## Acceptance check
>
> - A test-covered case with a strong code-tier match and a weak data-tier match now classifies as `CODE_CHANGE` (or `DATA_CHANGE` symmetrically) instead of `UNKNOWN`.
> - `Classification.confidence` is populated (non-`None`) for newly classified episodes, with unit tests covering at least: unambiguous single-candidate case (high confidence), close tie (low confidence), and a KB-provenance-boosted case.
> - Some UI surface (control panel or equivalent) shows a confirmed-vs-corrected count/ratio for AI-attributed causes, computable offline from fixture data.
> - Offline suite (`pytest -m "not live"`) covers the new tie-break and confidence logic; demo dataset seeds at least one example each of a resolved tie-break and a visible confidence value so the live demo shows the feature.

**Comment — palmkevin, 2026-07-08:**

> Implemented and merged in #74 (commit 65563d8, on `main` since 2026-07-07). The PR body said `Refs #73` rather than `Closes #73`, so the merge didn't auto-close this issue — closing it manually as completed.
>
> All acceptance checks are satisfied on `main`:
> - Score-magnitude tie-break in `analyze/classify.py` (`TIE_BREAK_MARGIN`): a strong code-tier match vs a weak data-tier match now classifies as CODE_CHANGE (and symmetrically for data) instead of UNKNOWN.
> - `Classification.confidence` populated by the documented deterministic formula, with unit tests for the unambiguous single-candidate, close-tie, and KB-provenance-boosted cases.
> - `/control` shows the AI-suggestion accuracy panel (confirmed vs corrected + precision), computable offline.
> - Demo seeds `test_discount_tiers` (resolved tie-break, visible confidence) and a confirmed + corrected verdict pair for the accuracy panel.
>
> ---
> _Generated by [Claude Code](https://claude.ai/code)_


<a id="issue-75"></a>

### #75 — Add flash feedback for every mutating action

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-07 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/75

> **Intent.** Every mutating POST (acknowledge, bulk acknowledge, "Ack all w/ signature", episode attribute/confirm, bulk attribute, identity set, control-panel saves/reverts/ingest) currently 303-redirects with zero confirmation — the row just disappears and the user has to infer success. Only `/control` has feedback, and only for errors (`?error=` → alert). Add a small flash pattern (short-lived message carried across the redirect, rendered as a dismissible Bootstrap alert in `base.html`) so every action reports what it did, e.g. *"Acknowledged 7 tests sharing this signature"*, *"Saved — triage status → INVESTIGATING"*, *"Threshold overridden (was 0.35)"*. Generalize the existing `/control` error banner into the same mechanism.
>
> **Acceptance check.** Performing any mutating action on any page shows a one-shot confirmation banner (with a meaningful, count-bearing message where applicable) on the page the user lands on; reloading that page does not re-show it; `/control` errors render through the same mechanism; offline tests cover the flash round-trip.


<a id="issue-76"></a>

### #76 — Bulk-selection ergonomics on the triage queue (select-all, live count, disabled at zero)

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-07 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/76

> **Intent.** The triage queue's bulk acknowledge / bulk attribute require ticking checkboxes one by one, and the "Acknowledge selected" / "Apply to selected" buttons give no hint of how many rows are selected (and no-op when nothing is selected). Add: a select-all checkbox in each bulk table's header (with indeterminate state on partial selection), a live count on the bulk buttons (e.g. "Acknowledge selected (12)"), and disable the bulk buttons while zero rows are selected. Small vanilla-JS enhancement in the template layer — no framework.
>
> **Acceptance check.** On `/` with rows in "New failing" and "Still failing": header checkbox selects/deselects all rows in that table only; bulk buttons show the live selected count and are disabled at zero; partial selection shows the header checkbox indeterminate; behaviour is covered by offline tests for the rendered markup (JS hooks present, buttons initially disabled).


<a id="issue-77"></a>

### #77 — Make triage filters instant and self-describing (auto-submit, filter chips, sortable columns)

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-07 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/77

> **Intent.** The triage filter bar requires filling fields and clicking "Apply filters", and once applied there is no at-a-glance signal of what is filtered — the state lives only inside the form controls. Sorting is a dropdown inside the same form rather than clickable column headers. Add: (1) auto-submit on change for the select/checkbox filters (text inputs still submit on Enter/Apply), (2) active filters rendered as removable chips above the tables (e.g. `owner: KP ✕ · flaky only ✕`), each chip's ✕ re-requesting the page without that filter, (3) clickable column-sort headers for the columns the server already sorts by (age/name/owner), replacing or complementing the Sort dropdown.
>
> **Acceptance check.** Changing a select/checkbox filter reloads the queue immediately without pressing Apply; every active filter appears as a chip whose ✕ removes just that filter; clicking the Test/Owner column header sorts by it (visibly marked); all filter/sort state stays in the URL (shareable); offline tests cover chip rendering and sort-link generation.


<a id="issue-78"></a>

### #78 — Auto-refresh control-panel ingest jobs (vendored HTMX polling + progress bar)

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-07 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/78

> **Intent.** The control panel says *"Reload to refresh job status"* while an ingest job is RUNNING. Vendor htmx (single static file under `src/uta/web/static/`, consistent with the no-CDN discipline) and poll just the jobs table as a fragment: `hx-get` every few seconds while any job is QUEUED/RUNNING, stopping once all are terminal. Show a progress bar per running job from the existing `builds_done / builds_total`. Serve the fragment from a small endpoint that renders only the jobs-table partial.
>
> **Acceptance check.** With a queued/running ingest job, `/control` updates the job table (status + progress bar) within a few seconds without a manual reload, and stops polling when all jobs are DONE/ERROR; no CDN/network dependency is introduced; offline tests cover the fragment endpoint and the poll-stop condition.


<a id="issue-79"></a>

### #79 — Orientation polish: active nav state, triage-count navbar badge, relative timestamps

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-07 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/79

> **Intent.** Three small orientation gaps that compound: (1) the navbar never marks the current section — pass the active route into `base.html` and set Bootstrap's `active` class on the matching nav link; (2) the count of unacknowledged new failures — the app's core number — is only visible on the triage page; add a small red badge on the "Triage" nav link (e.g. `Triage 3`) visible from every page, hidden at zero; (3) timestamps render absolute-only via the `|ts` filter, but for triage *age* is what matters — render a relative form ("2 days ago") with the absolute value in a `title` tooltip (server-side, no JS), applied at least to the triage queue and test-record ages.
>
> **Acceptance check.** On every page the current nav item is visually active; the Triage link shows the live unacknowledged-new count (absent when zero); triage/test-record timestamps read relative with absolute on hover; offline tests cover the badge count, active-state marking, and the relative-time filter.


<a id="issue-80"></a>

### #80 — Poller schedules its interval job paused — never polls again after the startup tick

- **State:** Closed
- **Labels:** area:infra, type:fix
- **Opened:** 2026-07-07 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/80

> **Severity: critical (found in app-wide bug review)**
>
> `run_scheduler` (`src/uta/poller.py:359`) passes `next_run_time=None` to `BlockingScheduler.add_job`. In APScheduler 3.x an explicit `next_run_time=None` adds the job **paused** (documented: "pass None to add the job as paused"; verified empirically — the job's `next_run_time` stays `None` and it never fires). The poller therefore runs exactly the one manual startup `_tick()` and then blocks forever without ever polling again.
>
> **Fix intent:** drop the `next_run_time=None` argument — the interval trigger already first-fires at now+interval, and the manual startup `_tick()` already covers "don't idle until the first interval".
>
> **Acceptance check:** a unit test asserting that the job registered by `run_scheduler` is not paused (has a real `next_run_time` once the scheduler starts / would fire on the interval). Offline suite stays green.


<a id="issue-81"></a>

### #81 — Move the regression alert email out of the ingest transaction

- **State:** Closed
- **Labels:** area:email, type:fix
- **Opened:** 2026-07-07 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/81

> **Severity: critical (found in app-wide bug review)**
>
> `maybe_notify` — a live SMTP send — runs inside the ingest `session_scope` block (`src/uta/ingest/pipeline.py:349-355`), i.e. before commit. Two failure modes, both bad:
>
> 1. **SMTP outage destroys ingests:** `smtplib` raises → the entire ~25k-row ingest rolls back. `SMTPException` is not classified transient by `poller._is_transient`, so each tick records a quarantine attempt — a mail outage spanning `quarantine_after_attempts` ticks **quarantines a perfectly healthy build** and silently loses that night's run until manual re-ingest.
> 2. **Commit failure duplicates alerts:** the email sends, then `commit()` fails with a transient `OperationalError` → the poller retries `ingest_build`, recomputes the identical diff, and **sends the same regression alert again**. There is no "already notified" record anywhere; the same applies across ticks for non-transient post-send commit failures.
>
> **Fix intent:** send the alert *after* the ingest transaction commits, and wrap the send so an email failure can never fail (or roll back) the ingest — log it / surface it on the heartbeat instead. Ensure at-most-once semantics per run (e.g. derive the notification from the committed run inside a separate scope, or record a notified marker).
>
> **Acceptance check:** unit tests proving (a) a raising email sender does not prevent the run from being persisted, and (b) a commit-then-retry cycle does not send the alert twice. Offline suite stays green.


<a id="issue-82"></a>

### #82 — Guard apply_run against out-of-order re-ingest of historical builds

- **State:** Closed
- **Labels:** area:analysis, type:fix
- **Opened:** 2026-07-07 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/82

> **Severity: critical (found in app-wide bug review)**
>
> `apply_run` (`src/uta/analyze/lifecycle.py:190-304`) diffs old-run vs old-baseline but applies the transitions to the **current** `TestLifecycle` / `FailureEpisode` rows, and the control panel's range ingest (`src/uta/control/jobs.py`) — the documented recovery path for quarantined builds — makes this reachable for arbitrary historical builds.
>
> Concrete corruption: build #103 is quarantined and skipped; #104–#106 ingest; test T failed in #103 but was fixed by #104 (episode closed). Re-ingesting #103 later diffs vs #102, sees T as a regression, and **opens a phantom episode** (episode_number bumped, acknowledgement cleared, lifecycle FAILING) that no later run will ever close — T shows FAILING forever. The reverse also corrupts: a test currently failing whose old run shows it passing gets its **live episode closed** with `fixed_in_run_id` pointing at the old build, hiding an actively failing test. `last_failing_at` can also move backward and `age_runs` shrink.
>
> **Fix intent:** lifecycle transitions must only be driven by runs *newer* than the state they mutate — e.g. skip `apply_run` (and the dependent classify/hypothesize/notify steps) when the ingested run is not the newest complete run, while still persisting the run, its results, and KB signatures. The pipeline's "idempotent per (baseline, run)" claim should hold for historical re-ingest too.
>
> **Acceptance check:** unit test — after ingesting builds N-2, N-1, N, re-ingesting an older build (with a differing pass/fail set) leaves lifecycle states, episodes, and acknowledgements untouched. Offline suite stays green.


<a id="issue-83"></a>

### #83 — Consult shard status in run completeness — an aborted run must not become a baseline

- **State:** Closed
- **Labels:** area:ingest, type:fix
- **Opened:** 2026-07-07 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/83

> **Severity: critical (found in app-wide bug review)**
>
> `RunTiming.is_complete` (`src/uta/ingest/wfapi.py:61-62`) only checks `len(self.shards) >= expected_shards`; `ShardTiming.status` is parsed (line 87) but never consulted — neither there nor at persist time (`pipeline.py`).
>
> Concrete failure: a build aborted midway through `devUTs: Execute - permanent_py39` still lists both UT stages in `wfapi/describe` (one with status `ABORTED`), so `run.complete = True`. `select_baseline` filters **only** on `Run.complete`, so the next run diffs against this partial run — inventing exactly the phantom "removed"/"newly fixed" mass transitions the flag exists to prevent — and the partial run itself gates into `apply_run`/`classify_run`.
>
> **Fix intent:** a run is complete only when all expected shards are present **and** each UT shard finished normally. Statuses that merely reflect test failures (`SUCCESS`, `UNSTABLE`, `FAILED`) still count as complete; `ABORTED` / `IN_PROGRESS` / `PAUSED` / `NOT_EXECUTED` must not.
>
> **Acceptance check:** unit tests — a wfapi payload with an `ABORTED` UT stage yields `complete=False` (and is skipped as a baseline), while a payload whose stages are `SUCCESS`/`UNSTABLE`/`FAILED` stays `complete=True`. Offline suite stays green.


<a id="issue-84"></a>

### #84 — Triage rows drop the second failing track — track filter hides tests failing in both tracks

- **State:** Closed
- **Labels:** area:dashboard, type:fix
- **Opened:** 2026-07-07 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/84

> **Severity: high (found in app-wide bug review)**
>
> `_failure_infos` (`src/uta/web/views.py:131-138`) builds `by_pair` with a dict comprehension over rows ordered by `TestResult.id`, so when a test failed in **both** tracks of the same run (the normal case — every test runs in `permanent` and `permanent_py39`), the later-ingested row overwrites the earlier one and the triage row carries only that one track. `_matches_filters` then does an exact `row["track"] != track` exclusion.
>
> Concrete failure: `test_x` fails in both tracks of a build; its row ends up `track="permanent_py39"` (higher result id). A user filtering the queue with `?track=permanent` does not see `test_x` at all — a genuinely failing test disappears from the filtered action queue.
>
> **Fix intent:** carry *all* failing tracks for the `(identity, run)` pair (and a signature per track or the first), render them all on the row, and make the track filter match when **any** failing track equals the filter.
>
> **Acceptance check:** unit test — a test failing in both tracks appears in the triage queue under both `?track=permanent` and `?track=permanent_py39`. Offline suite stays green.


<a id="issue-85"></a>

### #85 — Let a FAIL/ERROR traceback block override a garbled verbose status line in the unittest-log parser

- **State:** Closed
- **Labels:** area:ingest, type:fix
- **Opened:** 2026-07-07 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/85

> **Severity: high (found in app-wide bug review)**
>
> In `src/uta/ingest/unittest_log.py` the status recorded from the verbose status line always wins; the `====` FAIL/ERROR traceback block only *adds* tests not already present in `outcomes` (the `if (cls, name) not in outcomes` guard).
>
> Concrete failure: a test prints to stdout while running, so its console line becomes `test_x (mod.Cls) ... <printed junk>`; `_status_of` doesn't recognize the tail and maps it to `SKIPPED`. The test actually FAILED and its `FAIL: test_x (mod.Cls)` traceback block **is** parsed — but the block's evidence is discarded because the key already exists. The result persists as SKIPPED (a "hole"): no episode opens, no regression email — precisely the "silently turn a real failure green" mode the module's docstring says it guards against; the guard only covers the no-block case.
>
> **Fix intent:** a parsed FAIL/ERROR block is authoritative — it must override a status-line outcome that is anything other than an explicit FAIL/ERROR (and certainly an unrecognized/garbled one). While in there: the unrecognized-tail `logger.warning` currently logs the full raw console line, which for these legacy LIMS suites may contain patient data — truncate/omit the raw content (log the test id and a bounded, sanitized tail instead).
>
> **Acceptance check:** unit test — a log with a garbled status line plus a FAIL block for the same test yields FAILED with the block's details; the unrecognized-tail warning no longer embeds the full raw line. Offline suite stays green.


<a id="issue-86"></a>

### #86 — Anchor _INFRA_RE tokens on word boundaries — IOError is misclassified as infrastructure

- **State:** Closed
- **Labels:** area:analysis, type:fix
- **Opened:** 2026-07-07 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/86

> **Severity: high (found in app-wide bug review)**
>
> `_INFRA_RE` (`src/uta/analyze/error_type.py:22-28`) contains `o(?:racle)?error` with `re.IGNORECASE` and no word boundary, so it matches the substring `oerror` inside `IOError`, `ProtoError`, etc. Likewise `socket\.` matches `websocket.exceptions.ConnectionClosed`.
>
> Concrete failure: a test failing with `IOError: [Errno 2] No such file or directory: 'cfg.ini'` (a plain code/fixture bug) is typed INFRA; `classify.py` then forces `predicted_cause = INFRASTRUCTURE` at the flat 0.9 confidence, outranking the real SVN-commit evidence — the suggested contact and code-change evidence are suppressed.
>
> **Fix intent:** anchor the exception-name alternatives with word boundaries (`\boracleerror\b`, `\boerror\b` should not exist at all — the intended tokens are presumably `oracleerror` / `oerror`-as-in-`OError`? No: match `OperationalError`, `OracleError`, `ORA-xxxxx`, etc. explicitly) and make `socket\.` not match `websocket.`. Add regression cases for `IOError`, `ProtoError`, `websocket.exceptions.*` staying non-INFRA while `OracleError`, `oracledb.OperationalError`, `ORA-01234`, `socket.timeout` remain INFRA.
>
> **Acceptance check:** the unit tests above pass; offline suite stays green.


<a id="issue-87"></a>

### #87 — Make the Oracle local-time conversion DST-fold-safe

- **State:** Closed
- **Labels:** area:ingest, type:fix
- **Opened:** 2026-07-07 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/87

> **Severity: high (found in app-wide bug review)**
>
> `to_ut_ref_local` / `from_ut_ref_local` (`src/uta/ingest/clock.py:32-51`, used by `refdb/oracle.py` for the `CREDATIM BETWEEN` window and row conversion) use `astimezone(UT_REF_TZ).replace(tzinfo=None)` and `replace(tzinfo=UT_REF_TZ)` with the default `fold=0`. On the fall-back night (last Sunday of October, 02:00–03:00 local occurs twice) the naive mapping is non-monotonic:
>
> - **Window boundary:** a run ending 01:25 UTC gives `win_end` = naive `02:30` (CET, second occurrence). A `V_TRACKING` row written at 00:40 UTC has `CREDATIM = 02:40` (CEST, first occurrence); `02:40 > 02:30`, so the BETWEEN excludes a change that really happened 45 minutes *before* the window end — the culprit data change silently never becomes a candidate.
> - **Row conversion:** a row written at 01:30 UTC stores `CREDATIM = 02:30`; `from_ut_ref_local` with `fold=0` reads it as 02:30 CEST → 00:30 UTC, one hour early, shifting the persisted `DataChangeCandidate.changed_at` used for correlation.
>
> The named-zone invariant is honored; the *fold* handling is not.
>
> **Fix intent:** make the window inclusive across the fold (take the earlier local occurrence for the window start, the later for the window end — widening by up to an hour on that night is fine; the tolerance already widens it) and choose `fold` explicitly/deterministically when re-attaching the tz in `from_ut_ref_local` (document the ambiguity: prefer the interpretation that keeps candidates rather than losing them).
>
> **Acceptance check:** unit tests pinned to the fall-back transition (e.g. 2025-10-26) proving a change 45 min before the window end is not excluded, and that `from_ut_ref_local` is deterministic and documented for ambiguous times; spring-forward (nonexistent times) covered too. Offline suite stays green.


<a id="issue-88"></a>

### #88 — CSRF-protect the state-changing POST endpoints

- **State:** Closed
- **Labels:** area:dashboard, type:fix
- **Opened:** 2026-07-07 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/88

> **Severity: high (found in app-wide bug review)**
>
> No state-changing POST has CSRF protection (`src/uta/web/app.py` — `/control/settings`, `/control/settings/{key}/reset`, `/control/ingest`, acknowledge/confirm/attribute/`/identity`), and with `AUTH_ENABLED=false` (the default and current production posture) there is no session check either.
>
> Concrete failure: the app runs on the intranet; an employee's browser visits an external attacker page containing an auto-submitting `<form method=post action="http://uta.intranet/control/settings">` (or `/control/ingest`, or an episode attribute overwrite) — the browser carries the request past the network boundary and the state change lands, stamped as the victim's declared actor (or `test-user`). With `AUTH_ENABLED=true` the `SameSite=Lax` session cookie incidentally mitigates cross-site POSTs, but nothing protects the flag-off mode the app actually runs in.
>
> **Fix intent:** reject cross-site POSTs app-wide — e.g. a small middleware that, for unsafe methods, requires the request to be same-origin (validate `Sec-Fetch-Site` when present, falling back to `Origin`/`Referer` host checks) or a double-submit token wired into the shared form/HTMX layer. Must work identically in auth-off and auth-on modes and keep the offline test suite / TestClient flows working.
>
> **Acceptance check:** unit tests — a POST with a cross-site `Origin`/`Sec-Fetch-Site` is rejected (403) on control and triage endpoints; same-origin browser posts and the existing TestClient posts still succeed. Offline suite stays green.


<a id="issue-89"></a>

### #89 — Demo app must not expose the live control-panel mutation endpoints

- **State:** Closed
- **Labels:** area:dashboard, type:fix
- **Opened:** 2026-07-07 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/89

> **Severity: high (found in app-wide bug review)**
>
> `uta.demo.app` mounts the full real app, so the public Render demo serves the unauthenticated control panel:
>
> - Any anonymous visitor can POST `/control/settings`, persisting tunable overrides in the **shared** demo store (e.g. `ui_row_limit=0`) and degrading what every other visitor sees until the next restart.
> - Worse, POST `/control/ingest` spawns a daemon thread that builds a **real `HttpJenkinsClient`** and issues outbound HTTPS requests toward the config-default internal Jenkins hostname (`src/uta/config.py`) — attacker-triggerable outbound traffic from a public host, plus unbounded job-row/thread creation.
>
> **Fix intent:** in demo mode, block the mutating control-panel operations (settings override/reset, on-demand ingest) — e.g. a `demo_mode` flag on `create_app` that returns 403 (with a friendly note) for those POSTs, or a demo-safe stub — while the `/control` page itself keeps rendering its seeded, populated state. Triage actions (acknowledge/attribute/confirm) can stay: they're part of the demo story and the store is ephemeral. Keep the demo dataset/story intact.
>
> **Acceptance check:** unit tests — with the demo app, POST `/control/settings` and POST `/control/ingest` are rejected and no Jenkins client is constructed, while GET `/control` still renders the seeded panels; the real app's behavior is unchanged. Offline suite stays green.


<a id="issue-106"></a>

### #106 — Add signature-level bulk attribution

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-08 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/106

> ## Intent
>
> When a shared outage breaks many tests with the same failure signature, acknowledgement can already be applied signature-wide ("Acknowledge all with this signature", `/signatures/{id}/acknowledge`) — but **attribution cannot**. Root cause, causing person, Jira ticket, and triage status still have to be applied via checkbox bulk-selection, bucket by capped bucket, even though every affected test shares one conclusion.
>
> Add an **"attribute all open episodes with this signature"** action so one root-cause conclusion propagates to every test whose current failure carries the same `FailureSignature`, in one submit.
>
> ## Scope
>
> - New POST action (mirroring the existing signature-acknowledge pattern in `src/uta/web/actions.py`) that applies causing person / reason / Jira ticket / triage status to **all open episodes** whose latest failure links to the given signature.
> - Per-episode provenance must follow the existing single-episode attribute semantics: `HUMAN_CORRECTED` where an AI suggestion existed (retaining `original_ai_cause`/`original_ai_reason`), `HUMAN_ENTERED` otherwise — so the AI-accuracy metric and KB provenance weighting stay correct.
> - The human conclusion attaches to the signature (existing KB behaviour) so it resurfaces on future matches.
> - UI: expose it from the test record's attribution form (e.g. an "apply to all N tests with this signature" option when the current failure's signature has more than one affected test), consistent with existing HTMX/PRG + flash + CSRF conventions.
> - Demo dataset: the shared-outage pair (`test_email_dispatch` / `test_sms_dispatch`) should showcase the surface per the demo rule in CLAUDE.md.
>
> ## Acceptance check
>
> - Attributing via the new signature-wide action stamps attribution + triage status on every open episode sharing the signature, with correct per-episode provenance (a mix of `HUMAN_CORRECTED` and `HUMAN_ENTERED` is covered by a unit test).
> - Episodes of tests whose failure does **not** share the signature are untouched.
> - Offline suite (`pytest -m "not live"`) covers the action; the live demo shows the control on a shared-outage test record.


<a id="issue-108"></a>

### #108 — Add dashboard deep links to alert emails

- **State:** Closed
- **Labels:** area:email, type:feat
- **Opened:** 2026-07-08 · **Closed:** 2026-07-08
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/108

> ## Intent
>
> The regression email lists each new failing test (test, owner, predicted cause, suggested contact) plus a Jenkins URL — but no link to the tool's own per-test record, so recipients have to open the dashboard and search by hand. Every listed test should deep-link to its `/tests/{identity_id}` record, and the email should link the run summary (`/runs/{build}`) too.
>
> ## Scope
>
> - New `APP_BASE_URL` setting (typed settings in `src/uta/config.py`, documented in `.env.example`, empty by default): the externally reachable base URL of the dashboard.
> - When `APP_BASE_URL` is set, the regression email renders each new-failing test as (or with) a link to its test record, and includes a link to the run summary page; the recovery notice links the run as well. When unset, emails render exactly as today (no broken/relative links).
> - Applies to the emails built in `src/uta/delivery/email.py` / sent by the poller. No change to when emails fire.
>
> ## Explicitly out of scope
>
> - A daily digest mode (separate proposal).
> - Any new notification channel.
>
> ## Acceptance check
>
> - With `APP_BASE_URL` set, a regression email for a run with new failures contains an absolute link to each failing test's record and to the run summary; unit-tested offline against the fake email sender.
> - With `APP_BASE_URL` unset (default), email content is link-free as before — covered by a test.
> - Offline suite (`pytest -m "not live"`) and lint stay green.


<a id="issue-112"></a>

### #112 — docs: add Auth/Keycloak config subsection + activation runbook to README; add a config-docs-maintainer check

- **State:** Closed
- **Labels:** area:docs, type:feat
- **Opened:** 2026-07-09 · **Closed:** 2026-07-16
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/112

> ## Intent
>
> ### 1. Close the auth documentation gap in the README
> The README **Configuration** section ([README.md](README.md#L109-L187)) has a per-subsystem env-var table for every subsystem **except auth** (Jenkins, Oracle, Postgres, Email, LLM, App tuning, Ingest windows, Compose-only all have one). Keycloak OIDC is fully implemented ([src/uta/web/auth.py](src/uta/web/auth.py), [config.py:47-57](src/uta/config.py#L47-L57)) and well-documented *inline* in [.env.example](.env.example) and *conceptually* in [docs/OVERVIEW.html](docs/OVERVIEW.html) — but the README's own config reference silently implies auth doesn't exist, and there is **no ordered "how to turn it on" runbook** anywhere; the steps are scattered across `.env.example` comments and OVERVIEW.
>
> Add an **"Auth / Keycloak (optional)"** subsection to the README Configuration section:
> - the missing env-var table (`AUTH_ENABLED`, `OIDC_SERVER_METADATA_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_POST_LOGOUT_REDIRECT`, `SESSION_SECRET`);
> - a short activation checklist stitching the steps together: provision a confidential client in the realm (auth-code + PKCE, direct-access-grants off) → register the `…/auth/callback` redirect URI and post-logout URI per environment → generate `SESSION_SECRET` → set the vars (secret via Vault) → flip `AUTH_ENABLED=true`;
> - note the fail-closed middleware model + public allowlist (`/health`, `/login`, `/auth/callback`, `/logout`, `/static/*`).
>
> Keep it to the README (no separate `CONFIGURATION.md` — the reference content already lives in `.env.example`; what's missing is discoverability and the ordered how-to).
>
> **Acceptance check:** the README Configuration section has an Auth/Keycloak table + activation checklist; a reader can enable Keycloak end-to-end from the README alone.
>
> ### 2. Add a "config-docs-maintainer" check, analogous to docs-overview-maintainer
> Today [CLAUDE.md](CLAUDE.md) mandates invoking the [`docs-overview-maintainer`](.claude/agents/docs-overview-maintainer.md) agent after any change that alters the app's parts/communications/workflows — but there is **no equivalent guardrail for configuration documentation**. New/renamed/removed settings (env vars in `config.py` / `.env.example`) can drift out of sync with the README Configuration tables with nothing prompting a check — exactly the gap that produced aspect (1).
>
> Introduce an analogous mechanism: an agent (e.g. `.claude/agents/config-docs-maintainer.md`) plus a CLAUDE.md convention requiring it to be invoked after any change touching the settings surface (`src/uta/config.py`, `.env.example`, or a feature's config gating). It should decide materiality and, if needed, update the README Configuration section (and `.env.example` inline docs) to match — otherwise report "no update needed".
>
> **Acceptance check:** a `config-docs-maintainer` agent definition exists and CLAUDE.md documents when to invoke it, mirroring the docs-overview-maintainer convention.
>
> ---
> Aspect (1) is shippable immediately; aspect (2) is a small follow-up that prevents the recurrence. They can land in one PR or two.


<a id="issue-114"></a>

### #114 — Redefine 'owner' as the test's main developer (SVN blame), not the ZEPHYR test-case author

- **State:** Closed
- **Labels:** area:ingest, type:feat
- **Opened:** 2026-07-09 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/114

> ## Intent
> The dashboard's **Owner** was silently taken over by the **ZEPHYR test-case author** (initials parsed from the failing test's `ZEPHYR TEST CASE INFO` block). That was never the intent. The original design (retired `PLAN.md`) defined ownership as *"the test's main developer from SVN history/blame, as a fallback contact."* Bring it back to that meaning.
>
> ## Change
> - **Owner = main developer**, derived from **`svn blame`** of the test's source file (modal line author). New external boundary behind an interface (`SvnBlameClient`) + offline fake, gated by `SVN_BLAME_ENABLED` (default off) exactly like the Oracle/LLM live paths — the offline gate, local dev and the demo touch no SVN.
> - The ZEPHYR author is **kept as ZEPHYR metadata** (`zephyr_owner`), no longer shown as "Owner". ZEPHYR test-case deep-links are unchanged.
> - Schema: rename `owner_initials` → `zephyr_owner` (identity + result), add `TestIdentity.main_developer`.
> - **Fix existing data**: the rename preserves the ZEPHYR data under its honest name; `main_developer` starts NULL and is populated by ingest (when the flag is on) and a one-shot `uta reattribute-owners` backfill.
> - Demo seeds synthetic main developers via a fake blame client so the live demo shows the new meaning.
>
> ## Acceptance
> - `pytest -m "not live"` green: parser yields `zephyr_owner`; blame XML tally + path-mapping + resolver unit-tested with a fake; the dashboard "Owner" column/filter/sort reflects `main_developer`; ZEPHYR owner surfaces as ZEPHYR info on the test record.
> - OVERVIEW.html reflects the SVN-blame boundary and the owner-vs-ZEPHYR distinction.


<a id="issue-115"></a>

### #115 — Make an unfinished unittest console-log stage mark the run incomplete

- **State:** Closed
- **Labels:** area:ingest, type:fix
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/115

> ## Intent
>
> Run completeness (`run.complete`) currently only checks the devUTs JUnit shards (`RunTiming.is_complete`, guarded by `FINISHED_STAGE_STATUSES` since #83). The unittest **console-log** stages (LXS, SMB Pricing/Transform, ITF Highlevel, Uniface) are ingested behind the same interface, and `find_unittest_stages` captures each stage's wfapi `status` into `LogStage.status` — but nothing reads it. A run whose devUTs shards are SUCCESS but whose e.g. `LXS - permanent` stage was ABORTED halfway parses a truncated log into a partial case list on a run still marked complete. Every previously-failing LXS test absent from the truncated log lands in `diff.removed` (phantom REMOVED transitions), the run becomes the next baseline, and the following healthy run reports those still-failing tests as regressions — a spurious alert email. This is the #83 failure mode, left unguarded for the second source.
>
> Fix: when unittest-log ingestion is enabled, a selected console-log stage (matched by `find_unittest_stages` against the suite allowlist) whose status is not in `FINISHED_STAGE_STATUSES` must make the run incomplete, mirroring the devUTs shard guard. A suite stage entirely absent from the wfapi payload must **not** affect completeness (job configuration varies over history). The truncated stage's results are still parsed and stored — analysis/baseline/alerting are gated on `run.complete`, exactly as for incomplete devUTs runs today.
>
> ## Acceptance check
>
> Offline unit tests pin: both devUTs shards SUCCESS + an ABORTED (or NOT_EXECUTED) selected console-log stage ⇒ `run.complete` is False; all selected stages SUCCESS ⇒ True (existing behavior); a suite stage absent from the wfapi payload ⇒ completeness unaffected. `ruff check .` and `pytest -m "not live"` green.


<a id="issue-116"></a>

### #116 — Fix stale FailureSignature aggregates when a re-ingest orphans a signature

- **State:** Closed
- **Labels:** area:kb, type:fix
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/116

> ## Intent
>
> Re-ingesting a build whose failure content changed leaves `FailureSignature` aggregates permanently stale. `ingest_build` clears the run's old results, then `record_signatures_for_run` recomputes aggregates only for the signatures linked by the run's **new** failing rows. A signature that lost links in the delete but gained none (the test now passes, or its error text changed so it hashes to a different signature) is never recomputed — despite `_recompute_aggregates_bulk`'s docstring claiming orphans get reset to a zero/empty aggregate. Result: `occurrence_count` overcounts and `last_seen_run_id` can point at a run that no longer contains the failure — wrong on the KB dashboard ("seen N×", last-seen deep link) and fed as evidence into the LLM prompt.
>
> Fix: capture the set of signature ids linked to the run's results **before** the delete, and recompute aggregates for the union of old and new affected signatures, so orphaned ones actually get the documented reset.
>
> Same-root inconsistency to fix in the same recompute: the grouped query takes `min/max(Run.started_at)` for first/last_seen_at but `min/max(Run.id)` for first/last_seen_run_id, assuming id order == chronological order — false after a historical re-ingest (an older build ingested later gets a higher run id). The run ids must be those of the rows with min/max `started_at`.
>
> ## Acceptance check
>
> With builds #104 and #105 both failing test `t` (same signature, both tracks → `occurrence_count == 4`), re-ingesting #105 with `t` now passing leaves the signature with `occurrence_count == 2` and `last_seen_run_id` pointing at run #104 (the newest run that actually contains the failure). A signature losing **all** links gets the zero/empty aggregate reset. `first/last_seen_run_id` always belong to the runs with min/max `started_at`, not min/max run id. Covered by offline unit tests; existing identical-content re-ingest behaviour unchanged; `pytest -m "not live"` green.


<a id="issue-117"></a>

### #117 — Close the open episode when a REMOVED test reappears passing

- **State:** Closed
- **Labels:** area:analysis, type:fix
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/117

> ## Intent
>
> A test whose lifecycle went FAILING → REMOVED (absent from a complete run, episode deliberately left open — "disappeared ≠ fixed") gets **stuck as REMOVED forever** when it later reappears **passing**.
>
> Root cause: `compute_diff` (`src/uta/analyze/baseline.py`) only emits `newly_fixed` for identities that were FAILED *in the baseline*. A REMOVED test is absent from the baseline, so its passing reappearance lands in **no diff bucket**, and `apply_run` (`src/uta/analyze/lifecycle.py`) has no REMOVED → FIXED edge. The triage queue's "Still failing (Removed)" bucket then shows a healthy, passing test as a removed failure indefinitely, and the episode's `fixed_in_run_id` is never set — contradicting the lifecycle module contract ("FIXED = the test ran and passed again") and the `FailureEpisode.fixed_in_run_id` model comment.
>
> Fix: in `apply_run`, reconcile identities that are PASSED in the current run while their failure episode is still open — treat them as newly fixed (close the episode, set `fixed_in_run_id`, transition to FIXED). The intended boundary stays intact: a test reappearing as **failing** continues its same open episode (no new episode, no acknowledgement clearing).
>
> ## Acceptance check
>
> Unit test in `tests/unit/test_lifecycle.py`: run 1 test fails → run 2 test absent (state REMOVED, episode open) → run 3 test passes ⇒ lifecycle state FIXED, `episode.is_open` False, `episode.fixed_in_run_id` == run 3's id. Existing `test_removed_keeps_episode_open` semantics unchanged, and a reappearance that fails still extends the same open episode. `pytest -m "not live"` green.


<a id="issue-118"></a>

### #118 — Send the recovery notice only on the red-to-green transition, not on every green run

- **State:** Closed
- **Labels:** area:email, type:fix
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/118

> **Intent.** With `EMAIL_RECOVERY_NOTICE=true`, `build_regression_report` currently returns the "UT back to green" message for **every** green run — the gate (`run.total_failed == 0 and not diff.still_failing`) never checks that anything actually transitioned. On a healthy suite the poller therefore emails "UT back to green … Newly fixed this run: 0" for every complete run, violating the module contract that silence means "no worse than before". The notice should fire only when the baseline had at least one failing test that this run resolved (fixed **or** removed) — i.e. on the actual red→green transition.
>
> **Acceptance check.** Offline suite green, with new unit tests in `tests/unit/test_email.py` proving:
> - green run after an already-green baseline, `recovery_notice=True` → `None` (no email);
> - red→green transition still produces the "back to green" message (existing test);
> - first-ever run (no baseline), all green → `None`.


<a id="issue-119"></a>

### #119 — Stop stringifying NULL Oracle V_TRACKING columns to the literal "None"

- **State:** Closed
- **Labels:** area:ingest, type:fix
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/119

> **Intent.** In `_row_to_change` (`src/uta/refdb/oracle.py`) the row dict is built from `cursor.description`, so every selected column key always exists — the `.get("PKLST", "")` / `.get("LXTABLECODE", "")` / `.get("TYPE", "")` defaults are dead code. A SQL NULL arrives as Python `None`, so `pk=str(row.get("PKLST", ""))` persists the literal string `"None"` as the candidate's pk (rendered as `pk None` in the dashboard and in the LLM prompt), and a NULL `LXTABLECODE`/`TYPE` would flow `None` into `DataChange` fields typed as non-optional `str`. Normalize NULLs explicitly: NULL `PKLST` / `LXTABLECODE` / `TYPE` become `""` (matching the dataclass's non-optional `str` fields), following the existing `pk_ref` pattern (`None if row.get("PKLSTREF") is None else str(row["PKLSTREF"])`) for the optional fields.
>
> **Acceptance check.** A unit test feeding `_row_to_change` a row with `PKLST`, `LXTABLECODE`, and `TYPE` set to `None` yields `pk == ""`, `entity == ""`, `change_type == ""` — no `"None"` strings anywhere in the resulting `DataChange` — while rows with normal values are unchanged. `pytest -m "not live"` and `ruff check .` green.


<a id="issue-120"></a>

### #120 — Wire SMTP_USER/SMTP_PASSWORD into SmtpEmailSender (STARTTLS + login)

- **State:** Closed
- **Labels:** area:email, type:fix
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/120

> ## Intent
>
> `Settings` accepts `SMTP_USER` / `SMTP_PASSWORD` (documented in `.env.example`), but they are dead config: `build_email_sender` constructs `SmtpEmailSender(host, port, sender)` only, and `SmtpEmailSender.send` never calls `starttls()` or `login()`. On a relay that requires authentication every send raises — and since the alert path is deliberately best-effort (issue #81 swallows send failures), alerts silently never arrive.
>
> Fix: pass the optional credentials through `build_email_sender` into `SmtpEmailSender`. When a user is configured, negotiate STARTTLS and `login()` before `send_message`. A new `SMTP_STARTTLS` setting controls TLS explicitly; left unset it defaults to on exactly when credentials are configured. With no credentials configured, behavior is byte-identical to today (plain unauthenticated send). The password is never logged.
>
> ## Acceptance check
>
> With a monkeypatched `smtplib.SMTP` recording calls:
> - credentials configured ⇒ `starttls()` and `login(user, password)` are called, in that order, before `send_message`;
> - credentials absent ⇒ neither is called (unchanged behavior);
> - `SMTP_STARTTLS` explicitly set overrides the credential-derived default;
> - `build_email_sender` passes host/port/from/user/password/starttls from `Settings` through.
>
> `pytest -m "not live"` and `ruff check .` green.


<a id="issue-121"></a>

### #121 — Make send_ops_alert best-effort so SMTP outages can't break /health or erase the poller tick record

- **State:** Closed
- **Labels:** area:infra, type:fix
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/121

> ## Intent
>
> `send_ops_alert` (`src/uta/delivery/email.py`) calls `sender.send(message)` with no exception guard, unlike its sibling `send_alert`, which deliberately swallows send failures as best-effort. Two consequences when SMTP is unreachable (a correlated infra outage — exactly when an external monitor probes):
>
> - **`/health` raises 500 instead of the designed 503 "degraded" payload.** In `check_health` (`src/uta/control/health.py`) the stale-poller alert send sits outside the DB try/except and the `/health` route has no guard, so a stale poller + unreachable SMTP host makes the endpoint raise. And because `stale_alerted_at` latches only after a successful send, **every** probe re-dials SMTP, hanging the endpoint on connect timeouts.
> - **The poller's tick record is erased.** `send_ops_alert` is called inside the per-build except block in `poll_once` (quarantine / 404-skip paths). If SMTP raises there, the exception escapes to `poll_tick`'s generic handler, which stamps the heartbeat with `processed=[]` — losing the record of builds the tick actually ingested (they committed; only the reporting is lost) and skipping the retention pass.
>
> Fix: make `send_ops_alert` best-effort like `send_alert` — catch send failures, log a warning, return `None` so callers see non-delivery (`check_health` keeps its "latch only on success" semantics and a later successful send still alerts). Also put a connect timeout on the `smtplib.SMTP(...)` dial so a black-holed SMTP host can't hang `/health` for minutes.
>
> ## Acceptance check
>
> Offline unit tests (raising `EmailSender` fakes, no real SMTP) pin:
> - a sender that raises ⇒ `send_ops_alert` returns `None` without raising;
> - `check_health` with a raising sender ⇒ returns the stale `HealthReport` (ok `False`, poller `"stale"`) without raising, and `stale_alerted_at` stays unlatched so a later successful send still alerts;
> - poller: a sender that raises during the quarantine/skip ops alert ⇒ the tick still records the successfully processed builds on the heartbeat.
>
> `ruff check .` and `pytest -m "not live"` fully green.


<a id="issue-122"></a>

### #122 — Make demo control-state seeding idempotent so re-running `uta seed-demo` doesn't crash

- **State:** Closed
- **Labels:** area:infra, type:fix
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/122

> ## Intent
>
> `seed_demo_data` documents itself as "idempotent-ish" — re-seeding the same store re-ingests each build (the ingest pipeline *is* idempotent per build) and re-applies the triage actions. But `_seed_control_state` (`src/uta/demo/seed.py`) unconditionally `session.add()`s rows with fixed primary keys — `PollerHeartbeat(id=1)`, `BuildQuarantine(build_number=builds[0]-2)`, and the two `SettingOverride` rows (`kb_top_k`, `ui_row_limit`) — so a second seed of the same store dies with a duplicate-PK `IntegrityError` at the final commit, and the two auto-PK `IngestJob` demo rows would duplicate on every re-seed.
>
> This is reachable via `uta seed-demo`, which explicitly targets a persistent (e.g. Postgres) demo instance where re-running the command to refresh the dataset anchor is the natural maintenance action: it re-ingests all builds fine, then crashes on the control-state commit.
>
> Fix: make `_seed_control_state` idempotent — merge/upsert the fixed-PK rows and remove the previously seeded demo `IngestJob` rows (identifiable by `requested_by == "demo-user"`) before inserting, so a re-seed converges to the same state with no duplicates. No change to what values are seeded.
>
> ## Acceptance check
>
> Seeding the same store twice raises no exception and converges: exactly one `PollerHeartbeat` row, one `BuildQuarantine` row, two `SettingOverride` rows, and two demo `IngestJob` rows, with values identical to a fresh single seed — covered by an offline test.


<a id="issue-123"></a>

### #123 — Fix navbar test search returning no results when ui_row_limit is 0

- **State:** Closed
- **Labels:** area:dashboard, type:fix
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/123

> ## Intent
>
> `ui_row_limit = 0` is the documented "disable the cap" value (tunable minimum 0, help text "0 disables the cap"), and both `_cap` and `_page_window` in `src/uta/web/views.py` special-case `limit <= 0` accordingly. But `test_search` (the navbar "jump to test" search) passes the value straight into `.limit(limit)`, emitting `LIMIT 0` — so with the override set to 0, every query answers "No tests match" and the unique-match redirect never fires.
>
> Fix: skip applying `.limit()` in `test_search` when `limit <= 0`, consistent with `_cap` / `_page_window` semantics.
>
> ## Acceptance check
>
> - `test_search(session, query, limit=0)` returns **all** matching identities (unit test added).
> - A positive `limit` still caps the result count (unit test added).
> - An empty/whitespace query still returns `[]`.
> - Offline gate green: `pytest -m "not live"` and `ruff check .`.


<a id="issue-124"></a>

### #124 — Require same-track consistency for the shard_correlated flakiness flag

- **State:** Closed
- **Labels:** area:flakiness, type:fix
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/124

> **Intent.** `compute_stats` in `src/uta/analyze/flakiness.py` sets `shard_correlated` when every failing run in the window failed in exactly one track while the other passed — but it never checks that it is the **same** track across runs. Failures alternating between `permanent` (run A) and `permanent_py39` (run B) — the textbook non-shard-correlated flake — still set the flag, contradicting the documented semantic ("do the failures cluster in ONE track"; "a consistent single-track failure is a strong infra/flaky tell"). The flag feeds the flaky leaderboard as an infra tell, so this misdirects triage.
>
> **Fix.** Keep the existing per-run qualification (failed, other track passed, exactly one failing track) and additionally require that the union of `fail_tracks` across those qualifying runs is exactly one track.
>
> **Acceptance check.** Unit tests in `tests/unit/test_flakiness.py`: failures alternating between the two tracks across runs ⇒ `shard_correlated is False`; consistent single-track failures ⇒ `True` (existing test stays green); a single failing run in one track ⇒ `True`. `pytest -m "not live"` fully green.


<a id="issue-125"></a>

### #125 — Keep the demo's /health at 200 for the process's whole lifetime (seeded heartbeat goes stale)

- **State:** Closed
- **Labels:** area:infra, type:fix
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/125

> ## Intent
>
> The demo seeds a poller heartbeat (`_seed_control_state`, `src/uta/demo/seed.py`) so the `/control` panel renders populated — but the demo runs no poller, so the stamp never refreshes. `check_health` treats a *missing* heartbeat as the healthy web-only topology (`poller: "never"` → 200) but a *present stale* one as a fault → 503. With default settings (300 s × 5 intervals = 1500 s) the demo's `/health` flips to 503 "poller stale" once the process is ~21 minutes old. `render.yaml` sets `healthCheckPath: /health`, so Render marks the service unhealthy and restarts it — wiping the ephemeral in-memory store (and any visitor's triage edits) mid-session.
>
> Fix demo-side: have the demo app re-stamp the seeded heartbeat's `last_poll_at`/`last_success_at` whenever `/health` is probed, so the demo stays healthy indefinitely while `/control` still shows a populated, fresh heartbeat. Staleness detection for real deployments is untouched.
>
> ## Acceptance check
>
> - Offline test: with the seeded heartbeat aged far beyond the staleness window (simulating a long-lived demo process), the demo app's `/health` still returns 200 with `poller: "ok"`, and the `/control` panel still renders a populated heartbeat.
> - `check_health` behavior for real (non-demo) deployments unchanged; existing staleness tests stay green.


<a id="issue-126"></a>

### #126 — Rank and label KB similar cases by the strongest of both provenance columns

- **State:** Closed
- **Labels:** area:kb, type:fix
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/126

> **Intent.** KB retrieval currently ranks and labels similar cases by `reason_provenance` only: `_best_attribution`'s max key and `_to_case`'s `provenance` / `provenance_weight` in `src/uta/kb/retrieval.py` read just `a.reason_provenance`. A triager can set only `causing_person` (cause_provenance becomes HUMAN_ENTERED/HUMAN_CORRECTED while reason_provenance stays AI_UNCONFIRMED); such an attribution passes the candidate filter but gets weight 0 — ranking below an AI-confirmed reason on a near-equal text match and rendering with no `[provenance]` tag in the LLM prompt. This contradicts the module contract that confirmed/corrected knowledge ranks above unvalidated AI guesses. `strongest_provenance_weight` in the same file already maxes both columns; ranking and labeling should do the same.
>
> **Fix.** Use the strongest of the two provenance columns (cause / reason) for `_best_attribution`'s ranking key and for `_to_case`'s weight and provenance label, so a human-entered cause ranks and tags as human knowledge.
>
> **Acceptance check.** A unit test where an attribution with `cause_provenance=HUMAN_ENTERED` + `reason_provenance=AI_UNCONFIRMED` ranks above an AI_UNCONFIRMED-only attribution at comparable text similarity, and its `SimilarCase` carries the human provenance label; existing ranking tests stay green; `pytest -m "not live"` and ruff pass.


<a id="issue-127"></a>

### #127 — Make /health report a never-succeeded poller stale instead of ok forever

- **State:** Closed
- **Labels:** area:infra, type:fix
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/127

> ## Intent
>
> `check_health` uses `hb.last_success_at or hb.last_poll_at` as the freshness reference. `last_poll_at` moves on **every** tick (success or failure), so a poller that has *never* had a successful tick — e.g. a deployment misconfigured from day one (bad Jenkins URL, wrong Oracle password) — keeps `last_success_at = NULL` with a forever-fresh `last_poll_at`, and `/health` reports `poller: "ok"` indefinitely. That contradicts the module's own contract ("a poller that ticks but keeps failing goes stale too"). The `last_poll_at` fallback was meant only for the upgrade window (a heartbeat row predating the `last_success_at` column, migration `e5f6a7b8c9d0`), but the code cannot distinguish "upgrade window" from "never succeeded".
>
> Fix: when `last_success_at` is NULL, use the heartbeat row's `created_at` as the freshness reference instead of `last_poll_at`. That grants the same one-off grace window (`poller_stale_after_intervals × poll_interval_seconds`) to a fresh migration and a fresh deployment alike, then flips to stale once the window passes without any success. Missing heartbeat row still reports `poller: "never"` (200) and healthy pollers are unaffected.
>
> ## Acceptance check
>
> - Heartbeat row with `last_success_at = NULL` and `created_at` older than the staleness window ⇒ `/health` degraded, `poller: "stale"`.
> - Heartbeat row with `last_success_at = NULL` and fresh `created_at` ⇒ still `ok` (grace window).
> - No heartbeat row ⇒ `poller: "never"`, ok (unchanged).
> - `pytest -m "not live"` green.


<a id="issue-132"></a>

### #132 — Make the triage "Load all N Tests" expand link preserve active filters and sort

- **State:** Closed
- **Labels:** area:dashboard, type:fix
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/132

> The `more_hint` macro (`src/uta/web/templates/_macros.html`) emits `href="?expand=…#section"`, which replaces the **entire** query string. On a filtered triage view (e.g. `/?owner=KP`) the promised count N is post-filter, but clicking "Load all N Tests" drops the owner/suite/track/cause/triage_status/flaky filters **and** the sort — landing on the full unfiltered, default-sorted bucket (possibly thousands of rows, the very responsiveness problem the issue #19 cap addressed), with the filter silently gone. This breaks the "state stays entirely in the URL" contract the filter chips and header sort links (issue #77) maintain.
>
> **Fix:** build the expand links in the view layer (same `_triage_url` machinery as the chips/sort links) so they keep every active filter and the sort, replace only `expand` (merging with already-expanded sections), and still jump to the `#section` anchor.
>
> **Acceptance check:** rendering `/?owner=X` with a capped section yields a "Load all" link containing both `owner=X` and `expand=<section>`; following that link returns the *filtered* bucket rendered in full. Covered by offline unit tests (`pytest -m "not live"` green).


<a id="issue-143"></a>

### #143 — Keep your place: back-links on detail pages + episode anchors after actions

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/143

> ## Intent
>
> Two "never lose your place" navigation gaps (UX audit findings N1 + N4):
>
> - **N1 — detail pages are dead ends.** The test record and run detail pages have no back-link; the navbar "Triage" link hard-codes `/`, so clicking into a record from a filtered/sorted triage queue discards the queue's carefully URL-encoded filter state.
> - **N4 — episode actions dump you at the top of the page.** Episode cards on the test record have no `id` anchors, and every episode-scoped POST (Save attribution, Confirm AI suggestion, Apply-to-all) redirects via the bare referer, so after each edit the user must scroll back and re-find the episode.
>
> Plan:
> 1. Breadcrumb/back-link row on the drill-down pages: test record ("← Triage queue", preserving the referring filtered queue URL via a `return` query param on the record links) and run detail ("← Job runs"). Sanitized server-side: only same-origin relative paths are accepted; anything else falls back to the plain list URL.
> 2. `id="episode-N"` anchors on each episode card; episode-scoped POST actions redirect back with `#episode-N` appended (passed explicitly via a hidden form field, since fragments never reach the server).
> 3. The PRG `back()` redirect builder reduces the referer to its same-origin path + query (never an absolute external URL).
>
> ## Acceptance check
>
> - From `/?owner=AB&sort=name`, opening a record and clicking "← Triage queue" returns to exactly that filtered URL; without context the link falls back to `/` (and run detail links back to `/runs`).
> - `?return=https://evil.example/x` (and `//host`, backslash variants) on a record URL falls back to `/` — no external link/redirect from user-controllable input.
> - Saving an episode's attribution / confirming an AI suggestion redirects to the record with `#episode-N`, landing the browser at the edited episode.
> - Offline gate green (`pytest -m "not live"`), incl. new tests for the fragment redirect and the same-origin sanitization; ruff clean.


<a id="issue-144"></a>

### #144 — Make pass/fail status readable without color and label timestamps as UTC

- **State:** Closed
- **Labels:** area:dashboard, type:fix
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/144

> Two dashboard UX findings from an accessibility/clarity audit:
>
> **V1 — status is conveyed by hue alone.** The job-runs table colors bare counts red/green (Passed / Failed / Regressions / Newly fixed via the `.PASSED` / `.FAILED` / `.SKIPPED` classes), and the per-test sparkline distinguishes failed vs passed bars purely by fill color. ~8% of male users can't reliably distinguish red from green, so the signal is invisible to them.
>
> **D5 — timestamps are silently ambiguous.** The `ts` filter renders bare `2026-06-29 16:15:46` with no timezone indication anywhere on the dashboard. All stored instants are UTC, but users are in Luxembourg (UTC+1/+2), so readers naturally misread them as local wall-clock.
>
> Intent:
> - Pair every color-coded status count with a non-color cue (small ✓ / ✕ / ○ glyph) on the runs-table cells; places that already spell out the status word (PASSED/FAILED text) need no extra decoration.
> - Give the sparkline a second, non-hue channel (failed bars full-height, passed bars shorter) while keeping the existing colors.
> - Make `format_ts` append an explicit ` UTC` label and carry the full ISO-8601 timestamp (with offset) in a hover `title` — centralized in the one filter so every render site picks it up.
>
> Acceptance check:
> - `/runs` shows glyph-prefixed pass/fail/regression/newly-fixed counts; the cue survives with CSS colors ignored.
> - Sparkline failed and passed bars differ in height, not just fill.
> - Every `|ts` render ends in ` UTC` and hovers to the ISO timestamp with offset; `|reltime` hover titles carry the UTC label too.
> - Unit tests cover the `format_ts` suffix/title and assert the non-color cue in rendered HTML; offline suite green.


<a id="issue-145"></a>

### #145 — Surface one-line error snippets in the triage queue and tame long traces on the test record

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/145

> ## Intent
>
> Today the triage queue's **New** and **Still failing** tables show test / owner / first-failed / predicted-cause — but never the error text, so every triage decision requires opening the per-test record. And on the record, `error_details` / `error_stack_trace` render in full: a long trace produces an unbounded `<pre>` with no truncation and no copy affordance.
>
> - **Triage queue:** add a muted one-line error snippet under the test name in the New and Still-failing tables — the traceback's closing exception line (`AssertionError: …`; JUnit `errorDetails` is usually the constant "test failure", so the exception line is the informative part), falling back to the details field, truncated to a sane length. Carried through the existing batched `_failure_infos` query — no N+1; the page stays O(1) queries in the number of rows.
> - **Test record:** clamp long error details / stack traces to ~15 lines with a "Show full trace" expand/collapse toggle, and add a copy-to-clipboard button. Vanilla JS, vendored (no CDN), progressive enhancement — without JS the full trace still renders.
> - **Demo:** the seeded dataset should show snippets on the queue and include at least one >15-line trace exercising the clamp/expand path on the record.
>
> ## Acceptance check
>
> - `triage_queue` rows carry `error_type` / `error_snippet`; both tables render the snippet when error text exists; the triage query-count guard still passes unchanged.
> - A test record with a >15-line trace renders it clamped behind a "Show full trace" toggle and offers "Copy trace"; short traces show no toggle.
> - Live demo: snippets visible in the queue; one record demonstrates the clamped trace.
> - Offline gate green (`pytest -m "not live"`).


<a id="issue-150"></a>

### #150 — Make triage actions trustworthy: ack anchors, truthful bulk flash, disable-on-submit, live toast flashes

- **State:** Closed
- **Labels:** area:dashboard, type:fix
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/150

> ## Intent
> Four small, related trust/feedback defects in the dashboard's action loop (from a 5-lens UX review):
>
> 1. **Acknowledge loses your place.** The per-row ack routes (`/tests/{id}/acknowledge`, `/signatures/{id}/acknowledge`, bulk ack) call `back(request)` with no anchor, so every acknowledge reloads and scrolls to the top of the queue. The `back(request, anchor=...)` mechanism already exists and is used by `attribute_signature` (hidden `anchor` form field) — wire the same pattern into the ack routes so the redirect lands back at the section/row.
> 2. **False success on no-op bulk attribution.** `bulk_set_attribution` counts every episode for which `set_attribution` returns an attr — but `set_attribution` returns the attr even when nothing was written (`touched` false). An all-blank "Apply to selected" flashes "Updated 5 selected tests" having written nothing. Count only actually-touched episodes and flash an error ("Nothing to apply — fill in a status, person or reason") when all fields are empty.
> 3. **No pending state on any submit button.** Double-click on a slow request (signature-wide bulk is genuinely slow) re-POSTs and re-stamps `validated_at`/actor. Add a tiny global disable-on-submit script (disable the submitter, swap label to a busy state) applied to all forms.
> 4. **Flash confirmations render off-screen and silently.** Flashes render at the top of `<main>` with no `aria-live`, while episode actions (and, after item 1, ack actions) deliberately anchor-scroll away from them. Render flashes as a fixed-position toast (`role="status"`, `aria-live="polite"`, auto-dismiss with pause-on-hover, keep the manual dismiss).
>
> ## Acceptance
> - Acknowledge (single, signature, bulk) redirects back to the originating section anchor; existing PRG/flash behaviour otherwise unchanged.
> - All-blank bulk attribution flashes an error and reports 0 updates; partial input reports the true touched count.
> - Every form disables its submitter on submit; no double-POST.
> - Flash is announced to screen readers and visible regardless of scroll position.
> - `pytest -m "not live"` green with new unit coverage for the bulk-count fix and ack-anchor redirects.


<a id="issue-151"></a>

### #151 — Finish URL-state coherence: keep ?expand= across filter/sort changes; cap run-diff lists with counts

- **State:** Closed
- **Labels:** area:dashboard, type:fix
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/151

> ## Intent
> Two remaining halves of the URL-state/cap-expand work started in #132/#142:
>
> 1. **Filters and sort still drop `?expand=`.** #142 made the "Load all N Tests" links preserve filters+sort, but the reverse seam is still broken: the triage filter form's only hidden state field is `sort`, and the chip-remove and sort-header links call `triage_url(remaining, sort)` without passing the current expanded set — so applying/removing a filter or re-sorting collapses any expanded section. `triage_url()` already accepts an `expand` parameter; thread the current expanded set through the filter form (hidden field), chips, and sort links.
> 2. **Run-page diff lists are unbounded comma blobs with no counts.** `run.html`'s `diff_list` macro renders every regression / newly-fixed / still-failing / removed test as one comma-separated stream of links with no count in the row header — a run with 300 regressions produces an unscannable wall exactly on the worst nights. Add counts to each diff row header ("Regressions (12)"), cap each list (~20) with the same `?expand=` + view-built-URL pattern the triage queue now uses, and keep the `#diff` anchor on expand links.
>
> ## Acceptance
> - On a filtered+expanded triage view, changing any filter, removing a chip, or re-sorting keeps the expanded sections (and vice versa — verified by unit tests on the URL builders and a template render test).
> - Run diff rows show counts; lists longer than the cap are truncated with a working "Show all N" link that preserves the rest of the query string.
> - Demo dataset still exercises the visible surfaces (a diff bucket exceeding the cap is worth seeding only if it doesn't bloat the dataset — judgement per CLAUDE.md).
> - `pytest -m "not live"` green with new coverage.


<a id="issue-152"></a>

### #152 — Show the blast radius on "Ack all w/ signature (N)" before the click

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/152

> ## Intent
> "Ack all w/ signature" is the queue's flagship one-click action and it commits blind: the user learns it hit 34 tests only from the *after-the-fact* flash — and there is no un-acknowledge route in the web layer, so a mis-scoped signature-wide ack is irreversible. Surface the count in the button label **before** the click: "Ack all w/ signature **(34)**", and render the signature button only when the count is > 1 (a count of 1 adds nothing over the plain Acknowledge button).
>
> Implementation note (priced in review): signatures are per-test — two tests hitting the same underlying error get **distinct** `FailureSignature` rows (see `_error_key` docstring in `web/actions.py`), so this is **not** a `GROUP BY signature_id`. The count requires loading the current signatures' `normalized_text` for the New bucket's rows and grouping by `_error_key()` in Python — the identical computation `acknowledge_by_signature` performs at commit time, run earlier, in one batched pass through the queue projection (no per-row N+1). Row *clustering* by signature is explicitly out of scope (deferred; it interacts with the cap/sort/expand machinery).
>
> ## Acceptance
> - Each "Ack all w/ signature" button shows the number of currently-failing tests sharing that error key; the number matches what the action then acknowledges.
> - Button hidden (or plain ack only) when the count is 1.
> - No N+1: the counts come from one batched query + one Python pass in the queue projection (offline perf-sane at 100-row bucket scale).
> - Demo dataset seeds a multi-test shared signature so the live demo shows the count (verify the existing two-test incident pair surfaces it).
> - `pytest -m "not live"` green with unit coverage for the grouping/count.


<a id="issue-157"></a>

### #157 — Turn inert facts into pivots: linkify owner/suite/cause, clickable failed-count, cross-referring search empty states

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/157

> ## Intent
> Three href-only changes that turn dead-end text into navigation, using routes that already exist (from the 5-lens UX review; the "pivot bundle" runner-up of the review debate):
>
> 1. **Linkify owner / suite / predicted-cause values.** The triage queue's filter URLs are fully bookmarkable (`/?owner=KP`, `/?cause=CODE_CHANGE`, built by `views.triage_url`), yet everywhere these values appear — triage rows, run results, flaky leaderboard, search results — they are plain text. A team lead seeing "KP" against 5 failures should click the value to get the pre-filtered queue instead of retyping it into the filter form.
> 2. **Make the run header's failed count actionable.** The run page header shows "N failed" as inert text while `?failures_only=1` already exists as a GET param. Link the failed total to `/runs/{build}?failures_only=1#results`, and reflect the active filter in the Results heading. Optionally auto-submit the failures-only checkbox (drop the two-step tick+Apply).
> 3. **Cross-refer the two search systems' empty states.** The navbar box matches only test names; error-text search lives at `/kb`. Pasting an exception line into the navbar yields "No tests match …" with no hint that `/kb?q=` exists (and vice versa). Each empty state should link the same query into the other search.
>
> ## Acceptance
> - Owner/suite/cause values render as links to the filtered triage queue wherever they appear; links carry only filters (no stray state).
> - The run header's failed count links to the failures-only results view; heading reflects the active filter.
> - `/search` empty state offers "Search the knowledge base for this text"; `/kb` empty state offers the test-name search fallback.
> - No new routes, JS, or queries; template + URL-builder changes only. `pytest -m "not live"` green with render tests for the new hrefs.


<a id="issue-158"></a>

### #158 — Cluster same-signature rows in the New bucket (T5 follow-up to #152)

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/158

> ## Intent
> #152 put the blast-radius count on "Ack all w/ signature (N)". The second half of that review finding: after a shared breakage, the New bucket still shows N visually indistinguishable rows for one root cause. Group adjacent same-`_error_key` rows so a 34-row wall reads as one incident — e.g. sort same-key rows together within the bucket's existing order and render the shared error line once as a subtle group header, with the signature-wide ack button at group level.
>
> Design questions the review flagged as real (decide, don't improvise):
> - **Interaction with the 100-row cap:** a group must not be silently split by the cap (either cap at group boundaries or show "group continues — Load all").
> - **Interaction with per-column sort (issue #77):** clustering reorders rows; define whether sort applies within groups, disables clustering, or clustering only applies under the default (age) sort.
> - **Interaction with `?expand=` and filters:** counts stay pre-filter (the action ignores filters — #152's semantics), but grouping should operate on the rendered rows.
> - Presentational only: no route or model changes; reuse the `signature_ack_count`/`_error_key` plumbing #152 added.
>
> ## Acceptance
> - Two seeded tests sharing an error key render as one visual group with a single group-level "Ack all w/ signature (N)"; singleton rows are unchanged.
> - Cap/sort/expand behaviors are defined and tested (no group silently truncated mid-group without a cue).
> - Demo dataset's shared-signature pair (SMTP outage) shows the grouping on the live demo.
> - `pytest -m "not live"` green with render + ordering tests.


<a id="issue-159"></a>

### #159 — Render the classification evidence on the test record ("Why this prediction")

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/159

> ## Intent
> The test-record page asks the user to "Confirm AI suggestion" — a consequential attribution action — while showing only a bare `confidence 0.85` badge. The supporting evidence is already computed and shipped to the template context (`views.py` assembles the classification's evidence JSON for this page, ~613-637 pre-#153 numbering) but **no template renders it** — `grep evidence templates/` has zero hits. Trust-and-verify is the core interaction of the page and the justification is silently dropped.
>
> Render the evidence as a collapsed `<details>` ("Why this prediction") under the predicted-cause line — a small definition list of the evidence keys (e.g. relevance-score gap, KB provenance) — so the Confirm button sits next to its justification. Keep it collapsed by default; the hover-title summary can stay. If some evidence keys turn out to be internal-only noise, whitelist the user-meaningful ones rather than dumping raw JSON.
>
> ## Acceptance
> - An episode with a classification shows a collapsed "Why this prediction" block whose content comes from the stored evidence; episodes without evidence render no empty shell.
> - No new queries — the data is already in the view context.
> - Demo dataset: at least one seeded episode carries a populated evidence payload so the live demo shows the block (per the CLAUDE.md demo rule).
> - `pytest -m "not live"` green with a render test (evidence present/absent).


<a id="issue-161"></a>

### #161 — Add in-app end-user documentation (Help page)

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-12 · **Closed:** 2026-07-12
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/161

> End users have no in-app guide to the daily triage workflow, what each status/badge means, what the LLM contributes versus the deterministic classifier, or how to act on (confirm/correct) an AI suggestion. OVERVIEW.html covers architecture for contributors, but there's nothing end-user-facing inside the running dashboard.
>
> **Acceptance check:** a new `/help` page, linked from the navbar, explains the triage workflow (buckets, acknowledge, bulk/signature actions), the full status/badge glossary (lifecycle, triage status, predicted cause + confidence, result statuses, misc badges), how the LLM hypothesis is produced and how it differs from the deterministic classifier, how Confirm/correct map to provenance tiers and feed the AI-suggestion-accuracy metric, the knowledge base, a tour of the other dashboard pages, and the external deep links.


<a id="issue-166"></a>

### #166 — Owner blame is a no-op in production: svn CLI missing from the Docker image

- **State:** Closed
- **Labels:** area:infra, type:fix
- **Opened:** 2026-07-13 · **Closed:** 2026-07-13
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/166

> ## Problem
> `uta reattribute-owners` (and the incremental ingest owner-resolution from #114) resolve **0** owners in the deployed stack. Root cause: `SvnCliBlameClient` shells out to the `svn` CLI, but the production image (`python:3.12-slim`, Dockerfile) installs only `tzdata` — **no `subversion`**. A missing binary is caught as `None` (blame must never fail ingest), so every blame silently returns `None`.
>
> Confirmed against production: 13,011 identities, 57,739 results with a source path, `SVN_BLAME_ENABLED=true`, base URL reachable and blame verified working from an environment that *does* have `svn` — yet 0 owners resolved.
>
> ## Fix
> Install `subversion` in the Docker image (alongside `tzdata`).
>
> ## Acceptance
> - Image contains a working `svn`; after rebuild + `uta reattribute-owners`, Owner (`main_developer`) is populated for tests whose source file blames to an author.


<a id="issue-168"></a>

### #168 — Show test Owner in the still-failing triage bucket and as a pivot link on the per-test record page

- **State:** Closed
- **Labels:** area:dashboard, type:feat
- **Opened:** 2026-07-14 · **Closed:** 2026-07-14
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/168

> The test Owner (main developer) is only shown in the **New failing** triage table, even though every triage row already carries `owner`/`owner_url`. Owner is also useful when chasing/escalating a test that has been failing for a while.
>
> Additionally, the per-test record page shows the owner as plain inline text (`· owner X`) rather than the clickable pivot link used everywhere else (run summary, search, flaky, new-failing bucket).
>
> **Changes**
> - Add an Owner column (pivot link) to the **Still failing** triage table.
> - Render owner on the per-test record page as a pivot link, consistent with the rest of the UI (requires exposing `owner_url` on the record dict).
>
> **Acceptance check**
> - The Still failing table shows an Owner column that pivots the queue by owner.
> - The per-test record page renders owner as a clickable pivot link.
> - Offline suite green; ruff check + format clean.


<a id="issue-171"></a>

### #171 — Add monitoring of pipeline fails in the app

- **State:** Closed
- **Labels:** —
- **Opened:** 2026-07-23 · **Closed:** 2026-07-24
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/171

> Currently, the application is monitoring/reporting errors of unittests.
> But real pipeline failures are not yet part of the handled content by this application.
>
> I want to change this:
> When the pipeline is not executing successfully, then this should also be managed in the application. Be it whether the pipline was stopped by a user or stopped with an error 
> The user should here be able to document the problem, who is managing it, related tickets, and so on...
> The knowledge base and the LLM should help the user here to diagnose the problem.
>
> (When implementing this, consider (not implement) also ticket #172)

**Comment — palmkevin, 2026-07-24:**

> ## Implementation plan (agreed via design grilling)
>
> Introduces a build-level triage entity so pipeline-level failures (not just test failures) are managed, documented, and diagnosed with KB + LLM help. Designed forward-compatible with #172 (hung/slow builds) without schema churn.
>
> ### Concept & language (CONTEXT.md / ADR-0001)
> - New entity **Build Incident** — "a build-level condition requiring human triage." _Avoid_: Pipeline failure, Build failure, Incident (standalone).
> - **Incident Kind** discriminator: `pipeline_failure`, `aborted` now; `hung`, `slow` **reserved** for #172 (defined, not implemented).
>
> ### Trigger & lifecycle
> - Opens on a build whose top-level Jenkins `result` is **`FAILURE` or `ABORTED`** (`UNSTABLE`/`NOT_BUILT` excluded; orthogonal to test episodes — a build can produce both a Build Incident and test episodes).
> - **Streak model**: consecutive non-green builds collapse into **one** incident; **mixed kinds stay one incident** (kind = whatever opened it, others noted).
> - **Recovers** on the next build reaching **`SUCCESS` or `UNSTABLE`** (independent of `EXPECTED_TRACKS`). In-progress builds are ignored (that is #172's scope).
>
> ### Detection
> - Folded into the existing `ingest_build`/poller path (no new poller); high-water mark must advance past failed builds; incident handling runs **even when test analysis is skipped** (a FAILURE build is usually "incomplete").
> - Gated by a new flag (mirroring `INGEST_UNITTEST_STAGES`), **default on**.
>
> ### Enrichment
> - `FAILURE`: full reuse — Change Candidates + deterministic **Classification** (`infrastructure` becomes load-bearing) + **LLM Hypothesis** + Confirm/correct **provenance**.
> - **Signature** from the failing stage's log (fallback: console tail), reusing the Failure Signature machinery but **namespaced** — incident signatures only match incident signatures, never test-failure signatures.
> - `ABORTED`: no signature/classification/candidates → human-documented reason + optional LLM sanity note.
>
> ### Documentation surface (generalized to test episodes too)
> - New **Assignee** (person handling the fix), **Cause Ticket** (the existing single ticket field, **renamed/migrated** in place), **Resolution Ticket** (new) — all three on **both** Build Incidents and test episodes.
> - Resolution Ticket UI helper text must clarify it is "the ticket the **Assignee** is working on to resolve this" — not a claim that it is resolved.
> - Reuse existing triage-status enum (untriaged→investigating→root-caused→resolved), acknowledgement, and causing-person Attribution.
>
> ### Dashboard / alerts
> - **Dedicated Build Incidents triage page** + per-Build inline incident + **open-incident nav badge**.
> - Email on **new `FAILURE` incident open** only; `ABORTED` and recovery suppressed by default.
> - Teams-channel delivery deferred to #181.
>
> ### Cross-cutting
> - Incidents kept **forever** (like episodes; retention prunes neither).
> - Incident correlation window reuses the episode window (prev-build-start → this-build-end, capped by `DATA_CHANGE_MAX_LOOKBACK_DAYS`).
> - Demo dataset seeded with representative examples (a failure incident, an abort, a streak+recovery, and the new ticket/assignee fields).
> - `docs-overview-maintainer` run to sync OVERVIEW.html, help.html, README/.env.example, and CONTEXT.md.
>
> ---
> _Generated by [Claude Code](https://claude.ai/code)_


<a id="issue-172"></a>

### #172 — Tracking: Manage long-running pipelines

- **State:** Closed
- **Labels:** area:analysis, area:dashboard, area:ingest, type:feat
- **Opened:** 2026-07-23 · **Closed:** 2026-07-26
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/172

> **Tracking issue.** Beyond monitoring unit-test results (and pipeline *failures*, #171), we want to monitor pipeline **duration**. A grill-with-docs design session split this into two independently-shippable children with essentially zero shared implementation — one acts on *in-progress* builds, the other on *completed* ones.
>
> ## Children
> - [ ] #184 — **Visualize overrunning in-progress pipelines.** An always-on in-progress banner on the triage dashboard, highlighted (and emailed once) when a running build exceeds 2× its Expected Duration, so a human can stop it (→ the stop yields an `ABORTED` build documented by #171). *Ready to implement.*
> - [ ] #185 — **Flag & document abnormally slow successful builds.** A completed `SUCCESS`/`UNSTABLE` build slower than its Expected Duration by a configurable ratio (default 15%) becomes a documentable `BuildIncident(kind=SLOW)` with KB + LLM help. *Has one open lifecycle decision — not yet ready.*
>
> ## Shared design (settled)
> - **Canonical term `overrunning`** for the in-progress case (not "hung"/"never-ending"); `IncidentKind.HUNG` removed.
> - **Expected Duration** = median end-to-end wall-clock of the last 20 `SUCCESS`/`UNSTABLE` builds — the shared baseline for both children.
> - Recorded in **ADR-0006** and CONTEXT.md (*Expected Duration*, *Overrunning Build*).
>
> Original request preserved below for reference.
>
> ---
>
> Currently, the app is only monitoring unittests. With ticket #171, we will also integrate the management of Jenkins pipeline failures.
>
> The current issue is for still another level: we want to monitor the duration of the pipeline:
>
> - if a pipeline is never-ending, this should be made visible to the user. As a consequence, the user or somebody else could stop it (this will lead to an failure that can then be managed/documented with what has been implemented in #171) . For this feature, not more that visualizing never-ending pipelines is required
> - duration increase: When a pipeline-run was successful, but took unexpected longer then the average of previous successful runs, then this should also lead to an entry to be documented be the end user (same here as for #171 -> knowledgebase and LLM can provide help). Unexpected longer should be a ratio to be configured (a default of 15% seems a good fit to me)

**Comment — palmkevin, 2026-07-26:**

> Closing this tracking issue — both children are resolved:
>
> - **#184 — Visualize overrunning in-progress pipelines** → **shipped.** Delivers the core intent here: an in-progress build overrunning its Expected Duration is now visible on the dashboard (and emailed once) so a human can stop it, with the resulting `ABORTED` build documented via the #171 path.
> - **#185 — Flag & document abnormally slow successful builds** → **dropped** (closed not planned). The extra complexity (a GREEN-build incident lifecycle, per-kind-family `_open_incident`, plus undecided enrichment/alerting) wasn't worth taking on; what #184 shipped is sufficient for the duration-monitoring goal.
>
> Shared design work (canonical term `overrunning`, the *Expected Duration* baseline, `IncidentKind.HUNG` removal) landed with #184 and is recorded in ADR-0006 and CONTEXT.md. Nothing left open under this tracker.
>
> ---
> _Generated by [Claude Code](https://claude.ai/code)_


<a id="issue-174"></a>

### #174 — Rename shard → track: one term for the parallel lanes

- **State:** Closed
- **Labels:** area:docs, type:chore
- **Opened:** 2026-07-23 · **Closed:** 2026-07-24
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/174

> Domain-modeling session outcome: **Track** is the single canonical term for the parallel lanes the nightly build runs the test suite in; **shard** is banned (`_Avoid_`). Rationale: nothing is partitioned — the full suite runs in every lane, so CI-style "sharding" is the wrong metaphor; and the per-build execution record (status/timing of a track in a build) does not earn its own noun.
>
> Scope (all depths, clean break, no compat alias):
> - `CONTEXT.md`: add the **Track** entry, remove the "deliberately not yet defined" footnote.
> - New ADR-0002 recording the one-term decision and rejected alternatives.
> - Code identifiers: `BuildShard` → `BuildTrack`, `ShardTiming` → `TrackTiming`, `build.shards` → `build.tracks`, `shard_correlated` → `track_correlated`, `expected_shards` → `expected_tracks`.
> - DB: Alembic migration renaming `build_shards` → `build_tracks` (+ constraint). Column `track` stays `track` (matches `test_results.track`).
> - Settings surface: `EXPECTED_SHARDS` → `EXPECTED_TRACKS` (README table, `.env.example`, control-panel tunable label). **Breaking for operators** — one `.env` edit on the VM.
> - UI: build page "Shards" heading → "Tracks", "shard-correlated" badge → "track-correlated", help page drops the "(shard)" parenthetical.
> - Doc surfaces synced via `docs-overview-maintainer`.
>
> Deliberately **not** in scope: changing completeness semantics from track *count* to a name allowlist (separate issue if ever wanted); demo-dataset additions (rename only, no new visible signal).
>
> **Acceptance check:** `grep -ri shard` over the repo finds no hits outside git history / migration filenames' historical references.


<a id="issue-177"></a>

### #177 — Revisit retention volume estimate and data-change lookback window for per-commit build cadence

- **State:** Closed
- **Labels:** area:analysis, area:ingest, type:perf
- **Opened:** 2026-07-24 · **Closed:** 2026-07-24
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/177

> ## Context
>
> The "nightly build" language was corrected in #176 / ADR-0003: the analyzed **Permanent Pipeline** runs **one build per commit**, not once a night. Two numbers in the codebase were sized against the old once-a-night assumption and should be reviewed now that the true cadence is understood:
>
> 1. **Retention volume estimate** — `src/uta/retention.py` docstring reasons "~25k `TestResult` rows per build → ~9M rows/year." That 9M figure implicitly assumed ~365 builds/year (one per night). At per-commit cadence there are far more builds per year, so the real growth rate — and therefore the retention policy's sizing / `RESULT_RETENTION_DAYS` default — may need re-derivation.
>
> 2. **Data-change lookback window** — `DATA_CHANGE_LOOKBACK_HOURS` defaults to `12` (`src/uta/config.py`), chosen when a build was an overnight event. With frequent per-commit builds, a 12h lookback likely overlaps many builds' windows, which may over-attribute `ut_ref` changes to the wrong build. Review whether the window should shrink, or key off the previous build's boundary rather than a fixed hour count.
>
> ## Acceptance check
>
> - The retention growth estimate is re-derived from the actual per-commit build frequency (or the docstring is updated to reflect the corrected reasoning), and `RESULT_RETENTION_DAYS` is confirmed or adjusted accordingly.
> - The `DATA_CHANGE_LOOKBACK_HOURS` default (and/or the windowing strategy) is reviewed against per-commit cadence, with a decision recorded (keep as-is with rationale, shrink, or switch to a build-boundary-relative window).
>
> Terminology-only fix in #176 deliberately left both numbers untouched; this issue tracks the behavioral follow-up.


<a id="issue-178"></a>

### #178 — Accept "Jenkins run"/"pipeline run" as prose synonyms for Build in CONTEXT.md

- **State:** Closed
- **Labels:** area:docs, type:chore
- **Opened:** 2026-07-24 · **Closed:** 2026-07-24
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/178

> Domain-modeling session outcome: keep **Build** as the single canonical term (identifiers, schema, routes, and UI labels unchanged), but recognize the self-disambiguating compound forms **"Jenkins run"** and **"pipeline run"** as accepted *prose* synonyms — Jenkins's own API calls builds *runs* (`wfapi/runs`), translated to Build at the ingest boundary. Standalone "run" stays under `_Avoid_`, now with its reason spelled out (ambiguous with a single test's execution).
>
> **Acceptance check:** the CONTEXT.md `Build` entry documents the accepted compound synonyms with the boundary rationale, keeps standalone `Run` (and `job`) under `_Avoid_`, and states that identifiers/schema/routes/UI labels always say Build. `docs-overview-maintainer` confirms the other doc surfaces need no change.


<a id="issue-181"></a>

### #181 — Notify build incidents / alerts to a Microsoft Teams channel

- **State:** Closed
- **Labels:** area:email, type:feat
- **Opened:** 2026-07-24 · **Closed:** 2026-07-26
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/181

> Follow-up to #171 (build-incident monitoring).
>
> Today the app's only push channel is SMTP email (regression & ops alerts). In addition to email, we want to be able to post notifications to a **Microsoft Teams channel** — starting with new Build Incidents (pipeline failures/aborts from #171), and potentially the existing regression alerts too.
>
> Scope to define when picked up:
> - Transport: Teams incoming webhook (channel URL) vs Graph API — likely a configurable webhook URL, secret, flag-gated like the other integrations.
> - Which events route to Teams (build-incident opens, regressions, recovery?) and whether email + Teams are independently toggleable.
> - Message formatting (deep-link back to the incident/test record in the dashboard).
>
> Acceptance check: with a Teams webhook configured and the feature enabled, a newly opened Build Incident posts a message to the target channel with a link back to its record; disabled/unconfigured → no-op, offline gate unaffected.
>
> Not blocking #171 — email remains the channel delivered there.

**Comment — palmkevin, 2026-07-26:**

> ## Agreed design (domain-modeling session)
>
> Design settled ahead of the build. Docs landed on `claude/grill-with-docs-181-gt716z`: **ADR-0007** (`docs/adr/0007-alerts-multi-channel-teams-webhook.md`) + an **Alerting** section in `CONTEXT.md` (`Alert`, `Alert Kind`, `Alert Channel`).
>
> **Core move — multi-channel Alert layer.** Generalize the email-only delivery layer: each `build_*` composer returns a channel-neutral **`Alert`** (title, summary lines, deep-link, severity, kind). A post-commit **dispatcher** hands each `Alert` to every enabled **Alert Channel** whose subscription includes that kind; each channel renders it its own way. Two channels behind an `AlertChannel` Protocol (faked offline): `EmailAlertChannel` (existing SMTP, plain text) and `TeamsAlertChannel`.
>
> **Teams transport.** Incoming **webhook URL** (single secret POST target, flag-gated like SMTP) — **not** Graph API. Renders an **Adaptive Card** (title, facts block, `Action.OpenUrl` "Open in dashboard" from `app_base_url`), defaulting to the Power Automate Workflows `attachments` envelope. Uses the already-present `httpx` with a short timeout.
>
> **Alert kinds (the five email emits today):** `incident` (pipeline_failure opens), `regression`, `recovery`, `overrun`, `ops`. Aborted-incident and incident-recovery stay silent on all channels — no new composers.
>
> **Routing — full per-event × per-channel matrix**, two allowlists:
> - `EMAIL_EVENTS` — default `incident,regression,overrun,ops` (preserves today's behavior exactly).
> - `TEAMS_EVENTS` — default **empty** (opt-in per event).
> - `EMAIL_RECOVERY_NOTICE` **retired** → its effect is "is `recovery` in `EMAIL_EVENTS`".
> - Both validated against the five known kinds at startup (fail-fast).
>
> **Enablement.** Teams live iff `TEAMS_WEBHOOK_URL` set (independent of email — Teams-only/email-only/both/neither all valid). Acceptance-check "enabled" = URL set **and** `incident` in `TEAMS_EVENTS` (a bare URL posts nothing, by design).
>
> **Delivery.** Composed inside the ingest txn, dispatched **after commit**, **best-effort per channel** — one channel's failure never blocks the other or the ingest. Compose an `Alert` only when some enabled channel subscribes to its kind.
>
> **Config surface:** `+TEAMS_WEBHOOK_URL` (secret, never logged), `+TEAMS_EVENTS`, `+EMAIL_EVENTS`, `−EMAIL_RECOVERY_NOTICE`. New `build_channels(settings)` in `clients.py`, shared by pipeline + poller.
>
> **No UI footprint, no demo-dataset change** — backend side-effect, like SMTP today; the Render demo leaves Teams unconfigured.
>
> **Docs to sync at implementation time** (via `docs-overview-maintainer`): OVERVIEW.html (Teams as a new external system + the alert-channel layer), README config table + `.env.example` (three new keys, drop `EMAIL_RECOVERY_NOTICE`). Help page unchanged.
>
> Full rationale + rejected alternatives (Graph API, shared-text wrapper, parallel `TeamsSender`, ten booleans, strict email/Teams coupling) are in ADR-0007.
>
> ---
> _Generated by [Claude Code](https://claude.ai/code)_


<a id="issue-184"></a>

### #184 — feat: visualize overrunning in-progress pipelines

- **State:** Closed
- **Labels:** area:dashboard, area:ingest, type:feat
- **Opened:** 2026-07-26 · **Closed:** 2026-07-26
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/184

> Child of #172. Design settled in a grill-with-docs session; recorded in **ADR-0006** (`docs/adr/0006-overrunning-builds-live-signal-not-incident.md`) and CONTEXT.md (*Overrunning Build*, *Expected Duration*).
>
> ## Intent
> Make a still-running (in-progress) pipeline that is taking too long **visible** on the dashboard so a human can go stop it. Per the ticket, *"not more than visualizing is required"* — stopping the build produces an `ABORTED` build, which the existing #171 path documents.
>
> ## Domain decisions
> - **Canonical term: `overrunning`** (not "hung"/"never-ending"/"stuck"). Used in config keys, the stored flag, the banner, and docs.
> - An **Overrunning Build is NOT a Build Incident** and is never persisted as one. It is an ephemeral, poller-observed live signal. `IncidentKind.HUNG` is **removed** (code-only; nothing ever wrote it, so no migration).
> - **Expected Duration** = the **median** end-to-end wall-clock of the last **20** `SUCCESS`/`UNSTABLE` builds (shared with the slow-build child). Undefined until 20 such builds exist.
>
> ## Detection (poller-driven)
> - Poll interval default drops **300 → 60 s** (`poll_interval_seconds`) for a near-real-time banner. (`poller_stale_after_intervals` stays 5 → /health now flags stale after 5 min.)
> - Each tick the poller fetches Jenkins' current `lastBuild` (new `JenkinsClient` method: `number`, `building`, `timestamp`). If `building == true` it is the in-progress build.
> - **Overrunning** when `elapsed_at_tick > Expected Duration × (1 + overrun_ratio)`, default `overrun_ratio = 1.0` → **2× median**.
> - The **poller is the single source of truth** for overrunning-ness: it computes the flag and stores it. Requires the full 20-build baseline; with fewer, never flags.
>
> ## Persisted state (single-row snapshot, overwritten each tick)
> `build_number`, `started_at`, `expected` (the median), `building`, `overrunning` (poller-computed), and an alert-sent marker for de-dup. Stored in the DB (survives poller restart → no re-alert storm). Suggested home: extend the poller heartbeat state.
>
> ## UI (dumb — reflects stored facts, computes only elapsed)
> - **Always-on in-progress banner** at the top of the triage dashboard while a build is building, showing: build number, **elapsed** (`now − started_at`, the *only* value computed live at render), **expected ~Xh** (the stored median), and a **deep-link to the build in Jenkins**.
> - **Highlighted iff the stored `overrunning` flag is set** (highlight may lag the true crossing by ≤ 1 poll interval — accepted).
> - Edge cases: **no in-progress build** → no banner; **< 20 baseline builds** → banner still shows elapsed but omits "expected" and never highlights.
>
> ## Email
> - On the first tick the poller sets `overrunning`, send **one** email (existing SMTP config/recipients), de-duped by the persisted marker; reset when the in-progress build changes/finishes. The eventual `aborted` incident stays silent → no double alert.
>
> ## Config (new)
> - `detect_overrunning_builds` (bool, default `True`), `overrun_ratio` (float, default `1.0`, **live-tunable** via the control panel like the other thresholds).
> - Changed default: `poll_interval_seconds` 300 → 60.
>
> ## Demo
> - Seed **one un-flagged in-progress build** (recent `started_at`, `overrunning=false`) so the live demo shows the banner's normal state (elapsed ticks up live).
>
> ## Docs
> - Invoke `docs-overview-maintainer` for OVERVIEW.html, help.html, README + `.env.example` (3 config changes). CONTEXT.md + ADR-0006 already landed in the design branch.
>
> ## Acceptance check
> - `pytest -m "not live"` green (ruff check + format clean).
> - With a full baseline, an in-progress build past 2× the median median is stored as `overrunning` by the poller, the dashboard banner highlights it and links to Jenkins, and exactly one email fires per overrunning build.
> - Elapsed advances on refresh with no poll in between; no banner when nothing is building; graceful < 20-baseline behavior.
> - `IncidentKind.HUNG` removed with no references left; demo shows the in-progress banner.


<a id="issue-185"></a>

### #185 — feat: flag & document abnormally slow successful builds

- **State:** Closed
- **Labels:** area:analysis, type:feat
- **Opened:** 2026-07-26 · **Closed:** 2026-07-26
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/185

> Child of #172. Design partially settled in a grill-with-docs session; **one open decision remains** (see below) so this issue is *not yet ready to implement*.
>
> ## Intent
> When a build **completes** but took unexpectedly longer than usual, flag it so the end user can document *why* — same downstream workflow as #171 (knowledge base + LLM help).
>
> ## Settled decisions
> - **Duration measured:** overall build **wall-clock** (`Build.finished_at − started_at`) — the whole pipeline, not just the UT stages. (Ticket frames this as *pipeline* duration; a slowdown in any stage should surface.)
> - **Baseline (shared with #184):** the **median** wall-clock of the last **20** builds whose result is `SUCCESS` **or** `UNSTABLE` (the *Expected Duration*). No comparison at all until ≥ 20 such builds exist.
> - **Central tendency: median** (called "median" everywhere — config, UI, docs — even though the ticket says "average"; median is robust to a freak-slow outlier).
> - **Candidates evaluated:** both `SUCCESS` and `UNSTABLE` completed builds (symmetric with the baseline set).
> - **Threshold:** SLOW when `wall-clock > median × (1 + slow_build_ratio)`, default `slow_build_ratio = 0.15` (15%).
> - **Config (new):** `detect_slow_builds` (bool, default `True`), `slow_build_ratio` (float, default `0.15`, **live-tunable**), `slow_baseline_window` (int, default `20`, live-tunable — likely shared with #184).
> - **Incident kind:** a SLOW build becomes a `BuildIncident(kind=SLOW)` carrying the same documentation surface as #171 (assignee, cause/resolution ticket, triage, KB + LLM).
>
> ## ⛔ Open decision (blocks implementation)
> **How does a SLOW incident's lifecycle work, given it opens on a GREEN build?** The existing `BuildIncident` is a *streak* that opens on a non-green build and recovers on the next green one — SLOW inverts that (it opens on `SUCCESS`/`UNSTABLE`).
> - **Option 1 — one incident per slow build (no streak).** Simplest, but a rolling-median baseline means a genuine step-slowdown trips the threshold for ~11 consecutive builds before the median catches up → ~11 near-duplicate entries per regression.
> - **Option 2 — SLOW as its own streak** (open on first slow build, extend over consecutive slow builds, recover on the first back-to-normal build). One entry per slowdown episode; reuses `build_count`/`reopen_count`/`recovered_build_id`. Cost: two open incidents can coexist (a SLOW streak still open when a later build FAILUREs), so `_open_incident` must become **per-kind-family**.
>
> Recommendation was Option 2; decision **parked** — resolve before implementing. Likely warrants an ADR.
>
> ## Also to design when unparked
> - **Enrichment shape:** a slow `SUCCESS` build has no error text / failing stage / failure signature — decide what (if anything) the failure-signature/KB and LLM hypothesis operate on (change candidates in the correlation window? the slowest stage(s)?).
> - Whether SLOW alerts by email.
> - Demo seeding (a slow-build example).
> - Docs sync via `docs-overview-maintainer`; add *Slow Build* to CONTEXT.md; `slow` already noted as a reserved Incident Kind.
>
> ## Acceptance check (provisional)
> - A completed `SUCCESS`/`UNSTABLE` build slower than `median × 1.15` (≥ 20-build baseline) opens a `BuildIncident(kind=SLOW)` per the chosen lifecycle, documentable with KB + LLM like #171.
> - `pytest -m "not live"` green; ruff clean; demo showcases a slow build.

**Comment — palmkevin, 2026-07-26:**

> Closing as **not planned**.
>
> What #184 delivered (the shared *Expected Duration* baseline — median wall-clock over the last 20 `SUCCESS`/`UNSTABLE` builds) is sufficient for the long-running-pipeline goal under #172. Flagging *abnormally slow successful* builds as documentable `BuildIncident(kind=SLOW)` incidents adds meaningful complexity — most notably the unresolved lifecycle question (a streak that opens on a GREEN build, forcing `_open_incident` to become per-kind-family) plus the enrichment/alerting/demo design still to settle — that isn't worth taking on right now.
>
> The design notes here remain in the git/issue history if this is ever revisited.
>
> ---
> _Generated by [Claude Code](https://claude.ai/code)_


<a id="issue-189"></a>

### #189 — allow to search on failure

- **State:** Closed
- **Labels:** —
- **Opened:** 2026-07-27 · **Closed:** 2026-07-27
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/189

> I want to be able to find failing unittests by their failure details. 
> Example if unittests have "uuid4" in its  failure detail, the I want to find them


<a id="issue-191"></a>

### #191 — Remove the triage queue's Suite filter

- **State:** Closed
- **Labels:** area:dashboard, type:chore
- **Opened:** 2026-07-27 · **Closed:** 2026-07-27
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/191

> The triage filter bar's **Suite** field matches `TestIdentity.suite`, which for every devUTs (nose2) test is the literal JUnit suite-element name `nose2-junit` — the module prefix people actually want to filter by (`ut_ldt`, `ut_pricing`, …) lives in `class_name` / `canonical_name`, which the filter never reads.
>
> So the field can only ever select "all devUTs tests" or one of the five console-log stage suites (LXS, SMB Pricing, SMB Transform, ITF Highlevel, Uniface). Its placeholder (`e.g. ut_pricing`) promises module filtering it cannot deliver, which is how this was found: filtering on `ut_ldt` returns nothing even though those tests are failing.
>
> Remove the filter rather than keep a control that misleads. Suite stays a *displayed* fact on the test record and in the search pick-list; it just stops being a triage-queue filter (and stops being a pivot target, since the pivot points at that filter).
>
> **Scope**
> - drop `suite` from `_TRIAGE_FILTER_KEYS`, `_matches_filters`, `_CHIP_LABELS`
> - drop `suites` from `triage_filter_options` (dropdown source)
> - remove the Suite input + datalist from `triage.html`
> - render suite as plain text in `search.html` (no `suite_url` pivot)
> - update the tests and the affected doc surfaces
>
> **Acceptance check**
> No `suite=` query param is honored by the triage queue, no Suite control renders in the filter bar, and `pytest -m "not live"` is green.
>
> Finding tests by module prefix is still possible via the navbar search (`canonical_name ILIKE`); a dedicated triage-queue name filter is deliberately out of scope here.


<a id="issue-194"></a>

### #194 — Idea/spike: an "Incident" aggregate as the triage & documentation unit (grouping failing tests)

- **State:** Open
- **Labels:** area:analysis, type:feat
- **Opened:** 2026-07-29
- **Original URL:** https://github.com/palmkevin/Jenkins-UT-Analyzer/issues/194

> > **Status: idea / exploration, NOT a committed proposal.** Captured from a grilling session so it can be resumed later. Nothing here is decided — the point is to preserve the idea and the open questions.
>
> ## Where this came from
>
> A narrower observation started it: today the **cross-test signature grouping** is only surfaced in the triage queue's **New** bucket (the `signature_ack_count` + "Ack all w/ signature" button, over *unacknowledged* failing rows). Once tests are acknowledged they fall into **Still failing**, which carries **no** signature grouping — the only remnant is a bare count (`open_affected`) on an individual test's record page, never a list of *which* tests. So after acking a batch as "one outage," you can no longer see or act on that group.
>
> The narrow fix would be a signature-grouped view/column in Still-failing. But the grilling surfaced a bigger question about the model itself.
>
> ## The idea
>
> Introduce a first-class **Incident** aggregate: a group of failing tests (and possibly a failing/aborted build) understood as **one thing to triage**. Instead of documenting per-test failures, the **Incident** becomes the documentation locus — it carries the Cause Ticket, Assignee, Attribution, and Triage Status. Tests *link to* an incident. An incident closes when its tests stop failing.
>
> Framed in the current model:
> - The per-test **Failure Episode** almost certainly **survives** — the fail→fix lifecycle per test is a load-bearing invariant (it's how we know a test came back green). It would **demote** from "the thing you document" to **per-test evidence linked to an incident**.
> - Attribution / Assignee / Cause Ticket / Resolution Ticket / Triage Status / Hypothesis would move **up** from the episode to the incident (document once per outage, not once per test).
>
> **Motivating win:** document 1 incident instead of 14 near-identical tests. That's a complexity *reduction* for the common "one root cause, many tests" case — the opposite of the fear below.
>
> ## Big tension to resolve first: collision with "Build Incident"
>
> `CONTEXT.md` already defines **Build Incident** (a build-level condition — pipeline `FAILURE`/`ABORTED`) and explicitly keeps it **orthogonal** to Failure Episodes ("the two never merge"). This idea proposes a *broader* Incident that spans test failures too — so we must decide whether the new concept **unifies** build-level and test-level triage under one aggregate, or is a **new, separate** concept (and then what "Build Incident" becomes). This is the naming/architecture fork that gates everything.
>
> ## Open design questions (the decision tree to grill next)
>
> 1. **Membership — what makes a test belong to an incident?**
>    - *Derived/automatic* (incident = the live signature cohort with an identity; auto-attach on failure, auto-detach when the episode closes; "incident of one" created automatically — near-zero end-user ceremony).
>    - *Human-curated* (a person declares incidents and files tests into them — highest control, highest complexity; the "filing system" risk).
>    - *Hybrid* (auto-grouped by signature, human can split/merge to fix the imperfect `_error_key` grouping).
>    - _Leaning: start derived, design so hybrid split/merge can be added later._
> 2. **Cohort definition — live vs frozen.** Is "the group" the tests **currently** failing with the signature (drifts as builds land: new victims join, fixed ones drop), or the **frozen set** captured at some moment (e.g. an ack click)? _Leaning: live, keyed by signature — attribution tracks the cause, not a click's timestamp. (`open_episodes_for_signature` already computes the live set.)_
> 3. **Documentation locus & migration.** Confirm attribution/assignee/ticket/triage move to the incident; decide what happens to today's **per-episode** attributions and the existing `/signatures/{id}/attribute` (#106) and ack-by-signature (#63) actions.
> 4. **Unify with Build Incident or not** (see tension above). If unified: is a build failure just an incident whose "signature" is the failing stage?
> 5. **Identity & lifecycle.** What opens an incident, what closes it (**all** member tests green? any? what about removed-while-failing tests, which never close their episode?), how new matching failures join an already-documented incident, numbering.
> 6. **The "incident of one".** A lone failing test — is it an incident too? Must avoid adding ceremony to the common single-failure case (the end-user-complexity risk that motivated pausing).
>
> ## Grouping-key caveat
>
> The cross-test grouping key today is `_error_key` (exception type + masked message, stack frames stripped) — see `src/uta/web/actions.py`. It is deliberately coarser than the per-test **Failure Signature** (which includes frames). Any incident-membership design inherits that key's precision: two genuinely different outages sharing a masked message would mis-group, which is the main argument for a human split/merge escape hatch.
>
> ## Explicit non-goal for now
>
> No implementation. This is to be grilled further (likely a `/domain-modeling` session — the concept needs a name and a clean relationship to Build Incident / Failure Episode in `CONTEXT.md`, and if adopted, an ADR since it reshapes the triage aggregate and is hard to reverse).

