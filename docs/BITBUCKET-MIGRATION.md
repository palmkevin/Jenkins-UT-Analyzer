# Migration: GitHub → Bitbucket Cloud

Record of the move of this repo from `github.com/palmkevin/Jenkins-UT-Analyzer` to
`bitbucket.org/labsolutionlu/lx-ci-monitor`, and the runbook for the one-time steps that must be
done in the two web UIs.

**Shape of the move:** Bitbucket Cloud becomes the canonical remote. GitHub is
demoted to a **read-only push mirror** — it is not abandoned, because the public Render demo
auto-deploys from it and the pre-migration issue/PR history lives there. Only `main` was carried
over. The issue tracker did **not** survive the move: see *Where the tracker went* below.

## Decisions and their consequences

| Decision | Consequence |
|---|---|
| Bitbucket Cloud is canonical; GitHub kept as a push mirror | The mirror is fed by a **Pipelines step on `main`**, not by a developer's push. See *Keeping the mirror in sync* below. |
| Only `main` migrated | The ~110 merged PR branches were **squash-merged**, so their content is already in `main`. Their tips stay on the GitHub mirror. `main`'s full commit history is preserved byte-for-byte. |
| Issues **could not** move to Bitbucket | The tracker is being sunset and would not enable (`410 Gone`); Jira was declined. Open work moved in-tree to [`OPEN-WORK.md`](OPEN-WORK.md). All 84 issues + 110 PRs are archived in [`history/`](history/). |
| CI ported to Bitbucket Pipelines | [`../bitbucket-pipelines.yml`](../bitbucket-pipelines.yml) is the merge gate. `.github/workflows/ci.yml` is retained **only** so the mirror stays green; it is not the gate. |
| Render demo left pointing at GitHub | No Render reconfiguration, no downtime for the public demo. |

### `#N` is now ambiguous — the one trap worth internalising

