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

## `naming-alignment` — reconcile the three names this project answers to

`area: infra` · raised by the Bitbucket migration

The Bitbucket repo is **`lx-ci-monitor`**, the Python package is **`uta`**, the Render service is
**`jenkins-ut-analyzer-demo`**, and the devcontainer `name` / `workspaceFolder` are still
**`Jenkins-UT-Analyzer`**. Nothing is broken — but four names for one tool is a standing tax on every
doc and every new reader.

**Acceptance:** either a decision to align them (and the rename executed across
`.devcontainer/devcontainer.json`, `render.yaml`, README/OVERVIEW product naming), or a recorded
decision to keep them divergent with the reason.

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
