# Human-facing names align on `lx-ci-monitor`; identity keys stay pinned

The Bitbucket migration renamed the repo `Jenkins-UT-Analyzer` → `lx-ci-monitor` and left the tool
answering to four names: the Bitbucket repo `lx-ci-monitor`, the Python package `uta`, the Render
service `jenkins-ut-analyzer-demo`, and the devcontainer's `name` / `workspaceFolder`
`Jenkins-UT-Analyzer`. Nothing was broken, but four names for one tool is a tax on every doc and
every new reader (the `naming-alignment` item in OPEN-WORK.md). This ADR settles it.

We decided to split the names into two classes and treat them differently.

**Human-facing labels align on `lx-ci-monitor`.** These exist to be read, so they should match the
repo. Changed: `.devcontainer/devcontainer.json` `name` and `workspaceFolder` (now
`/workspaces/lx-ci-monitor`), and the matching bind-mount target in
`.devcontainer/docker-compose.dev.yml`. Cost is one **Rebuild Container**: the editable install
(`pip install -e '.[dev]'`) pins an absolute source path, so `import uta` breaks in a container that
outlives the rename until `postCreateCommand` re-runs — which a rebuild does. Existing
`.worktrees/<x>` would need `git worktree repair` plus a venv reinstall for the same reason (there
were none at the time of the rename).

**Identity keys stay as they are, and are now pinned rather than inferred.** A name that some system
uses as a *key* cannot be renamed without moving or losing the thing it keys:

- **The deployment compose project `jenkins-ut-analyzer`.** It was never configured — compose derived
  it from the directory basename, and the live stack was first brought up from
  `/workspaces/Jenkins-UT-Analyzer`. Its data sits in the project-prefixed volume
  `jenkins-ut-analyzer_pgdata`. So a path rename would have made the next `docker compose up` start a
  *second*, empty stack while the real one kept running orphaned. It is now pinned as a top-level
  `name:` in `docker-compose.yml`, which also fixes the pre-existing latent version of the same bug:
  the host clone was already `lx-ci-monitor`, so a host-side `up` would have done exactly that.

- **The devcontainer compose project `jenkins-ut-analyzer-dev`.** Same mechanism, worse blast radius:
  it prefixes `…-dev_claude-code-config`, `…-dev_gh-config` and `…-dev_git-credentials`, so renaming
  it mounts three empty volumes and silently discards the Claude Code login, the `gh` token and the
  Bitbucket credential store that `devcontainer.json` goes to some length to persist. The name only
  has to be *distinct* from the deployment's, which it is.

- **The Render service `jenkins-ut-analyzer-demo`.** Its name *is* the public URL
  (`https://jenkins-ut-analyzer-demo.onrender.com`), cited in CLAUDE.md, README.md and
  OVERVIEW.html. Render keys blueprint services by name, so changing `render.yaml` would create a
  new free service and leave the old one to be deleted by hand — paying a broken public link for a
  cosmetic gain.

- **The Python package `uta`** (`src/uta/`). It is the import root, the console-script name, the
  entrypoints (`uta.web.app:app`, `uta.demo.app:app`), the Dockerfile `CMD`, the `render.yaml`
  `dockerCommand`, the CI invocations, and every module path in ~200 commits of history. Renaming is
  a repo-wide mechanical churn with no user-visible gain, and `uta` is short and unambiguous inside
  the codebase. It stays.

The rejected alternative was **aligning all four**. It buys one consistent name at the price of a
changed public demo URL, a re-issued set of dev credentials, a hand-deleted Render service, and a
repo-wide import rewrite — with a real chance of orphaning the live database along the way. The
rejected opposite, **recording "keep them divergent" and changing nothing**, leaves the editor title
bar and the container path advertising a repo name that no longer exists, which is the one divergence
a reader trips over daily.

So the standing rule: **a name humans read follows the repo; a name a system keys on gets pinned
where it is, with the reason next to it.**
