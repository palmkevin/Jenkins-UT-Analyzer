#!/usr/bin/env bash
# ─── Dev container post-create ────────────────────────────────────────────────
# Runs once, after the container is created (devcontainer.json postCreateCommand).
# Extracted from the JSON one-liner this replaced, which had grown to six chained
# commands with no room for a comment explaining any of them.
#
# Steps 1-2 are load-bearing — if the install or the migration fails, container
# creation should fail loudly. Steps 3-4 are conveniences and are guarded, so a
# missing plugin or credential store never costs you a working container.
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

CRED_DIR=/home/vscode/.config/git

# ─── 1. SSH -> HTTPS remote rewrites ──────────────────────────────────────────
# Container-local (~/.gitconfig, not the bind-mounted .git) so plain git push/fetch
# use HTTPS credentials: the container has no forwarded SSH agent, so a `git@…:`
# URL fails with `Permission denied (publickey)`. bitbucket.org is the one that
# matters (it is the canonical remote); github.com is kept because the read-only
# mirror is still a push target. A host clone that legitimately uses SSH is
# unaffected, since this is container-local.
git config --global url.https://bitbucket.org/.insteadOf git@bitbucket.org:
git config --global url.https://github.com/.insteadOf git@github.com:

# ─── 2. Python env ────────────────────────────────────────────────────────────
# Match CI's install exactly (bitbucket-pipelines.yml), then bring the schema to
# head against the compose `db`.
pip install -e '.[dev]'
uta migrate

# ─── 3. Atlassian tooling ─────────────────────────────────────────────────────
# The ls-atlassian plugin (Bitbucket/Jira/Confluence) plus its one dependency.
# Here rather than in the Dockerfile: it installs into ~/.claude, which the
# `claude-code-config` volume shadows — an image layer would only ever seed an
# *empty* volume and then silently freeze at that version — and its marketplace is
# a private Bitbucket repo, so the clone needs credentials that do not exist at
# build time, reached via the rewrite step 1 just applied. `requests` is not a
# project dependency, and the plugin's shared lib hard-exits without it.
pip install requests || true
claude plugin marketplace add git@bitbucket.org:labsolutionlu/ai-marketplace.git || true
claude plugin install ls-atlassian@labsolution-plugins --scope user || true

# ─── 4. Make the git-credentials volume usable ────────────────────────────────
# The volume mounts empty *and* root-owned — the image has no ~/.config/git for
# Docker to copy ownership from — so git's `store` helper could never write there
# as `vscode`. That is why the "one-time token" step promised in devcontainer.json
# never actually happened, and why pushing fell back to the VS Code relay (which
# only forwards credentials the *host* holds, and the host holds none for
# bitbucket.org).
sudo -n chown -R vscode:vscode "$CRED_DIR" ||
  echo "post-create: could not chown $CRED_DIR — push credentials will not persist" >&2

# URL-scoped rather than the generic `credential.helper`: that key belongs to the
# Dev Containers extension, which points it at a per-session relay script and
# rewrites it on every start, so anything we put there would be clobbered. A
# `credential.<url>.helper` entry is a separate key, consulted *in addition* to
# the relay — the relay still answers for every other host, and the store answers
# for bitbucket.org once the relay comes up empty.
#
# The store starts empty by design. The first `git push` to Bitbucket prompts for
# username + password: give your Atlassian account email and an API token (not a
# password — Bitbucket retired those). The helper writes it to $CRED_DIR/credentials
# and, now that the volume is writable, it survives every later rebuild. Rotate by
# deleting that file and pushing again.
git config --global "credential.https://bitbucket.org.helper" "store --file=$CRED_DIR/credentials"
