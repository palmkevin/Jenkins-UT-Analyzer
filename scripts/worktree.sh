#!/usr/bin/env bash
#
# Manage parallel in-container git worktrees for local dev (see CLAUDE.md "worktrees").
#
# One devcontainer, many worktrees under .worktrees/<name>. Each gets its own editable venv (the
# `pip install -e` pins a single source path, so worktrees can't share one) and its own throwaway
# Postgres database `uta_<name>` on the shared compose `db` server, so parallel `pytest -m "not
# live"` runs — including the destructive migration test — never contend.
#
# Usage:
#   scripts/worktree.sh add <name>       # create .worktrees/<name>, its venv, DB, and migrate it
#   scripts/worktree.sh remove <name>    # git worktree remove + dropdb (teardown)
#   scripts/worktree.sh list             # list existing worktrees
#
# <name> must match [a-z0-9][a-z0-9-]* (a valid git branch leaf). The throwaway DB is
# `uta_<name>` with '-' mapped to '_' (a clean unquoted Postgres identifier).
#
# There is no postgresql-client in the image, so CREATE/DROP DATABASE go through psycopg (already a
# project dependency), reached via the base DATABASE_URL the devcontainer exports.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
WORKTREES_DIR="$REPO_ROOT/.worktrees"

die() { echo "worktree: $*" >&2; exit 1; }

# Validate a worktree name up front (before any git/pg side effect) so the tests can exercise this
# path offline and a typo fails fast.
validate_name() {
  local name="${1:-}"
  [[ -n "$name" ]] || die "a <name> is required (e.g. \`make worktree name=demo\`)"
  [[ "$name" =~ ^[a-z0-9][a-z0-9-]*$ ]] \
    || die "invalid name '$name' — use lowercase letters, digits and '-' (must start alphanumeric)"
}

db_name() {  # <name> -> uta_<name with - mapped to _>
  echo "uta_${1//-/_}"
}

# Base DATABASE_URL used to reach the shared `db` server. The devcontainer exports it (it overrides
# any .env value in pydantic-settings), so prefer the environment; fall back to the repo .env, then
# the compose default. We swap only the database name for the per-worktree throwaway DB.
base_url() {
  if [[ -n "${DATABASE_URL:-}" ]]; then
    printf '%s' "$DATABASE_URL"
  elif [[ -f "$REPO_ROOT/.env" ]] && grep -qE '^DATABASE_URL=' "$REPO_ROOT/.env"; then
    grep -E '^DATABASE_URL=' "$REPO_ROOT/.env" | head -1 | cut -d= -f2-
  else
    printf 'postgresql+psycopg://uta:uta@db:5432/uta'
  fi
}

# Rewrite a DATABASE_URL to point at a different database name, preserving driver/host/port/creds.
url_for_db() {  # <base-url> <db-name>
  python - "$1" "$2" <<'PY'
import sys
from sqlalchemy.engine import make_url
print(make_url(sys.argv[1]).set(database=sys.argv[2]).render_as_string(hide_password=False))
PY
}

# Run one CREATE/DROP DATABASE statement via psycopg (autocommit — these can't run in a transaction),
# connected to the base server's maintenance DB (you can't create/drop the database you're in).
pg_admin() {  # <sql>
  python - "$(base_url)" "$1" <<'PY'
import sys
import psycopg
from sqlalchemy.engine import make_url
url = make_url(sys.argv[1])
dsn = (
    f"host={url.host} port={url.port or 5432} "
    f"user={url.username} password={url.password} dbname={url.database}"
)
with psycopg.connect(dsn, autocommit=True) as conn:
    conn.execute(sys.argv[2])
PY
}

cmd_add() {
  local name="$1"
  validate_name "$name"
  local dir="$WORKTREES_DIR/$name"
  local db; db="$(db_name "$name")"

  [[ -e "$dir" ]] && die "$dir already exists — remove it first (\`make worktree-rm name=$name\`)"
  git show-ref --verify --quiet "refs/heads/$name" \
    && die "branch '$name' already exists — pick another name or delete the branch"

  echo "==> git worktree add $dir -b $name origin/main"
  git -C "$REPO_ROOT" fetch --quiet origin main || echo "    (fetch skipped — using local origin/main)"
  git -C "$REPO_ROOT" worktree add "$dir" -b "$name" origin/main

  echo "==> creating venv + editable install (.[dev]) in $dir/.venv"
  python -m venv "$dir/.venv"
  "$dir/.venv/bin/pip" install --quiet --upgrade pip
  "$dir/.venv/bin/pip" install --quiet -e "$dir[dev]"

  echo "==> writing $dir/.env (DATABASE_URL -> $db)"
  local wt_url; wt_url="$(url_for_db "$(base_url)" "$db")"
  if [[ -f "$REPO_ROOT/.env" ]]; then
    grep -vE '^DATABASE_URL=' "$REPO_ROOT/.env" > "$dir/.env"
  else
    : > "$dir/.env"
  fi
  echo "DATABASE_URL=$wt_url" >> "$dir/.env"

  # The devcontainer exports DATABASE_URL container-wide, which outranks the .env file in
  # pydantic-settings. So teach the venv's activate to export the per-worktree URL: `source
  # .venv/bin/activate` then makes both the interpreter and DATABASE_URL point at this worktree.
  cat >> "$dir/.venv/bin/activate" <<EOF

# Added by scripts/worktree.sh: point this worktree's shell at its own throwaway database.
export DATABASE_URL="$wt_url"
EOF

  echo "==> createdb $db + uta migrate"
  pg_admin "CREATE DATABASE $db"
  ( cd "$dir" && DATABASE_URL="$wt_url" "$dir/.venv/bin/uta" migrate )

  cat <<EOF

worktree ready: $dir  (branch $name, db $db)
  cd $dir
  source .venv/bin/activate       # activates the venv AND sets DATABASE_URL=$db
  pytest -m "not live"
EOF
}

cmd_remove() {
  local name="$1"
  validate_name "$name"
  local dir="$WORKTREES_DIR/$name"
  local db; db="$(db_name "$name")"

  echo "==> git worktree remove $dir (and branch $name)"
  git -C "$REPO_ROOT" worktree remove --force "$dir" 2>/dev/null || echo "    (no worktree at $dir)"
  git -C "$REPO_ROOT" branch -D "$name" 2>/dev/null || true

  echo "==> dropdb $db"
  # WITH (FORCE) terminates any lingering connection so the drop can't hang (Postgres 13+).
  pg_admin "DROP DATABASE IF EXISTS $db WITH (FORCE)"
  echo "removed."
}

cmd_list() {
  git -C "$REPO_ROOT" worktree list
}

main() {
  local sub="${1:-}"
  case "$sub" in
    add)    shift; cmd_add "${1:-}" ;;
    remove) shift; cmd_remove "${1:-}" ;;
    list)   cmd_list ;;
    ""|-h|--help)
      grep -E '^#( |$)' "$0" | sed 's/^# \{0,1\}//'
      [[ -z "$sub" ]] && exit 2 || exit 0 ;;
    *) die "unknown subcommand '$sub' (expected add|remove|list)" ;;
  esac
}

# Only drive from argv when executed directly; when sourced (e.g. from tests) just define functions.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
