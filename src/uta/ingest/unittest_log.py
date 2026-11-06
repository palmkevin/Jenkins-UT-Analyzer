"""Parser for the deferred **unittest console-log** UT stages (SMB Pricing/Transform, ITF
Highlevel, LXS, Uniface deploy unit tests).

These stages run Python ``unittest`` inside Jenkins *Shell Script* steps; unlike the devUTs (nose2)
JUnit report there is **no structured artifact** — results live only in the **stage console log**
(``/<build>/execution/node/<id>/wfapi/log``). This parser turns that verbose console text into the
same :class:`~uta.ingest.ut_report.TestCaseResult` objects the JUnit parser emits, so the rest of
the pipeline (identity, lifecycle, classification, signatures, flakiness) treats both ingest sources
identically — the "same ingest interface" the plan reserved for these stages, added without a
redesign.

It assumes **verbose** unittest output (``-v``): one ``method (dotted.path) ... <outcome>`` line per
test. Failure/error tracebacks are read from the trailing ``====``-delimited blocks; a block is
**authoritative** — it overrides the test's status-line outcome (stdout printed mid-test can garble
the tail), and a test that appears only in a block (e.g. a non-verbose build) is still surfaced as
FAILED. A test that prints gets its outcome word on a later line, after the printed output; a
failing ``subTest`` gets an indented ``(params) ... FAIL`` line and a ``FAIL: … (params)`` block —
both collapse onto the parent test, which is FAILED. (Tests with docstrings
render the docstring on the status line in verbose mode; these stages don't use them, so that form
is intentionally not parsed — such a test still surfaces from its failure block if it fails.)

Golden-tested against anonymized ``tests/fixtures/jenkins/stagelog_*.json`` (medical data redacted).
It never touches the network; feed it the parsed ``wfapi/log`` JSON (or its raw ``text``).
"""

from __future__ import annotations

import html
import logging
import re

from .ut_report import TestCaseResult, extract_zephyr

logger = logging.getLogger(__name__)

# Jenkins' Timestamper plugin wraps each console line in HTML: a visible ``<b>HH:MM:SS</b>`` span
# and a hidden ISO-8601 span, with ``>`` etc. HTML-escaped. The ``wfapi/log`` ``text`` field carries
# this markup verbatim, so it must be stripped to plain console text before the line patterns match.
_TS_SPAN_RE = re.compile(r'<span class="timestamp">.*?</span>\s*')
_HIDDEN_SPAN_RE = re.compile(r'<span style="display: ?none">.*?</span>\s*')
_TAG_RE = re.compile(r"<[^>]+>")

# A verbose status line: ``test_method (dotted.path) ... <outcome>``. The tail may be empty: a test
# that prints (or has a failing subTest) gets its outcome on a later line.
_STATUS_RE = re.compile(r"^(?P<name>\w+) \((?P<path>[\w.]+)\) \.\.\.(?: (?P<rest>.*?))?\s*$")
# A failing subTest's verbose line, indented under its parent's status line:
# ``  test_method (dotted.path) (i=1) ... FAIL`` (``[msg]`` and/or ``(params)`` after the path).
_SUBTEST_RE = re.compile(r"^\s+(?P<name>\w+) \((?P<path>[\w.]+)\) .+ \.\.\. (?P<rest>.+?)\s*$")
# A failure/error block header: ``FAIL: test_method (dotted.path)``, optionally followed by a
# subTest description (``(i=1)``, ``[msg]``) — subTest failures collapse onto their parent test.
_BLOCK_HEADER_RE = re.compile(
    r"^(?P<kind>FAIL|ERROR): (?P<name>\w+) \((?P<path>[\w.]+)\)(?: .+?)?\s*$"
)
_SEP_RE = re.compile(r"^=+$")  # block separator (a build of '=')
_RULE_RE = re.compile(r"^-+$")  # rule under a header / before the summary (a build of '-')
_RAN_RE = re.compile(r"^Ran \d+ tests? in ")  # trailing summary line
_FRAME_RE = re.compile(r'File "([^"]+)", line (\d+)')

# A parsed traceback block: (details, stack, file_path, line) keyed by (class_name, method).
_Block = tuple[str | None, str, str | None, int | None]


