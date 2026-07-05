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
test. Failure/error tracebacks are read from the trailing ``====``-delimited blocks; a test that
appears only in a block (e.g. a non-verbose run) is still surfaced as FAILED. (Tests with docstrings
render the docstring on the status line in verbose mode; these stages don't use them, so that form
is intentionally not parsed — such a test still surfaces from its failure block if it fails.)

Golden-tested against anonymized ``tests/fixtures/jenkins/stagelog_*.json`` (medical data redacted).
It never touches the network; feed it the parsed ``wfapi/log`` JSON (or its raw ``text``).
"""

from __future__ import annotations

import html
import re

from .ut_report import TestCaseResult, extract_zephyr

# Jenkins' Timestamper plugin wraps each console line in HTML: a visible ``<b>HH:MM:SS</b>`` span
# and a hidden ISO-8601 span, with ``>`` etc. HTML-escaped. The ``wfapi/log`` ``text`` field carries
# this markup verbatim, so it must be stripped to plain console text before the line patterns match.
_TS_SPAN_RE = re.compile(r'<span class="timestamp">.*?</span>\s*')
_HIDDEN_SPAN_RE = re.compile(r'<span style="display: ?none">.*?</span>\s*')
_TAG_RE = re.compile(r"<[^>]+>")

# A verbose status line: ``test_method (dotted.path) ... <outcome>``.
_STATUS_RE = re.compile(r"^(?P<name>\w+) \((?P<path>[\w.]+)\) \.\.\. (?P<rest>.+?)\s*$")
# A failure/error block header: ``FAIL: test_method (dotted.path)``.
_BLOCK_HEADER_RE = re.compile(r"^(?P<kind>FAIL|ERROR): (?P<name>\w+) \((?P<path>[\w.]+)\)\s*$")
_SEP_RE = re.compile(r"^=+$")  # block separator (a run of '=')
_RULE_RE = re.compile(r"^-+$")  # rule under a header / before the summary (a run of '-')
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


def _status_of(rest: str) -> str:
    """Map a verbose-line outcome tail to our status vocabulary (PASSED/FAILED/SKIPPED)."""
    r = rest.strip().lower()
    if r == "ok":
        return "PASSED"
    if r.startswith("skip"):
        return "SKIPPED"
    if r.startswith("expected failure"):
        return "PASSED"  # xfail: ran and failed as designed — not a regression, build stays green
    if r.startswith("unexpected success"):
        return "FAILED"  # an xfail that passed — unittest counts this as a failure
    if r.startswith(("fail", "error")):
        return "FAILED"
    return "PASSED"  # unknown tail — conservative (unittest only emits the cases above)


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
                blocks[(cls, name)] = (_last_meaningful_line(body), stack, file_path, line)
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
    for line in lines:
        m = _STATUS_RE.match(line)
        if not m:
            continue
        key = _split_identity(m.group("name"), m.group("path"))
        if key not in outcomes:
            order.append(key)
        outcomes[key] = _status_of(m.group("rest"))

    blocks = _parse_blocks(lines)

    def _case(cls: str, name: str, status: str) -> TestCaseResult:
        details, stack, file_path, line = blocks.get((cls, name), (None, None, None, None))
        zephyr_ids, owner = extract_zephyr(stack)
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
            owner_initials=owner,
        )

    results = [_case(cls, name, outcomes[(cls, name)]) for (cls, name) in order]
    # A failure block with no verbose status line (non-verbose run) still surfaces as FAILED.
    for cls, name in blocks:
        if (cls, name) not in outcomes:
            results.append(_case(cls, name, "FAILED"))
    return results
