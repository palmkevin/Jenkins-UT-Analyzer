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

**Acceptance:** either Pipelines is kept deliberately as the pre-merge gate with Jenkins doing
post-merge deploy, or `bitbucket-pipelines.yml` is dropped and the gate moves to Jenkins. Whichever,
update the *Testing contract* in `CLAUDE.md`.

---

## `github-protection-removal` — stop the mirror push from breaking

`area: infra` · **time-sensitive** · raised by the Bitbucket migration

`main` on the GitHub mirror still has a required-status-check branch protection. The migration push
had to bypass it (the remote said so). Once Actions minutes lapse or that workflow stops running,
mirror pushes get **rejected** — and because Render auto-deploys the public demo from the mirror,
the demo silently stops updating.

**Acceptance:** protection removed on the mirror's `main`, Issues + Wikis unchecked, a MIRROR note
added. The repo must **not** be archived — archiving makes it read-only and kills the mirror push
outright. See [BITBUCKET-MIGRATION.md](BITBUCKET-MIGRATION.md) → *Demote GitHub*.