def _strip_console_html(text: str) -> str:
    """Strip Timestamper HTML markup back to plain console text.

    A no-op fast path for already-plain text (the fixtures, hand-written test strings) so the parser
    behaves identically whether fed raw or pre-cleaned logs.
    """
    if "<" not in text and "&" not in text:
        return text
    text = _TS_SPAN_RE.sub("", text)
    text = _HIDDEN_SPAN_RE.sub("", text)
    text = _TAG_RE.sub("", text)
    return html.unescape(text)


def _outcome(rest: str) -> str | None:
    """The status a unittest outcome word maps to, or ``None`` if ``rest`` isn't one.

    Matched exactly (not by prefix) so text a test printed — ``Error loading …`` — is never read
    as an outcome.
    """
    r = rest.strip().lower()
    if r == "ok":
        return "PASSED"
    if r == "skipped" or r.startswith("skipped "):
        return "SKIPPED"
    if r == "expected failure":
        return "PASSED"  # xfail: ran and failed as designed — not a regression, build stays green
    if r == "unexpected success":
        return "FAILED"  # an xfail that passed — unittest counts this as a failure
    if r in ("fail", "error"):
        return "FAILED"
    return None


def _status_of(rest: str, *, test_id: str) -> str:
    """Map a verbose-line outcome tail to our status vocabulary (PASSED/FAILED/SKIPPED).

    An unrecognized tail means the nose2/unittest output format drifted from what this regex-based
    parser expects — or the test printed to stdout mid-build, gluing arbitrary text onto its status
    line. Defaulting that to PASSED would silently turn a real failure green — the worst failure
    mode for this tool — so it's logged loudly and mapped to SKIPPED (a neutral "hole", consistent
    with how the rest of the pipeline already treats SKIPPED/absent results) instead. The tail
    itself is **not** logged: in these legacy LIMS suites stdout may carry patient data (see the
    medical-data invariant), so only the test identity and the tail's size are recorded.
    """
    status = _outcome(rest)
    if status is not None:
        return status
    logger.warning(
        "unittest_log: unrecognized outcome tail (%d chars, content withheld) on status line of %s",
        len(rest),
        test_id,
    )
    return "SKIPPED"


def _split_identity(name: str, path: str) -> tuple[str, str]:
    """``(class_name, method)`` from the verbose line's name + dotted path.

    Python ≤3.10 renders ``method (module.Class)``; 3.11+ renders ``method (module.Class.method)``.
    Strip a trailing duplicate of the method so identity matches the JUnit ``className.name`` shape.
    """
    parts = path.split(".")
    if len(parts) > 1 and parts[-1] == name:
        parts = parts[:-1]
    return ".".join(parts), name


def _last_meaningful_line(body: list[str]) -> str | None:
    """The exception summary — the last non-blank, non-rule line of a traceback block."""
    for ln in reversed(body):
        s = ln.strip()
        if s and not _RULE_RE.match(s):
            return s
    return None


def _parse_blocks(lines: list[str]) -> dict[tuple[str, str], _Block]:
    """Map ``(class_name, method)`` to a :data:`_Block` from the ``====`` traceback blocks."""
    blocks: dict[tuple[str, str], _Block] = {}
    n = len(lines)
    i = 0
    while i < n:
        if _SEP_RE.match(lines[i]) and i + 1 < n:
            header = _BLOCK_HEADER_RE.match(lines[i + 1])
            if header:
                cls, name = _split_identity(header.group("name"), header.group("path"))
                j = i + 2
                if j < n and _RULE_RE.match(lines[j]):  # skip the rule under the header
                    j += 1
                body: list[str] = []
                while j < n and not _SEP_RE.match(lines[j]):
                    if _RAN_RE.match(lines[j].strip()):  # reached the trailing summary
                        break
                    body.append(lines[j])
                    j += 1
                # Trim the blank line + rule that belong to the summary, not this traceback.
                while body and (not body[-1].strip() or _RULE_RE.match(body[-1])):
                    body.pop()
                stack = "\n".join(body).strip()
                frame = _FRAME_RE.search(stack)
                file_path = frame.group(1) if frame else None
                line = int(frame.group(2)) if frame else None
                # Several failing subTests of one test yield several blocks; the first one is kept
                # so the test's details/signature don't depend on how many subTests failed.
                blocks.setdefault(
                    (cls, name), (_last_meaningful_line(body), stack, file_path, line)
                )
                i = j
                continue
        i += 1
    return blocks


