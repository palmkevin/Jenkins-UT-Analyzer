"""Per-test relevance ranking of a run's change candidates (issue #50).

The persisted candidates (:mod:`uta.models.signals`) are **run-windowed** — every failure in the
run shares the same flat list. This module scores each candidate against *one* failing test so the
test record, the classifier tie-break and the LLM prompt can lead with the likely culprit:

- **Code candidates** (SVN revisions): each changed path is matched against the failing test's own
  source location, its stack-frame paths, and the module implied by its class name. Changed paths
  and test frames live under different roots (``/trunk/lx/…`` vs ``…/release/<track>/tests/dev/…``),
  so matching compares **trailing path segments**: file name *plus* parent directory is a module
  match; a bare file-name match is weaker; sharing only a package directory is weaker still.
- **Data candidates** (``ut_ref`` ``V_TRACKING`` rows): the changed entity table code (and the
  component name) matched as a whole word against the failure's error text — a test that names the
  entity it choked on names its own suspect. Only the already-persisted key/author fields are ever
  read; raw ``MODDATA`` is never stored, so it cannot surface here.

Scores are deliberately coarse **tiers**, not probabilities — enough to order candidates and to
break the classifier's "both kinds present" tie, without pretending to a confidence model the KB
can't back yet. Everything is pure and deterministic: no I/O, no clock.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uta.models.signals import CodeChangeCandidate, DataChangeCandidate

# Score tiers, most specific first. A module match (file name + parent directory) is near-certain
# to be the test's own code; a bare file-name match may collide across packages; a shared package
# directory is only a neighbourhood hint.
SCORE_MODULE = 3.0
SCORE_FILE = 2.0
SCORE_PACKAGE = 1.0
SCORE_ENTITY = 3.0
SCORE_COMPONENT = 2.0

# Any traceback frame path — broader than ut_report's dev-test frame regex on purpose: product
# frames under the release tree are just as good an anchor for path matching.
_FRAME_PATH = re.compile(r'File "([^"]+)"')
# Volatile leading path of an in-tree frame (mirrors kb.signature) — only the stable module-relative
# suffix should take part in package matching.
_STRIP_PREFIX = re.compile(r"^.*?/(?:release/[^/]+|tests/dev)/")
# Directory names too generic to indicate a package relationship.
_GENERIC_DIRS = frozenset({"trunk", "branches", "tags", "lx", "src", "tests", "test", "dev"})
# File names shared by every package — a name-only match on these means nothing.
_GENERIC_FILES = frozenset({"__init__.py", "conftest.py", "setup.py"})


@dataclass(frozen=True)
class RankedCodeChange:
    """One SVN candidate scored against a single failing test (plain fields, no ORM refs)."""

    revision: str | None
    author: str | None
    message: str | None
    committed_at: datetime
    score: float
    reasons: tuple[str, ...]  # human-readable match reasons; empty when nothing matched


@dataclass(frozen=True)
class RankedDataChange:
    """One ``ut_ref`` candidate scored against a single failing test.

    Field set is the medical-data allowlist: entity key, change type, component, author, timestamp
    — never row content (``MODDATA`` is not even persisted upstream).
    """

    entity: str
    pk: str | None
    change_type: str
    component: str | None
    author: str | None
    changed_at: datetime
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RankedChanges:
    """Both candidate lists, most relevant first (ties stay chronological)."""

    code: tuple[RankedCodeChange, ...]
    data: tuple[RankedDataChange, ...]

    @property
    def code_relevant(self) -> bool:
        return any(c.score > 0 for c in self.code)

    @property
    def data_relevant(self) -> bool:
        return any(d.score > 0 for d in self.data)

    @property
    def top_code(self) -> RankedCodeChange | None:
        return self.code[0] if self.code else None

    @property
    def top_data(self) -> RankedDataChange | None:
        return self.data[0] if self.data else None


def _segments(path: str) -> tuple[str, ...]:
    return tuple(seg for seg in path.replace("\\", "/").lower().split("/") if seg)


def _tail_overlap(a: tuple[str, ...], b: tuple[str, ...]) -> int:
    """How many trailing path segments two paths share (0 = not even the file name)."""
    n = 0
    for seg_a, seg_b in zip(reversed(a), reversed(b), strict=False):
        if seg_a != seg_b:
            break
        n += 1
    return n


def _module_file(class_name: str | None) -> str | None:
    """``ut_billing.bi_round.TestClass`` -> ``ut_billing/bi_round.py`` (drop the class)."""
    if not class_name or "." not in class_name:
        return None
    module = class_name.rsplit(".", 1)[0]
    return module.replace(".", "/") + ".py"


def _reference_paths(
    file_path: str | None, error_stack_trace: str | None, class_name: str | None
) -> list[tuple[str, ...]]:
    """The failing test's own path shapes: report location, stack frames, class-derived module."""
    raw: list[str] = []
    if file_path:
        raw.append(file_path)
    if error_stack_trace:
        raw.extend(_FRAME_PATH.findall(error_stack_trace))
    module = _module_file(class_name)
    if module:
        raw.append(module)
    seen: set[tuple[str, ...]] = set()
    refs: list[tuple[str, ...]] = []
    for path in raw:
        segs = _segments(path)
        if segs and segs not in seen:
            seen.add(segs)
            refs.append(segs)
    return refs


