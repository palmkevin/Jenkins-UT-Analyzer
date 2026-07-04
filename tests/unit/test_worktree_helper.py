"""Offline checks for the parallel-worktree dev helper (scripts/worktree.sh + Makefile).

These exercise the validation boundary only — the argument parsing and name checks that run
*before* any git/Postgres side effect — so they need neither the `db` server nor a clean git tree.
The end-to-end behaviour (worktree + venv + throwaway DB + migrate) is the issue's manual acceptance
check, not something to reproduce in the offline gate.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "worktree.sh"
_MAKEFILE = _REPO_ROOT / "Makefile"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(_SCRIPT), *args],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_script_is_executable() -> None:
    assert _SCRIPT.exists(), "scripts/worktree.sh is missing"
    assert _SCRIPT.stat().st_mode & 0o111, "scripts/worktree.sh must be executable"


def test_script_has_valid_bash_syntax() -> None:
    assert subprocess.run(["bash", "-n", str(_SCRIPT)]).returncode == 0


def test_no_subcommand_prints_usage_and_fails() -> None:
    result = _run()
    assert result.returncode != 0
    assert "Usage:" in result.stdout


def test_help_is_zero_exit() -> None:
    result = _run("--help")
    assert result.returncode == 0
    assert "Usage:" in result.stdout


def test_add_without_name_fails_fast() -> None:
    result = _run("add")
    assert result.returncode != 0
    assert "is required" in result.stderr


def test_remove_without_name_fails_fast() -> None:
    result = _run("remove")
    assert result.returncode != 0
    assert "is required" in result.stderr


@pytest.mark.parametrize("bad", ["Bad", "a b", "-lead", "under_score!", "café"])
def test_invalid_names_are_rejected_before_side_effects(bad: str) -> None:
    result = _run("add", bad)
    assert result.returncode != 0
    assert "invalid name" in result.stderr


def test_unknown_subcommand_fails() -> None:
    result = _run("frobnicate")
    assert result.returncode != 0
    assert "unknown subcommand" in result.stderr


def test_makefile_exposes_worktree_targets() -> None:
    text = _MAKEFILE.read_text()
    for target in ("worktree:", "worktree-rm:", "worktree-ls:"):
        assert target in text, f"Makefile is missing the `{target[:-1]}` target"


def test_worktrees_dir_is_gitignored() -> None:
    # A path under .worktrees/ must be ignored so worktrees never get committed.
    result = subprocess.run(
        ["git", "check-ignore", ".worktrees/demo"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, ".worktrees/ is not gitignored"


def _call_fn(fn_call: str) -> subprocess.CompletedProcess[str]:
    # Source the script (guarded so `main` does NOT run) and call one helper — no side effects.
    return subprocess.run(
        ["bash", "-c", f"source {_SCRIPT!s}; {fn_call}"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("name", ["demo", "feature-1", "a", "wt-99"])
def test_validate_name_accepts_well_formed_names(name: str) -> None:
    assert _call_fn(f"validate_name {name}").returncode == 0


@pytest.mark.parametrize(
    ("name", "expected"),
    [("demo", "uta_demo"), ("feature-1", "uta_feature_1"), ("a-b-c", "uta_a_b_c")],
)
def test_db_name_maps_hyphens_to_underscores(name: str, expected: str) -> None:
    result = _call_fn(f"db_name {name}")
    assert result.returncode == 0
    assert result.stdout.strip() == expected


def test_url_for_db_swaps_only_the_database_name() -> None:
    base = "postgresql+psycopg://uta:uta@db:5432/uta"
    result = _call_fn(f"url_for_db {base} uta_demo")
    assert result.returncode == 0
    assert result.stdout.strip() == "postgresql+psycopg://uta:uta@db:5432/uta_demo"
