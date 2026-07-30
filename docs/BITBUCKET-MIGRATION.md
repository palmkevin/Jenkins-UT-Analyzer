# Migration: GitHub → Bitbucket Cloud

Record of the move of this repo from `github.com/palmkevin/Jenkins-UT-Analyzer` to
`bitbucket.org/labsolutionlu/lx-ci-monitor`, and the runbook for the one-time steps that must be
done in the two web UIs.

**Shape of the move:** Bitbucket Cloud becomes the canonical remote and the issue tracker. GitHub is
demoted to a **read-only push mirror** — it is not abandoned, because the public Render demo
auto-deploys from it and the pre-migration issue/PR history lives there. Only `main` was carried
over.

## Decisions and their consequences

| Decision | Consequence |
|---|---|
| Bitbucket Cloud is canonical; GitHub kept as a push mirror | `origin` has **two push URLs**, so one `git push origin main` updates both. Fetch is Bitbucket-only. |
| Only `main` migrated | The ~110 merged PR branches were **squash-merged**, so their content is already in `main`. Their tips stay on the GitHub mirror. `main`'s full commit history is preserved byte-for-byte. |
| Issues move to the Bitbucket tracker | Only the **1 open** issue (GH#194) needed recreating; the other 83 were closed. All 84 issues + 110 PRs are archived in [`history/`](history/). |
| CI ported to Bitbucket Pipelines | [`../bitbucket-pipelines.yml`](../bitbucket-pipelines.yml) is the merge gate. `.github/workflows/ci.yml` is retained **only** so the mirror stays green; it is not the gate. |
| Render demo left pointing at GitHub | No Render reconfiguration, no downtime for the public demo. |

### `#N` is now ambiguous — the one trap worth internalising

GitHub numbers issues **and** PRs in a single sequence (this repo's `#193` is a PR, `#194` an issue).
Bitbucket numbers issues and PRs **separately, each from 1**. So Bitbucket issue IDs could never line
up with the GitHub numbers, and ~110 merged commit messages already contain bare `#N`.

The convention (also in `CLAUDE.md`): **a bare `#N` written before the migration means the GitHub
sequence**, resolvable in [`history/github-issues.md`](history/github-issues.md) and
[`history/github-pull-requests.md`](history/github-pull-requests.md). A bare `#N` written after means
a Bitbucket issue. When citing a pre-migration item from now on, write `GH#194`.

### What Bitbucket's tracker cannot carry

- **No free-form labels.** `type:*` maps onto Bitbucket's fixed `kind`
  (`type:fix`→`bug`, `type:feat`/`type:perf`→`enhancement`, `type:chore`/`type:test`→`task`).
  `area:*` has no equivalent — components must be pre-created in repo settings and are read-only over
  the API — so it goes in the issue body instead.
- **No author/date preservation.** Recreated issues are authored by the migrating user, dated now.
  The originals go in a provenance footer.
- **No `Closes #N` automation.** Bitbucket will not close an issue from a PR body. Resolving is a
  separate, deliberate step after merge.

## What changed in the repo

| Path | Change |
|---|---|
| [`../bitbucket-pipelines.yml`](../bitbucket-pipelines.yml) | **New.** Port of the GitHub Actions CI. |
| [`../scripts/wait_for_db.py`](../scripts/wait_for_db.py) | **New.** Postgres readiness gate — Pipelines has no service health-checks. |
| [`../scripts/migrate_issues_to_bitbucket.py`](../scripts/migrate_issues_to_bitbucket.py) | **New.** One-shot issue recreation via the Bitbucket REST API. |
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

The **REST API** (issue migration, opening PRs) has no equivalent of the git helper and always needs
the token explicitly. These are developer-shell credentials, **not app config** — nothing under
`src/uta/` reads them, so they are deliberately absent from `config.py` and `.env.example`. Export
them from your shell profile, not `.env`:

```bash
export BITBUCKET_EMAIL='kevin.palm@labsolution.lu'
export BITBUCKET_TOKEN='<api-token>'
```

**A git-push token is not enough, and two things bite here:**

1. **The username differs by transport.** Git over HTTPS accepts the Bitbucket *username*
   (`kpa_labsolution`); the REST API rejects it with `API token must be used with an atlassian
   registered email` and requires the **Atlassian account email**.
2. **Scopes.** The credential already stored in this devcontainer is git-only — it returns `403` on
   `/2.0/user`, `/pullrequests`, `/issues` and `/pipelines_config` while `GET /2.0/repositories/…`
   succeeds. A token for the API work needs **pull-request write** and **issue write**
   (`write:pullrequest:bitbucket` / `write:issue:bitbucket` on a scoped Atlassian API token;
   `pullrequest:write` / `issue:write` on a repository or workspace access token).
3. **Admin is a separate tier.** Enabling the **issue tracker** *or* **Pipelines** over the API needs
   repository **admin**, which a pull-request/issue-write token does not carry — both `PUT`s answer
   `Your credentials lack one or more required privilege scopes`. Do these two in the UI (§4) unless
   you deliberately mint an admin-scoped token.
4. **`410 Gone` on `/issues` means the tracker is switched off**, not that the token is wrong. It is
   easy to misread as an auth failure while `/pullrequests` returns `200` with the same credential.

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
4. **Issue tracker** — the migration script enables it via the API; otherwise Repository settings →
   Issue tracker → enable.

### 5. Migrate the issues

```bash
python scripts/migrate_issues_to_bitbucket.py labsolutionlu lx-ci-monitor --dry-run
python scripts/migrate_issues_to_bitbucket.py labsolutionlu lx-ci-monitor
```

Add `--include-closed` to also recreate the 83 closed issues as `resolved`. Not recommended: the
archive already holds them, and recreating them makes Bitbucket's IDs diverge further from the
GitHub numbers that the commit history cites.

### 6. Demote GitHub

GitHub must stay **pushable** (the mirror) but stop being a workplace:

1. Remove the required-status-check branch protection on `main` — otherwise mirror pushes are
   rejected once Actions minutes lapse or the workflow is disabled.
2. Repository settings → Features → **uncheck Issues** (the archive is in-tree) and **Wikis**.
3. Edit the GitHub description / add a `MIRROR` note to the top of the README's GitHub view pointing
   at Bitbucket.
4. Leave **Actions enabled** if you want the mirror's CI as a free second opinion; it is not the gate.

Do **not** archive the GitHub repo — archiving makes it read-only and the mirror push would fail,
which also breaks the Render demo deploy.

## Open follow-ups

- **Repo renamed in the move** (`Jenkins-UT-Analyzer` → `lx-ci-monitor`) while the Python package
  stays `uta` and the Render service stays `jenkins-ut-analyzer-demo`. Decide whether to align the
  names, and whether `docs/OVERVIEW.html`'s and the README's product naming should follow.
- **Pipelines vs Jenkins.** [`../DEPLOYMENT-HANDOVER-uta-filled.md`](../DEPLOYMENT-HANDOVER-uta-filled.md)
  states the internal target is Bitbucket + a **DevOps-owned Jenkins** pipeline on RKE2. If DevOps
  runs CI in Jenkins against this repo, `bitbucket-pipelines.yml` becomes a redundant second CI that
  still bills build minutes — at that point either drop it or keep it deliberately as the
  pre-merge gate with Jenkins doing post-merge deploy.
- **Pipelines build minutes** are metered per plan (the free tier is 50 min/month); this suite runs
  several minutes per build across install + lint + tests. Check the workspace plan before relying on
  it as the merge gate.