def _package_dirs(refs: Iterable[tuple[str, ...]]) -> set[str]:
    """Package directories of the test's module-relative paths (generic dirs dropped)."""
    dirs: set[str] = set()
    for segs in refs:
        relative = _segments(_STRIP_PREFIX.sub("", "/".join(segs)))
        dirs.update(seg for seg in relative[:-1] if seg not in _GENERIC_DIRS)
    return dirs


def _candidate_files(paths_json: str | None) -> list[str]:
    if not paths_json:
        return []
    try:
        entries = json.loads(paths_json)
    except (ValueError, TypeError):
        return []
    if not isinstance(entries, list):
        return []
    return [e.get("file", "") for e in entries if isinstance(e, dict) and e.get("file")]


def _score_code(
    paths_json: str | None,
    refs: list[tuple[str, ...]],
    packages: set[str],
) -> tuple[float, tuple[str, ...]]:
    """Best match tier of one commit's changed paths against the failing test's paths."""
    score = 0.0
    reasons: list[str] = []
    for file in _candidate_files(paths_json):
        segs = _segments(file)
        if not segs:
            continue
        best_overlap = max((_tail_overlap(segs, ref) for ref in refs), default=0)
        if best_overlap >= 2:
            tier, reason = SCORE_MODULE, f"changed {file} matches the failing test's module"
        elif best_overlap == 1 and segs[-1] not in _GENERIC_FILES:
            tier, reason = SCORE_FILE, f"changed {file} matches a stack-trace file name"
        else:
            pkg = next((p for p in sorted(packages) if p in segs[:-1]), None)
            if pkg is None:
                continue
            tier, reason = SCORE_PACKAGE, f"changed {file} touches the test's package '{pkg}'"
        if tier > score:
            score = tier
        if reason not in reasons:
            reasons.append(reason)
    return score, tuple(reasons[:3])


def _word_mentioned(word: str | None, text: str) -> bool:
    if not word or len(word) < 3:
        return False
    return re.search(rf"\b{re.escape(word)}\b", text, flags=re.IGNORECASE) is not None


def _score_data(
    entity: str, component: str | None, error_text: str
) -> tuple[float, tuple[str, ...]]:
    """Entity/component mention of one ``ut_ref`` change in the failure's error text."""
    score = 0.0
    reasons: list[str] = []
    if _word_mentioned(entity, error_text):
        score = SCORE_ENTITY
        reasons.append(f"entity {entity} mentioned in the error text")
    if _word_mentioned(component, error_text):
        score = max(score, SCORE_COMPONENT)
        reasons.append(f"component {component} mentioned in the error text")
    return score, tuple(reasons)


def rank_candidates(
    code_candidates: Iterable[CodeChangeCandidate],
    data_candidates: Iterable[DataChangeCandidate],
    *,
    file_path: str | None = None,
    error_details: str | None = None,
    error_stack_trace: str | None = None,
    class_name: str | None = None,
) -> RankedChanges:
    """Score a run's candidates against one failing test and return them most-relevant first.

    The failure context is optional field by field — with nothing to match against every score is
    0 and the lists stay chronological (the run-windowed v1 presentation).
    """
    refs = _reference_paths(file_path, error_stack_trace, class_name)
    packages = _package_dirs(refs)
    error_text = "\n".join(t for t in (error_details, error_stack_trace) if t)

    code: list[RankedCodeChange] = []
    for c in code_candidates:
        score, reasons = _score_code(c.paths, refs, packages)
        code.append(
            RankedCodeChange(
                revision=c.revision or c.commit_id,
                author=c.author,
                message=c.message,
                committed_at=c.committed_at,
                score=score,
                reasons=reasons,
            )
        )
    data: list[RankedDataChange] = []
    for d in data_candidates:
        score, reasons = _score_data(d.lx_table_code, d.component_name, error_text)
        data.append(
            RankedDataChange(
                entity=d.lx_table_code,
                pk=d.pk_lst,
                change_type=d.change_type,
                component=d.component_name,
                author=d.author,
                changed_at=d.changed_at,
                score=score,
                reasons=reasons,
            )
        )
    code.sort(key=lambda c: (-c.score, c.committed_at))
    data.sort(key=lambda d: (-d.score, d.changed_at))
    return RankedChanges(code=tuple(code), data=tuple(data))
