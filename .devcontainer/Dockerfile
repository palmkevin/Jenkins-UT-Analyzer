# Devcontainer base for the `dev` service (see docker-compose.dev.yml).
#
# Why a Dockerfile instead of using the image directly: the upstream
# mcr.microsoft.com/devcontainers/python image ships a Yarn apt source
# (/etc/apt/sources.list.d/yarn.list) whose signing key was rotated upstream, so
# `apt-get update` now fails signature verification (NO_PUBKEY 62D54FD4003F6525).
# That breaks ANY devcontainer feature that runs apt during the build — here the
# docker-outside-of-docker feature aborts, so the container never comes up.
#
# We don't use Yarn, so drop the offending source before the features layer builds
# on top of this image (features run at build time, before any lifecycle command —
# this is the only place to remove it). apt-get update then succeeds.
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

RUN rm -f /etc/apt/sources.list.d/yarn.list

# Pre-create the Claude Code config dir owned by the non-root `vscode` user. The
# claude-code-config named volume (see devcontainer.json) mounts here; Docker seeds a
# NEWLY created volume from the image path, preserving its ownership. Without this dir in
# the image, a fresh volume is created bare + root-owned, and `vscode` can't write its
# credentials there — so `claude` login silently fails to persist. (An already-existing
# root-owned volume is not re-seeded: remove it with `docker volume rm
# jenkins-ut-analyzer-dev_claude-code-config`, or chown it once inside the container.)
RUN mkdir -p /home/vscode/.claude && chown vscode:vscode /home/vscode/.claude

# Same treatment for the gh-config named volume (mounts at ~/.config/gh): pre-create the dir
# vscode-owned so a freshly created volume seeds with the right ownership and `gh auth login`
# can persist its token. (~/.config itself must exist and be vscode-owned too.)
RUN mkdir -p /home/vscode/.config/gh && chown -R vscode:vscode /home/vscode/.config

# Bake Claude Code's permission mode into the image so the devcontainer runs prompt-free.
# /etc/claude-code/managed-settings.json is the Linux MANAGED-settings path — highest precedence,
# and (unlike ~/.claude or the workspace) NOT shadowed by any bind mount or named volume, so the
# image copy is what's read at runtime. bypassPermissions is sanctioned precisely for isolated
# containers like this one; `rm -rf /`/`~` and the repo's `deny` rules still prompt/block as a
# circuit-breaker. This lives ONLY inside the image (never on the host tree, never committed as a
# loose file), so it supersedes the need for a hand-maintained `permissions.allow` list in
# .claude/settings.json for devcontainer work.
RUN mkdir -p /etc/claude-code \
 && printf '%s\n' \
      '{' \
      '  "permissions": {' \
      '    "defaultMode": "bypassPermissions"' \
      '  }' \
      '}' \
      > /etc/claude-code/managed-settings.json
