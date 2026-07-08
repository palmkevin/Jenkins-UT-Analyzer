"""Deterministic synthetic Jenkins payloads + a synthetic ``ut_ref`` feed for demo/tests.

The goal is a *small but complete* run history that lights up every dashboard surface without any
external system: new & acknowledged failures, a recently-fixed test, a flaky oscillator, a removed
test, a newly-added test, plus each deterministic cause (CODE / DATA / INFRASTRUCTURE / UNKNOWN),
a recurring KB signature with fuzzy-similar neighbours, and a shared-outage pair (two new,
unacknowledged tests with identical error text) exercising the triage queue's filters and its
"acknowledge all with this signature" bulk action (issue #63). The per-test **relevance ranking**
(issue #50) is exercised in both directions: ``test_invoice_rounding``'s top-ranked candidate is
the commit touching its own module (path overlap), while ``test_timezone_convert``'s is the
``LORDER`` data change its error text names (entity mention) — two failures of the same run
history whose likely culprits visibly differ — and ``test_pdf_render`` shows the no-match case.
``test_discount_tiers`` adds the score-magnitude tie-break (issue #73): both candidate kinds match
it, but the tier-3 module match outscores the tier-2 component mention, so it classifies as
CODE_CHANGE (with a visible confidence) instead of UNKNOWN; the seed Confirms that suggestion and
the timezone test's seeded attribution is a correction, so the control panel's AI-accuracy metric
shows both verdict kinds.

:class:`SyntheticJenkins` implements the same duck-typed interface as
:class:`tests.fakes.jenkins.FakeJenkinsClient` (``build_meta`` / ``test_report`` / ``change_sets``
/ ``wfapi`` / ``stage_describe`` / ``stage_log`` / ``last_completed_build``), producing payloads
byte-shaped like the golden fixtures so the *real* parsers and pipeline run unchanged.
:class:`SyntheticTrackingFeed` implements :class:`uta.refdb.oracle.TrackingFeed`.

Everything is derived from an ``anchor`` datetime (the newest run's finish time). Passing a fixed
anchor makes the whole dataset reproducible; the running demo passes "now" so "recently fixed" and
age-in-days read naturally against the current date.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from uta.ingest.clock import (
    to_ut_ref_local,
    to_ut_ref_local_window_end,
    to_ut_ref_local_window_start,
)
from uta.refdb.oracle import DataChange, _row_to_change

# ── The story, as status strings ────────────────────────────────────────────────────────────────
# One character per build (oldest -> newest). P=passed, F=failed, S=skipped, x=absent (not present
# in that run — either not yet added, or removed). Every test runs in *both* tracks with the same
# status. 14 builds.
_N_BUILDS = 14
FIRST_BUILD = 601


@dataclass(frozen=True)
class TestSpec:
    """One synthetic test: its identity, ownership, per-build status, and failure text."""

    class_name: str
    method: str
    schedule: str  # len == _N_BUILDS, chars in {P,F,S,x}
    exc_type: str | None = None  # exception line type for failures (drives error_type/signature)
    message: str | None = None  # exception message (masked into the signature)
    line: int = 100
    owner: str | None = None  # ZEPHYR owner initials embedded in the stack trace
    # Extra ZEPHYR test cases this test is also referenced by (beyond the primary LX-T4<line>);
    # lets the demo exercise the multi-case rendering. Only emitted when ``owner`` is set.
    extra_zephyr_ids: tuple[str, ...] = ()

    @property
    def canonical_name(self) -> str:
        return f"{self.class_name}.{self.method}"

    @property
    def module_path(self) -> str:
        """``ut_pricing.pr_engine.TestClass`` -> ``ut_pricing/pr_engine`` (drop the class)."""
        module = self.class_name.rsplit(".", 1)[0]
        return module.replace(".", "/")


# The AssertionError "values differ" family deliberately shares wording across three tests so the KB
# surfaces them as fuzzy-similar past cases (distinct signatures — the hash includes test identity).
_SPECS: tuple[TestSpec, ...] = (
    # Stable passers — carry the pass count and give the results table body.
    TestSpec("ut_accounting.ac_csvc.TestClass", "test_post_journal", "PPPPPPPPPPPPPP"),
    TestSpec("ut_core.co_utils.TestClass", "test_slugify", "PPPPPPPPPPPPPP"),
    TestSpec("ut_reporting.rp_export.TestClass", "test_csv_header", "PPPPPPPPPPPPPP"),
    TestSpec("ut_billing.bi_tax.TestClass", "test_vat_rate", "PPPPPPPPPPPPPP"),
    TestSpec("ut_interface.if_fhir.TestClass", "test_bundle", "PPPPPPPPPPPPPP"),
    # Skipped — carry the skip count.
    TestSpec("ut_pricing.pr_engine.TestClass", "test_legacy_path", "SSSSSSSSSSSSSS"),
    # Recently fixed: regresses (code change), then fixed near the end -> "Recently fixed" bucket.
    TestSpec(
        "ut_pricing.pr_engine.TestClass",
        "test_margin_calc",
        "PPPPPPPPPFFFPP",
        exc_type="AssertionError",
        message="values differ: expected 42 got 43",
        line=128,
        owner="kam",
    ),
    # Still failing (DATA cause), acknowledged in the seed -> "Still failing"; long recurrence.
    # Its error names the changed LORDER entity, so the relevance ranking puts that ut_ref change
    # first (entity mention) — the data-side match-reason example on the test record.
    TestSpec(
        "ut_core.co_time.TestClass",
        "test_timezone_convert",
        "PPPPFFFFFFFFFF",
        exc_type="AssertionError",
        message="values differ for LORDER: expected 2 got 1",
        line=88,
        owner="tha",
    ),
    # Infrastructure cause: an Oracle/TNS fault outranks any coincidental change -> INFRASTRUCTURE.
    TestSpec(
        "ut_core.co_math.TestClass",
        "test_matrix_inverse",
        "PPPPPPPFFFFFFF",
        exc_type="OperationalError",
        message="ORA-12541: TNS:no listener",
        line=55,
    ),
    # New & unacknowledged; opens with both code+data in the window, but the commit touches this
    # test's own module (ut_billing/bi_round.py) and no entity is named in the error, so the
    # relevance tie-break resolves it to CODE_CHANGE — the path-overlap example (issue #50).
    # Referenced by two ZEPHYR cases -> exercises the multi-case link rendering in the demo.
    TestSpec(
        "ut_billing.bi_round.TestClass",
        "test_invoice_rounding",
        "PPPPPPPPPPPFFF",
        exc_type="AssertionError",
        message="values differ: expected 100 got 101",
        line=77,
        owner="mel",
        extra_zephyr_ids=("LX-T5120",),
    ),
    # Score-magnitude tie-break (issue #73): opens in build 612, whose window carries BOTH candidate
    # kinds and BOTH match this test — the commit touches its own module ut_pricing/pr_engine.py
    # (tier-3 module match) while the error text names the AC_CSVC2 *component* (tier-2 mention).
    # The old boolean tie-break collapsed this to UNKNOWN; the margin-aware comparison resolves it
    # to CODE_CHANGE with a visible mid-range confidence. The seed then Confirms the suggestion, so
    # the AI-accuracy panel shows a confirmed verdict next to the timezone test's corrected one.
    TestSpec(
        "ut_pricing.pr_engine.TestClass",
        "test_discount_tiers",
        "PPPPPPPPPPPFFF",
        exc_type="AssertionError",
        message="tier lookup failed after AC_CSVC2 refresh: expected 3 rows got 0",
        line=152,
        owner="kam",
    ),
    # Flaky oscillator: alternating pass/fail -> high transition rate -> flaky flag + leaderboard.
    # Also the UNKNOWN examples: its build-612 episode has both candidate kinds but neither is
    # relevant to it (no path overlap, no entity mention), so the tie stays UNKNOWN; its current
    # episode opens in a build with no candidates at all -> UNKNOWN too.
    TestSpec(
        "ut_reporting.rp_pdf.TestClass",
        "test_pdf_render",
        "PFPFPFPFPFPFPF",
        exc_type="ValueError",
        message="cannot render page 3",
        line=210,
    ),
    # Removed: fails for a stretch, then disappears from the run -> REMOVED with an open episode.
    TestSpec(
        "ut_interface.if_hl7.TestClass",
        "test_ack_generation",
        "xxxxxFFFFFFxxx",
        exc_type="KeyError",
        message="'MSH'",
        line=142,
    ),
    # Newly added mid-history, then fails at the end -> shows a fresh identity in "New failures".
    TestSpec(
        "ut_interface.if_hl7.TestClass",
        "test_parse_message",
        "xxxxxxxxxPPPFF",
        exc_type="AssertionError",
        message="unexpected segment count: expected 5 got 4",
        line=64,
        owner="mel",
    ),
    # One incident, two tests: both new & unacknowledged, both naming the *same* outage in their
    # error text -> distinct signatures (identity is part of the hash) but identical normalized
    # text, exactly what the triage queue's "Acknowledge all with this signature" bulk action
    # (issue #63) targets. A fresh suite/owner also widens the filter bar's dropdown options.
    TestSpec(
        "ut_notify.nt_dispatch.TestClass",
        "test_email_dispatch",
        "PPPPPPPPPPPPFF",
        exc_type="ConnectionError",
        message="SMTP relay unreachable: connection refused",
        line=63,
        owner="rvo",
    ),
    TestSpec(
        "ut_notify.nt_dispatch.TestClass",
        "test_sms_dispatch",
        "PPPPPPPPPPPPFF",
        exc_type="ConnectionError",
        message="SMTP relay unreachable: connection refused",
        line=91,
        owner="rvo",
    ),
)

TRACKS = ("permanent", "permanent_py39")

# Builds that carry candidate signals (see the classifier: code-only -> CODE, data-only -> DATA,
# both -> per-test relevance tie-break, else UNKNOWN; infra error trumps all). Keyed by build
# number.
_CODE_CHANGE_BUILDS = frozenset({FIRST_BUILD + i for i in (5, 8, 9, 11, 12)})
_DATA_CHANGE_BUILDS = frozenset({FIRST_BUILD + i for i in (4, 11)})

# Synthetic commit authors / data-change users — invented initials, never real people. Each
# candidate build carries a single author, so its CODE/DATA-classified episodes surface that
# author as the suggested contact (#49) — the demo shows the one-click Confirm surface populated.
_COMMIT_AUTHORS = ("R. Devlin", "S. Okafor", "P. Nowak")
_DATA_USERS = ("THA", "MEL", "KAM")

_JENKINS_URL = (
    "https://jenkins.example.invalid/job/Development/job/"
    "lsdevbuild-build-release-permanent/{build}/"
)

_STATUS_MAP = {"P": "PASSED", "F": "FAILED", "S": "SKIPPED"}

_RUN_DURATION = timedelta(hours=1)
_BUILD_INTERVAL = timedelta(days=1)


def build_numbers() -> list[int]:
    """The build numbers this dataset produces, oldest-first."""
    return [FIRST_BUILD + i for i in range(_N_BUILDS)]


def _run_start(index: int, anchor: datetime) -> datetime:
    """Start time of build ``index`` (0=oldest). The newest run *ends* at ``anchor``."""
    newest = _N_BUILDS - 1
    return anchor - _RUN_DURATION - (newest - index) * _BUILD_INTERVAL


def _millis(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _stack_trace(spec: TestSpec, track: str) -> str:
    """A Python traceback shaped like the real ones: an in-tree frame + the exception line.

    The in-tree ``/release/<track>/tests/dev/...`` frame is what the report parser reads for the
    test's file/line and what the signature normalizer keeps (after stripping the track prefix).
    """
    frame_path = f"/opt/ls/lx/release/{track}/tests/dev/{spec.module_path}.py"
    exc_line = spec.exc_type or "Exception"
    if spec.message:
        exc_line = f"{exc_line}: {spec.message}"
    lines = [
        "Traceback (most recent call last):",
        f'  File "{frame_path}", line {spec.line}, in {spec.method}',
        "    result = run_case()",
        exc_line,
    ]
    if spec.owner:
        # ZEPHYR ownership signal (parsed into owner_initials + the referenced test case ids).
        # Shaped like the real "ZEPHYR TEST CASE INFO" block so the parser exercises the same path.
        ids = (f"LX-T4{spec.line:03d}", *spec.extra_zephyr_ids)
        rule = "-" * 70
        lines += ["", rule, "", "ZEPHYR TEST CASE INFO:"]
        lines.append(f"Unit test referenced by following test case(s): {', '.join(ids)}")
        for tc in ids:
            lines.append(f'\t{tc} ({spec.owner}): "{spec.method}"')
        lines += ["", rule]
    return "\n".join(lines)


def _case(spec: TestSpec, track: str, status_char: str, index: int) -> dict:
    """One JUnit ``cases[]`` entry for a test in a given track/build."""
    status = _STATUS_MAP[status_char]
    failed = status_char == "F"
    duration = round(0.05 + (spec.line % 7) * 0.03 + index * 0.001, 6)
    return {
        "className": spec.class_name,
        "name": spec.method,
        "status": status,
        "duration": duration,
        "age": 0,
        "failedSince": 0,
        "skipped": status_char == "S",
        "skippedMessage": "demo: environment-gated" if status_char == "S" else None,
        "errorDetails": "test failure" if failed else None,
        "errorStackTrace": _stack_trace(spec, track) if failed else None,
    }


@dataclass
class SyntheticJenkins:
    """A fixtures-free Jenkins client producing the demo build history.

    Duck-types the pipeline's ``JenkinsClient`` protocol. All builds are **complete** (both track
    shards report), so every run advances the lifecycle.
    """

    anchor: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.anchor.tzinfo is None:
            self.anchor = self.anchor.replace(tzinfo=UTC)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _index(self, build: int) -> int:
        index = build - FIRST_BUILD
        if not 0 <= index < _N_BUILDS:
            raise KeyError(f"no synthetic fixture for build {build}")
        return index

    def _present(self, spec: TestSpec, index: int) -> str | None:
        char = spec.schedule[index]
        return None if char == "x" else char

    def _has_failure(self, index: int) -> bool:
        return any(self._present(s, index) == "F" for s in _SPECS)

    # ── JenkinsClient protocol ───────────────────────────────────────────────
    def build_meta(self, build: int) -> dict:
        index = self._index(build)
        start = _run_start(index, self.anchor)
        result = "UNSTABLE" if self._has_failure(index) else "SUCCESS"
        return {
            "number": build,
            "result": result,
            "url": _JENKINS_URL.format(build=build),
            "timestamp": _millis(start),
            "duration": int(_RUN_DURATION.total_seconds() * 1000),
        }

    def test_report(self, build: int) -> dict:
        index = self._index(build)
        suites = []
        for track in TRACKS:
            cases = []
            for spec in _SPECS:
                char = self._present(spec, index)
                if char is None:
                    continue
                cases.append(_case(spec, track, char, index))
            suites.append(
                {
                    "name": "nose2-junit",
                    "enclosingBlockNames": [f"Collect test results - {track}", track, "Unit tests"],
                    "cases": cases,
                }
            )
        return {"suites": suites}

    def change_sets(self, build: int) -> dict:
        self._index(build)
        if build not in _CODE_CHANGE_BUILDS:
            return {"changeSets": []}
        index = self._index(build)
        start = _run_start(index, self.anchor)
        author = _COMMIT_AUTHORS[index % len(_COMMIT_AUTHORS)]
        revision = 48000 + build
        items = [
            {
                "commitId": str(revision),
                "timestamp": _millis(start - timedelta(minutes=40)),
                "author": {"fullName": author},
                "msg": f"LX-{build}: adjust calculation and refresh expected fixtures",
                "paths": [
                    {"editType": "edit", "file": "trunk/lx/ut_pricing/pr_engine.py"},
                    {"editType": "edit", "file": "trunk/lx/ut_billing/bi_round.py"},
                ],
            }
        ]
        return {"changeSets": [{"kind": "svn", "items": items}]}

    def wfapi(self, build: int) -> dict:
        index = self._index(build)
        start = _run_start(index, self.anchor)
        stages = []
        for offset, track in enumerate(TRACKS):
            shard_start = start + timedelta(minutes=offset)
            stages.append(
                {
                    "id": str(300 + offset),
                    "name": f"devUTs: Execute - {track}",
                    "status": "SUCCESS",
                    "startTimeMillis": _millis(shard_start),
                    "durationMillis": int(
                        (_RUN_DURATION - timedelta(minutes=5)).total_seconds() * 1000
                    ),
                }
            )
        return {
            "id": str(build),
            "name": f"#{build}",
            "status": "UNSTABLE" if self._has_failure(index) else "SUCCESS",
            "startTimeMillis": _millis(start),
            "durationMillis": int(_RUN_DURATION.total_seconds() * 1000),
            "stages": stages,
        }

    def stage_describe(self, build: int, node_id: str) -> dict:
        self._index(build)
        return {"id": str(node_id), "stageFlowNodes": []}

    def stage_log(self, build: int, node_id: str) -> dict:
        self._index(build)
        return {"nodeId": str(node_id), "text": ""}

    def last_completed_build(self) -> int | None:
        return FIRST_BUILD + _N_BUILDS - 1


class SyntheticTrackingFeed:
    """A synthetic :class:`uta.refdb.oracle.TrackingFeed` (the ``ut_ref`` data-change candidates).

    Rows are placed a couple of hours before each :data:`_DATA_CHANGE_BUILDS` run start, stored as
    naive Europe/Luxembourg wall-clock (exactly like ``CREDATIM``), and filtered with the same
    window-to-local conversion the real feed uses — so the clock discipline is exercised end to end.
    """

    def __init__(self, anchor: datetime | None = None) -> None:
        anchor = anchor or datetime.now(UTC)
        if anchor.tzinfo is None:
            anchor = anchor.replace(tzinfo=UTC)
        self._rows: list[dict] = []
        for build in sorted(_DATA_CHANGE_BUILDS):
            index = build - FIRST_BUILD
            run_start = _run_start(index, anchor)
            changed_at_local = to_ut_ref_local(run_start - timedelta(hours=2))
            user = _DATA_USERS[index % len(_DATA_USERS)]
            for n, (entity, comp, ctype) in enumerate(
                (("LORDER", "LORDER_CSVC", "U"), ("ACINVORD", "AC_CSVC2", "C"))
            ):
                self._rows.append(
                    {
                        "SESSIONLOGID": 90000 + build * 10 + n,
                        "LXTABLECODE": entity,
                        "PKLST": str(10000 + build),
                        "LXTABLECODEREF": entity,
                        "PKLSTREF": str(10000 + build),
                        "TYPE": ctype,
                        "COMPONENTNAME": comp,
                        "CREDATIM": changed_at_local,
                        "UPDDATIM": changed_at_local,
                        "USRIDCRE": 1100 + n,
                        "USRCODE": user,
                    }
                )

    def changes_in_window(self, start_utc: datetime, end_utc: datetime) -> list[DataChange]:
        lo = to_ut_ref_local_window_start(start_utc)
        hi = to_ut_ref_local_window_end(end_utc)
        rows = [r for r in self._rows if lo <= r["CREDATIM"] <= hi]
        rows.sort(key=lambda r: r["CREDATIM"])
        return [_row_to_change(r) for r in rows]
