"""SVN blame access — resolves a test's **main developer** (issue #114).

"Owner" in the dashboard is the test's main developer: the author who wrote most of the test's
source file, per ``svn blame``. This is the seam for that lookup — the same interface/fake shape as
the Oracle feed (:mod:`uta.refdb.oracle`): production uses :class:`SvnCliBlameClient` (shells out to
the ``svn`` CLI), the offline suite/demo use a fixtures-backed fake.

Gated by ``SVN_BLAME_ENABLED`` (default off) — with it off no ``SvnBlameClient`` is built, so the
offline gate, local dev and the public demo never touch SVN, exactly like the Oracle/LLM live paths.
Every failure mode (network down, missing path, no ``svn`` binary, unparsable output) resolves to
``None`` — a missing owner never fails an ingest.
"""

from __future__ import annotations

import logging
import re
import subprocess
from collections import defaultdict
from typing import Protocol
from xml.etree import ElementTree

logger = logging.getLogger(__name__)

# The stable, module-relative suffix of a test's source path begins at ``tests/dev/`` — the leading
# path is volatile (build-checkout roots like ``…/release/<track>/``), so only the suffix maps into
# the SVN repo. Mirrors uta.analyze.relevance's prefix handling.
_TEST_ROOT_MARKER = re.compile(r"(?:^|/)(tests/dev/.*)$")


class SvnBlameClient(Protocol):
    def main_developer(self, repo_path: str) -> str | None:
        """The author of the most blamed lines in ``repo_path``, or ``None`` if undeterminable."""
        ...


def to_repo_path(file_path: str | None) -> str | None:
    """A test's source ``file_path`` -> its repo-relative path (from ``tests/dev/`` onward).

    ``file_path`` comes from the failing test's stack frame, e.g.
    ``/…/release/permanent/tests/dev/ut_core/co_time.py`` -> ``tests/dev/ut_core/co_time.py``.
    Returns ``None`` when the path has no ``tests/dev/`` segment (nothing blameable).
    """
    if not file_path:
        return None
    m = _TEST_ROOT_MARKER.search(file_path.replace("\\", "/"))
    return m.group(1) if m else None


def main_developer_from_blame_xml(xml_text: str) -> str | None:
    """Tally ``svn blame --xml`` output into the modal author (most authored lines).

    Lines with no committed author (local uncommitted mods) are ignored. Ties break toward the more
    recently active author (highest revision), then author name — deterministic regardless of line
    order. Returns ``None`` when there are no attributable lines or the XML is unparsable.
    """
    try:
        # Trusted input: this is our own `svn` CLI's output, not attacker-controlled.
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return None
    lines: dict[str, int] = defaultdict(int)
    last_rev: dict[str, int] = defaultdict(int)
    for commit in root.iter("commit"):
        author_el = commit.find("author")
        if author_el is None or not (author_el.text or "").strip():
            continue
        author = author_el.text.strip()
        lines[author] += 1
        try:
            rev = int(commit.get("revision", "0"))
        except ValueError:
            rev = 0
        last_rev[author] = max(last_rev[author], rev)
    if not lines:
        return None
    return max(lines, key=lambda a: (lines[a], last_rev[a], a))


class SvnCliBlameClient:
    """Live ``svn blame`` via the ``svn`` CLI (read-only, non-interactive).

    ``base_url`` is the SVN URL under which the repo-relative ``tests/dev/…`` paths resolve, e.g.
    ``https://svn.example/svn/ls/trunk/lx``. Credentials are optional (anonymous read works on some
    repos). Each call is a single ``svn blame --xml`` of one file; the caller caches per path.
    """

    def __init__(
        self,
        base_url: str,
        *,
        username: str = "",
        password: str = "",
        svn_binary: str = "svn",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._svn = svn_binary
        self._timeout = timeout_seconds

    def _url(self, repo_path: str) -> str:
        return f"{self._base_url}/{repo_path.lstrip('/')}"

    def main_developer(self, repo_path: str) -> str | None:
        cmd = [self._svn, "blame", "--xml", "--non-interactive", "--no-auth-cache"]
        if self._username:
            cmd += ["--username", self._username, "--password", self._password]
        cmd.append(self._url(repo_path))
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self._timeout, check=False
            )
        except (OSError, subprocess.SubprocessError) as exc:
            logger.debug("svn blame failed for %s: %s", repo_path, exc)
            return None
        if proc.returncode != 0:
            logger.debug(
                "svn blame non-zero (%d) for %s: %s",
                proc.returncode,
                repo_path,
                proc.stderr.strip(),
            )
            return None
        return main_developer_from_blame_xml(proc.stdout)