def parse_unittest_log(log: dict | str, *, track: str, suite_name: str) -> list[TestCaseResult]:
    """Parse one stage's ``wfapi/log`` payload into per-test results for ``track`` / ``suite_name``.

    Accepts the raw ``wfapi/log`` JSON (uses its ``text`` field) or the console text directly.
    Per-test durations are not reported in unittest console output, so they are ``0.0``.
    """
    text = log if isinstance(log, str) else (log.get("text") or "")
    lines = _strip_console_html(text).splitlines()

    outcomes: dict[tuple[str, str], str] = {}
    order: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    # A status line whose tail isn't an outcome (empty, or stdout the test printed) leaves the test
    # *pending*: unittest writes the outcome word once the test finishes, on its own line after the
    # printed output. A pending test superseded mid-log falls back to ``_status_of`` (warn + the
    # SKIPPED hole); one still pending when the log *ends* is settled FAILED (see below).
    pending: tuple[tuple[str, str], str] | None = None

    def _settle() -> None:
        if pending is not None:
            key, rest = pending
            outcomes.setdefault(key, _status_of(rest, test_id=".".join(key)))

    for line in lines:
        m = _STATUS_RE.match(line)
        if m:
            _settle()
            pending = None
            key = _split_identity(m.group("name"), m.group("path"))
            if key not in seen:
                seen.add(key)
                order.append(key)
            outcomes.pop(key, None)
            rest = m.group("rest") or ""
            status = _outcome(rest)
            if status is None:
                pending = (key, rest)
            else:
                outcomes[key] = status
            continue
        sub = _SUBTEST_RE.match(line)
        if sub:
            key = _split_identity(sub.group("name"), sub.group("path"))
            if key in seen and _outcome(sub.group("rest")) == "FAILED":
                outcomes[key] = "FAILED"  # any failing subTest fails the parent test
                if pending is not None and pending[0] == key:
                    pending = None
            continue
        if pending is not None:
            if _SEP_RE.match(line):  # the traceback blocks begin — nothing left to resolve it
                _settle()
                pending = None
                continue
            status = _outcome(line)
            if status is not None:
                outcomes[pending[0]] = status
                pending = None
    if pending is not None:
        # The log ended with a test still awaiting its outcome — no outcome word, no traceback
        # block, no summary: the process crashed (or the log was truncated) mid-test. A neutral
        # SKIPPED hole would hide that, so it is a failure. Tail withheld (medical-data invariant).
        key, rest = pending
        logger.warning(
            "unittest_log: %s never reported an outcome before the log ended (%d-char tail, "
            "content withheld) — treating it as FAILED (crashed or truncated run?)",
            ".".join(key),
            len(rest),
        )
        outcomes.setdefault(key, "FAILED")

    blocks = _parse_blocks(lines)

    def _case(cls: str, name: str, status: str) -> TestCaseResult:
        details, stack, file_path, line = blocks.get((cls, name), (None, None, None, None))
        zephyr_ids, zephyr_owner = extract_zephyr(stack)
        return TestCaseResult(
            track=track,
            suite_name=suite_name,
            class_name=cls,
            name=name,
            status=status,
            duration=0.0,
            age=0,
            failed_since=0,
            error_details=details,
            error_stack_trace=stack,
            file_path=file_path,
            line=line,
            zephyr_id=zephyr_ids[0] if zephyr_ids else None,
            zephyr_ids=zephyr_ids,
            zephyr_owner=zephyr_owner,
        )

    # A parsed FAIL/ERROR block is authoritative: a test that prints to stdout mid-build garbles
    # its status line's tail (mapped to the SKIPPED "hole" above), but unittest only emits a
    # ``====`` traceback block for a test that actually failed/errored — so the block overrides
    # whatever the status line said, keeping the real failure from persisting as a hole.
    results = [
        _case(cls, name, "FAILED" if (cls, name) in blocks else outcomes[(cls, name)])
        for (cls, name) in order
    ]
    # A failure block with no verbose status line (non-verbose build) still surfaces as FAILED.
    for cls, name in blocks:
        if (cls, name) not in outcomes:
            results.append(_case(cls, name, "FAILED"))
    return results
