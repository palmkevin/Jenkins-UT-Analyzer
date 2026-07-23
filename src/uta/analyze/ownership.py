"""Resolve each test's **main developer** from ``svn blame`` (issue #114).

"Owner" in the dashboard is the developer who wrote most of a test's source file. This module maps a
test's source path to its repo-relative path, blames it via a :class:`~uta.refdb.svn.SvnBlameClient`
and stores the modal author on ``TestIdentity.main_developer`` (an identity-level property of the
source file, not of any single build).

Two entry points share one resolver:
- :func:`resolve_for_cases` — called from the ingest pipeline for the build's *failing* tests (only
  failures carry a source path), so new owners appear incrementally.
- :func:`resolve_all` — the ``uta reattribute-owners`` backfill over the whole store.

Both cache blame per repo path (many tests share a file) and, by default, only fill identities whose
owner is still unknown — ``refresh=True`` re-blames everything. A blame that yields nothing leaves
the owner untouched.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from uta.models import TestIdentity, TestResult
from uta.refdb.svn import SvnBlameClient, to_repo_path

if TYPE_CHECKING:
    from uta.ingest.ut_report import TestCaseResult

_CHUNK = 1000


def _resolve_pairs(pairs: list[tuple[TestIdentity, str]], client: SvnBlameClient) -> int:
    """Blame each (identity, source path), setting ``main_developer``. Returns the count set.

    Blame results are cached per repo path — sibling tests in one file cost a single ``svn blame``.
    """
    cache: dict[str, str | None] = {}
    resolved = 0
    for ident, file_path in pairs:
        repo_path = to_repo_path(file_path)
        if repo_path is None:
            continue
        if repo_path not in cache:
            cache[repo_path] = client.main_developer(repo_path)
        developer = cache[repo_path]
        if developer:
            ident.main_developer = developer
            resolved += 1
    return resolved


def resolve_for_cases(
    identities: dict[str, TestIdentity],
    cases: list[TestCaseResult],
    client: SvnBlameClient,
    *,
    refresh: bool = False,
) -> int:
    """Resolve owners for the build's failing tests (called from the pipeline). Returns count set.

    ``identities`` is the pipeline's ``canonical_name -> TestIdentity`` map. Only failing cases with
    a parsed source path are blameable; each identity is resolved once per build.
    """
    pairs: list[tuple[TestIdentity, str]] = []
    seen: set[str] = set()
    for case in cases:
        if not case.failed or not case.file_path:
            continue
        ident = identities.get(case.test_id)
        if ident is None or ident.canonical_name in seen:
            continue
        if not refresh and ident.main_developer is not None:
            continue
        seen.add(ident.canonical_name)
        pairs.append((ident, case.file_path))
    return _resolve_pairs(pairs, client)


def _latest_source_paths(session: Session, identity_ids: list[int]) -> dict[int, str]:
    """Each identity's most recent failing-result source path (newest build wins)."""
    paths: dict[int, str] = {}
    for start in range(0, len(identity_ids), _CHUNK):
        chunk = identity_ids[start : start + _CHUNK]
        rows = session.execute(
            select(TestResult.test_identity_id, TestResult.file_path)
            .where(
                TestResult.test_identity_id.in_(chunk),
                TestResult.file_path.is_not(None),
            )
            .order_by(TestResult.test_identity_id, TestResult.build_id.desc())
        ).all()
        for tid, file_path in rows:
            if tid not in paths:
                paths[tid] = file_path
    return paths


def resolve_all(
    session: Session,
    client: SvnBlameClient,
    *,
    refresh: bool = False,
    limit: int | None = None,
) -> int:
    """Backfill ``main_developer`` across the store from each test's source file. Returns count set.

    By default only identities with no owner yet are resolved; ``refresh=True`` re-blames all.
    ``limit`` caps how many identities are attempted (a sampled/first pass).
    """
    idents = list(session.scalars(select(TestIdentity)).all())
    if not refresh:
        idents = [i for i in idents if i.main_developer is None]
    paths = _latest_source_paths(session, [i.id for i in idents])
    pairs = [(i, paths[i.id]) for i in idents if paths.get(i.id)]
    if limit is not None:
        pairs = pairs[:limit]
    return _resolve_pairs(pairs, client)
