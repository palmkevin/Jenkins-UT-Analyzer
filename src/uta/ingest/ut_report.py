"""Parser for the devUTs (nose2) JUnit ``TestResultAction`` JSON.

Source: ``GET /<build>/testReport/api/json``. Two ``nose2-junit`` suites, one per **track**
(``permanent`` / ``permanent_py39``); the same test builds in both. A result is therefore keyed by
``(build, test, track)``. Test identity is the bare ``className.name`` — track is an attribute.

This parser is golden-tested against ``tests/fixtures/jenkins/testReport_1702.json`` (anonymized).
It never touches the network; feed it a parsed JSON dict.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# A track is the bare element among enclosingBlockNames, e.g. "permanent" / "permanent_py39".
_TRACK_RE = re.compile(r"^permanent(?:_py39)?$")
# First stack frame pointing at a dev test file -> the test's own source location.
_TEST_FRAME_RE = re.compile(r'File "([^"]*?/tests/dev/[^"]+\.py)", line (\d+)')
# Marker beginning the "ZEPHYR TEST CASE INFO" block a failing test emits; ids/owner are read from
# after it so stray `LX-T…` mentions elsewhere in the trace can't be mistaken for references.
_ZEPHYR_MARKER = "ZEPHYR TEST CASE INFO"
# A ZEPHYR test-case identifier, e.g. `LX-T4447`. A failing test may reference more than one.
_ZEPHYR_ID_RE = re.compile(r"LX-T\d+")
# ZEPHYR ownership line: `LX-T4447 (kam): "..."` -> (zephyr_id, zephyr_owner). NB: this is the
# owner of the ZEPHYR *test case*, not the developer of the unit test — see #114.
_ZEPHYR_RE = re.compile(r"(LX-T\d+)\s*\(([^)]+)\)")

# Statuses Jenkins reports. REGRESSION/FIXED are vs Jenkins' own previous build; we keep them as
# observed but compute our own complete-build baseline elsewhere.
FAILED_STATUSES = frozenset({"FAILED", "REGRESSION"})


@dataclass(frozen=True)
class TestCaseResult:
    __test__ = False  # not a pytest test class despite the Test* name
    track: str
    suite_name: str
    class_name: str
    name: str
    status: str
    duration: float
    age: int
    failed_since: int
    error_details: str | None
    error_stack_trace: str | None
    # Derived signals:
    file_path: str | None = None
    line: int | None = None
    zephyr_id: str | None = None  # first referenced ZEPHYR test case (owner-correlation anchor)
    zephyr_ids: tuple[str, ...] = ()  # every ZEPHYR test case the failing test references
    zephyr_owner: str | None = None  # ZEPHYR test-case owner initials (NOT the test's developer)

    @property
    def test_id(self) -> str:
        """Track-independent identity: ``class_name.name``."""
        return f"{self.class_name}.{self.name}"

    @property
    def failed(self) -> bool:
        return self.status in FAILED_STATUSES


@dataclass
class ParsedReport:
    cases: list[TestCaseResult] = field(default_factory=list)

    @property
    def tracks(self) -> set[str]:
        return {c.track for c in self.cases}

    def failed(self) -> list[TestCaseResult]:
        return [c for c in self.cases if c.failed]


def _track_of(enclosing_block_names: list[str]) -> str:
    for block in enclosing_block_names or []:
        if _TRACK_RE.match(block):
            return block
    # Fall back to "Tests for <track>" if the bare element is absent.
    for block in enclosing_block_names or []:
        m = re.match(r"Tests for (permanent(?:_py39)?)$", block)
        if m:
            return m.group(1)
    raise ValueError(
        f"could not determine track from enclosingBlockNames={enclosing_block_names!r}"
    )


def _extract_location(stack_trace: str | None) -> tuple[str | None, int | None]:
    if not stack_trace:
        return None, None
    m = _TEST_FRAME_RE.search(stack_trace)
    if not m:
        return None, None
    return m.group(1), int(m.group(2))


def extract_zephyr(stack_trace: str | None) -> tuple[tuple[str, ...], str | None]:
    """The ZEPHYR test cases a failing test references, plus the first ZEPHYR-owner initials.

    Scoped to the ``ZEPHYR TEST CASE INFO`` block so unrelated ``LX-T…`` mentions elsewhere in the
    trace aren't picked up. Returns ``((), None)`` when there is no block. A test may reference more
    than one case (``… test case(s): LX-T1, LX-T2``); ids are returned de-duplicated in first-seen
    order. The owner initials come from the first ``LX-T… (initials)`` detail line, when present —
    this is the ZEPHYR *test case* owner, not the unit test's developer (see #114).
    """
    if not stack_trace:
        return (), None
    idx = stack_trace.find(_ZEPHYR_MARKER)
    if idx == -1:
        return (), None
    section = stack_trace[idx:]
    ids = tuple(dict.fromkeys(_ZEPHYR_ID_RE.findall(section)))
    m = _ZEPHYR_RE.search(section)
    zephyr_owner = m.group(2) if m else None
    return ids, zephyr_owner


def parse_test_report(report: dict) -> ParsedReport:
    """Parse a ``testReport/api/json`` payload into per-(test, track) results."""
    parsed = ParsedReport()
    for suite in report.get("suites", []):
        track = _track_of(suite.get("enclosingBlockNames", []))
        suite_name = suite.get("name", "")
        for case in suite.get("cases", []):
            trace = case.get("errorStackTrace")
            file_path, line = _extract_location(trace)
            zephyr_ids, zephyr_owner = extract_zephyr(trace)
            parsed.cases.append(
                TestCaseResult(
                    track=track,
                    suite_name=suite_name,
                    class_name=case.get("className", ""),
                    name=case.get("name", ""),
                    status=case.get("status", ""),
                    duration=float(case.get("duration", 0.0) or 0.0),
                    age=int(case.get("age", 0) or 0),
                    failed_since=int(case.get("failedSince", 0) or 0),
                    error_details=case.get("errorDetails"),
                    error_stack_trace=trace,
                    file_path=file_path,
                    line=line,
                    zephyr_id=zephyr_ids[0] if zephyr_ids else None,
                    zephyr_ids=zephyr_ids,
                    zephyr_owner=zephyr_owner,
                )
            )
    return parsed