GitHub numbers issues **and** PRs in a single sequence (this repo's `#193` is a PR, `#194` an issue).
Bitbucket numbers issues and PRs **separately, each from 1**. So Bitbucket issue IDs could never line
up with the GitHub numbers, and ~110 merged commit messages already contain bare `#N`.

The convention (also in `CLAUDE.md`): **a bare `#N` means the GitHub sequence**, resolvable in
[`history/github-issues.md`](history/github-issues.md) and
[`history/github-pull-requests.md`](history/github-pull-requests.md). When citing a pre-migration
item from now on, write `GH#194`. Because no replacement tracker exists, nothing new mints issue
numbers that could collide — the only post-migration numbers are **Bitbucket PR IDs** (from 1),
which are always written as `PR #1`. In-tree work items are referenced by **slug** instead.

### Where the tracker went

The plan was to recreate the one still-open issue (GH#194) in Bitbucket Issues and carry on there.
That failed, and the fallback is now the convention:

1. **Bitbucket's tracker would not enable.** Every `POST`/`GET` on `/2.0/repositories/…/issues`
   answered **`410 Gone`** — the tracker is switched off at the repo level, and turning it on needs
   repository **admin** scope, which the pull-request/issue-write token does not carry
   (`Your credentials lack one or more required privilege scopes`).
2. **It is being sunset anyway.** Atlassian is retiring Bitbucket Cloud's issue tracker in favour of
   Jira, so re-enabling it — even with an admin token, or by hand in the UI — would have meant
   migrating twice.
3. **Jira was declined.** Adopting the workspace Jira for this repo was considered and rejected: too
   heavy for a single-maintainer tool, and it puts the backlog behind an auth wall that the repo's
   own readers (and Claude Code sessions) can't see.
4. **So the backlog moved in-tree**, to [`OPEN-WORK.md`](OPEN-WORK.md). It versions with the code,
   needs no credentials to read, and the PR that finishes an item deletes its entry — so the diff
   *is* the closing record. The cost is that it is hand-maintained and has no query/filter surface;
   it stays viable only because the list is short.

Even had it enabled, Bitbucket's tracker was a poor fit — recorded here so the decision isn't
revisited from scratch:

- **No free-form labels.** `type:*` would have collapsed onto the fixed `kind`
  (`bug`/`enhancement`/`proposal`/`task`); `area:*` has no equivalent at all, since components must
  be pre-created in repo settings and are read-only over the API.
- **No author/date preservation.** Recreated issues would be authored by the migrating user, dated
  now, with the originals demoted to a provenance footer.
- **No `Closes #N` automation.** Bitbucket will not close an issue from a PR body, so every close
  would have been a separate manual step after merge.

## What changed in the repo

| Path | Change |
|---|---|
| [`../bitbucket-pipelines.yml`](../bitbucket-pipelines.yml) | **New.** Port of the GitHub Actions CI, plus the `mirror main to the GitHub mirror` step (see *Keeping the mirror in sync*). |
| [`../scripts/wait_for_db.py`](../scripts/wait_for_db.py) | **New.** Postgres readiness gate — Pipelines has no service health-checks. |
| [`OPEN-WORK.md`](OPEN-WORK.md) | **New.** The in-tree backlog that replaces the issue tracker. |
| [`history/`](history/) | **New.** Frozen Markdown + JSON archive of 84 issues and 110 PRs. |
| [`pull-request-template.md`](pull-request-template.md) | **Moved** from `.github/`. Bitbucket has no in-repo PR template; this is the source text for the repo setting. |
| `../.github/workflows/ci.yml` | **Kept**, mirror-only. |
| `../.devcontainer/devcontainer.json` | Added a `git-credentials` volume so the Bitbucket HTTPS token survives rebuilds. |
| `../CLAUDE.md`, `../README.md`, `OVERVIEW.html` | Task workflow, CI, and status-source-of-truth references retargeted. |

### Why `wait_for_db.py` exists

The migration tests **skip** (not fail) when Postgres is unreachable — deliberate, so
`pytest -m "not live"` stays green on a dev box without one. GitHub Actions guaranteed readiness with
`--health-cmd pg_isready`; Bitbucket Pipelines has no equivalent and starts the step as soon as the
service container launches. Without a readiness gate, a startup race would make the **destructive
migration test silently skip** — the gate would go quietly weaker rather than red. `wait_for_db.py`
turns that race into an explicit failure.

## Runbook

### 1. Credentials (once)

**`git push` over HTTPS already works** inside the devcontainer: the VS Code credential helper
forwards the Bitbucket credentials the *host* holds (verified with `git push --dry-run`). Use the
**HTTPS** remote URL, not `git@bitbucket.org:` — the container has no SSH key, so the SSH URL fails
with `Permission denied (publickey)`.

Outside VS Code (a plain terminal, or after the helper's socket goes away) there is no host
forwarding, so store an **Atlassian API token** instead — Atlassian retired Bitbucket app passwords.
Create one at **id.atlassian.com → Security → API tokens**:

```bash
# Persisted at ~/.config/git/credentials (a devcontainer volume — survives rebuilds).
git config --global credential.helper store
printf 'https://%s:%s@bitbucket.org\n' "<url-encoded-atlassian-email>" "<api-token>" \
  >> ~/.config/git/credentials
chmod 600 ~/.config/git/credentials
```

`@` in the email must be percent-encoded as `%40` in the credentials file.

The **REST API** (opening PRs) has no equivalent of the git helper and always needs
the token explicitly. These are developer-shell credentials, **not app config** — nothing under
`src/uta/` reads them, so they are deliberately absent from `config.py` and `.env.example`. Export
them from your shell profile, not `.env`:

```bash
export BITBUCKET_EMAIL='kevin.palm@labsolution.lu'
export BITBUCKET_TOKEN='<api-token>'
```

**A git-push token is not enough, and a few things bite here:**

1. **The username differs by transport.** Git over HTTPS accepts the Bitbucket *username*
   (`kpa_labsolution`); the REST API rejects it with `API token must be used with an atlassian
   registered email` and requires the **Atlassian account email**.
2. **Scopes.** The credential already stored in this devcontainer is git-only — it returns `403` on
   `/2.0/user`, `/pullrequests`, `/issues` and `/pipelines_config` while `GET /2.0/repositories/…`
   succeeds. A token for the API work needs **pull-request write**
   (`write:pullrequest:bitbucket` on a scoped Atlassian API token; `pullrequest:write` on a
   repository or workspace access token). Issue-write is moot — there is no tracker.
3. **Admin is a separate tier.** Enabling **Pipelines** (or the issue tracker) over the API needs
   repository **admin**, which a pull-request-write token does not carry — the `PUT`s answer
   `Your credentials lack one or more required privilege scopes`. Do it in the UI (*Bitbucket repo
   settings*, below) unless you deliberately mint an admin-scoped token.
4. **`410 Gone` on `/issues` means the tracker is switched off**, not that the token is wrong. It is
   easy to misread as an auth failure while `/pullrequests` returns `200` with the same credential.
   This is what ended the tracker plan — see *Where the tracker went*.

Verify a new token before relying on it:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' -u "$BITBUCKET_EMAIL:$BITBUCKET_TOKEN" \
  https://api.bitbucket.org/2.0/repositories/labsolutionlu/lx-ci-monitor/pullrequests
```

### 2. Remotes

```bash
git remote rename origin github
git remote add origin https://bitbucket.org/labsolutionlu/lx-ci-monitor.git

# Make `origin` fan out to both hosts on push, Bitbucket first.
git remote set-url --add --push origin https://bitbucket.org/labsolutionlu/lx-ci-monitor.git
git remote set-url --add --push origin https://github.com/palmkevin/Jenkins-UT-Analyzer.git

git remote -v          # expect 1 fetch + 2 push URLs on origin
```

### 3. Reconcile the destination's stub commit, then push `main`

The Bitbucket repo was created through the web UI, so it already had a `main` — one `Initial commit`
(`17b3568`) containing nothing but Atlassian's boilerplate `.gitignore` template. It shares **no
common ancestor** with our history, so a plain `git push` is rejected as a non-fast-forward.

Force-pushing is the wrong tool here (and is blocked by `.claude/settings.json`'s deny rule). Merge
the stub in instead — it costs one merge commit and destroys nothing:

```bash
git checkout main
git fetch origin
git merge origin/main --allow-unrelated-histories  # conflicts on .gitignore
git checkout --ours .gitignore                     # ours is purpose-built; theirs is boilerplate
git add .gitignore && git commit
git push -u origin main
```

> **Do not use `git merge FETCH_HEAD` here.** While `main` still tracked `github/main`,
> `git fetch origin main` recorded FETCH_HEAD as **`not-for-merge`**, so `git merge FETCH_HEAD`
> reported *"Already up to date"* and silently did nothing — the merge looked done when no merge had
> happened. Merge the remote-tracking ref (or the explicit SHA) instead.

### 4. Bitbucket repo settings (web UI, once)

1. **Pipelines** — Repository settings → Pipelines → Settings → **Enable Pipelines**. Nothing runs
   until this is on, even with `bitbucket-pipelines.yml` committed.
2. **Branch restrictions** on `main` — Repository settings → Branch restrictions → Add:
   - Prevent deletion, prevent rewriting history (force-push).
   - **Merge checks:** at least 1 successful build, and *"Merge via pull request only"*.
   - Enable **"Rebase, merge or squash only when the branch is up to date"** — this is the analogue of
     GitHub's `strict` required check that we relied on.
   - Leave admins exempt, preserving the direct-push hotfix escape hatch.
3. **Default PR description** — Repository settings → Pull requests → paste
   [`pull-request-template.md`](pull-request-template.md).
4. **Issue tracker** — **skip: deliberately left disabled.** See *Where the tracker went* above; the
   backlog lives in [`OPEN-WORK.md`](OPEN-WORK.md). Enabling it would reintroduce a second,
   contradictory source of truth for status.

### 5. Demote GitHub

GitHub must stay **pushable** (the mirror) but stop being a workplace:

1. Remove the required-status-check branch protection on `main`. This is a **hard prerequisite for
   the automated mirror sync** (next section), not just future-proofing: the migration push could
   bypass the protection because it was made by a repo admin, but the deploy key the Pipelines step
   authenticates with cannot bypass anything, so the automated push is **rejected outright** while
   the protection stands. Independently, the protection would also start rejecting pushes once
   Actions minutes lapse or the workflow is disabled.
2. Repository settings → Features → **uncheck Issues** (the archive is in-tree) and **Wikis**.
3. Edit the GitHub description / add a `MIRROR` note to the top of the README's GitHub view pointing
   at Bitbucket.
4. Leave **Actions enabled** if you want the mirror's CI as a free second opinion; it is not the gate.

Do **not** archive the GitHub repo — archiving makes it read-only and the mirror push would fail,
which also breaks the Render demo deploy.

### 6. Keeping the mirror in sync

**The problem this solves.** `origin` was originally given two push URLs so one `git push origin
main` would update both hosts. That works only when a *human* pushes `main` — and after the
migration nobody does: `main` advances exclusively through a Bitbucket **PR merged server-side**, so
no workstation is in the loop at all. The mirror therefore drifts silently, and because Render
auto-deploys the public demo from the mirror, the demo quietly stops updating. It is a failure with
no error message anywhere, which is what makes it worth automating rather than remembering.

**The mechanism.** A second step in [`../bitbucket-pipelines.yml`](../bitbucket-pipelines.yml)'s
`branches: main` pipeline pushes `main` to GitHub from Atlassian's runners, so the sync depends on
no workstation being up, credentialed, or switched on. Three properties are deliberate:

- **It runs after `test`.** Pipelines aborts a pipeline at the first failing step, so a red `main`
  never reaches the mirror and never reaches the demo. That is what keeps "demo deploys are
  test-gated" true by construction rather than by habit.
- **`clone: depth: full`.** Pipelines clones at depth 50; git cannot push a complete history out of
  a shallow clone.
- **It never force-pushes.** The mirror is receive-only, so the push is always a fast-forward. If it
  ever is not, someone has committed to the mirror directly and the push *should* fail loudly rather
  than silently discard their work.

**The credential** is an SSH deploy key, not a token — a PAT expires and would strand the demo on a
date nobody has written down. One-time setup, both in web UIs:

1. **Bitbucket** → Repository settings → **SSH keys** → *Generate keys*. Copy the **public** key.
2. Same page → **Known hosts** → add `github.com` and *Fetch* its fingerprint. Without this the push
   fails host-key verification — it is the step that is easiest to miss.
3. **GitHub** → the mirror repo → Settings → **Deploy keys** → *Add deploy key* → paste the public
   key, tick **Allow write access**.

Once it is live, **drop the GitHub push URL from `origin`** — two mechanisms doing one job is how
they drift, and a manual push to the mirror's `main` would hit the same branch protection anyway:

```bash
git remote set-url --delete --push origin https://github.com/palmkevin/Jenkins-UT-Analyzer.git
git remote -v          # expect 1 fetch + 1 push URL, both Bitbucket
```

**If Pipelines is ever dropped** (see the `ci-ownership` item in [`OPEN-WORK.md`](OPEN-WORK.md)),
this step goes with it and the mirror sync has to move to whatever replaces it — otherwise the demo
silently stops updating again, by exactly the same mechanism.

## Open follow-ups

These are **tracked in [`OPEN-WORK.md`](OPEN-WORK.md)**, not here — this doc records the move, and a
second backlog would be exactly the drift the single-source-of-truth rule exists to prevent. The
migration raised three items, by slug. Two are still open:

- **`naming-alignment`** — the repo was renamed in the move (`Jenkins-UT-Analyzer` → `lx-ci-monitor`)
  while the package stays `uta` and the Render service stays `jenkins-ut-analyzer-demo`.
- **`ci-ownership`** — Bitbucket Pipelines vs the DevOps-owned Jenkins named in
  [`../DEPLOYMENT-HANDOVER-uta-filled.md`](../DEPLOYMENT-HANDOVER-uta-filled.md), including the
  metered build minutes (free tier is 50 min/month; this suite costs ~3.5 min per build). Pipelines
  now also carries the mirror sync, so it is no longer only the test gate.

The third, **`github-protection-removal`**, is **done** — recorded here because this doc is the
record of the move, while its `OPEN-WORK.md` entry was deleted on completion per the closing
convention. Branch protection is off the mirror's `main`, Issues and Wikis are unchecked, the
description points at Bitbucket, and the automated sync was observed pushing `main` to the mirror
(`main` pipeline #9: `test` then `mirror main to the GitHub mirror`, both green, with the mirror's
`main` read back to confirm it had actually advanced). The local `origin` no longer carries the
GitHub push URL, so the Pipelines step is the single mechanism.

Two things bit during that setup, both worth knowing if the credential is ever re-issued:

- **Repository settings → Security → Access keys is the wrong page.** That is the *inbound*
  direction — keys granting read access *to* the Bitbucket repo. The Pipelines key lives under
  **Repository settings → Pipelines → SSH keys**, which is also where *Known hosts* is set. Only that
  page generates a pair whose private half is injected into build containers.
- **`Permission denied (publickey)` does not distinguish "no key configured" from "wrong key on the
  far end".** It is an *authentication* failure, so it also rules out the read-only-deploy-key theory
  (a read-only key authenticates and then fails the push with an explicit read-only message). Do not
  read it as proof that *Known hosts* is correct either — that only shows up as
  `Host key verification failed` once a key is actually being offered.
