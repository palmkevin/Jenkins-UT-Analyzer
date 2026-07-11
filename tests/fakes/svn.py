"""Fake implementing the SvnBlameClient protocol — no `svn`, no network in the offline suite."""

from __future__ import annotations


class FakeSvnBlameClient:
    """Return a canned main developer per repo path (``mapping``), else ``default``.

    Records every path it is asked about in ``calls`` so tests can assert the per-path caching the
    resolver does (one blame per unique file, not per test).
    """

    def __init__(
        self, mapping: dict[str, str | None] | None = None, *, default: str | None = None
    ) -> None:
        self._mapping = mapping or {}
        self._default = default
        self.calls: list[str] = []

    def main_developer(self, repo_path: str) -> str | None:
        self.calls.append(repo_path)
        return self._mapping.get(repo_path, self._default)
