"""Golden + unit tests for the unittest console-log parser (deferred UT stages)."""

from __future__ import annotations

import json
from pathlib import Path

from uta.ingest.unittest_log import parse_unittest_log

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "jenkins"


def _log(node: int) -> dict:
    return json.loads((_FIXTURES / f"stagelog_1702_{node}.json").read_text())


def test_all_pass_stage_parses_each_case():
    cases = parse_unittest_log(_log(274), track="permanent", suite_name="SMB Transform")
    by_id = {c.test_id: c for c in cases}
    assert len(cases) == 4
    assert {c.track for c in cases} == {"permanent"}
    assert {c.suite_name for c in cases} == {"SMB Transform"}
    assert (
        by_id["smb.transform.test_pricing.PricingTransformTest.test_apply_markup"].status
        == "PASSED"
    )
    # 'skipped ...' maps to SKIPPED, not a failure.
    assert (
        by_id["smb.transform.test_rates.RatesTransformTest.test_skip_when_disabled"].status
        == "SKIPPED"
    )
    assert not any(c.failed for c in cases)


def test_failure_and_error_blocks_attach_details_and_location():
    cases = parse_unittest_log(_log(292), track="permanent_py39", suite_name="SMB Transform")
    by_id = {c.test_id: c for c in cases}

    fail = by_id["smb.transform.test_pricing.PricingTransformTest.test_round_half_even"]
    assert fail.status == "FAILED"
    assert fail.error_details == "AssertionError: Decimal('0.00') != Decimal('REDACTED')"
    assert fail.file_path == "/opt/ls/lx/release/permanent_py39/tests/smb/test_pricing.py"
    assert fail.line == 88
    assert "Traceback (most recent call last)" in fail.error_stack_trace

    err = by_id["smb.transform.test_rates.RatesTransformTest.test_currency_conversion"]
    assert err.status == "FAILED"
    assert err.error_details == "KeyError: 'REDACTED'"
    # The first frame is the test's own location (not the deeper library frame).
    assert err.file_path == "/opt/ls/lx/release/permanent_py39/tests/smb/test_rates.py"
    assert err.line == 142


def test_track_is_stripped_so_both_tracks_share_identity():
    """The same method in two tracks yields the same ``test_id`` — track is an attribute."""
    perm = parse_unittest_log(_log(274), track="permanent", suite_name="SMB Transform")
    py39 = parse_unittest_log(_log(292), track="permanent_py39", suite_name="SMB Transform")
    assert {c.test_id for c in perm} == {c.test_id for c in py39}


def test_python311_status_line_form_strips_duplicate_method():
    text = "test_thing (pkg.mod.Klass.test_thing) ... ok\n"
    (case,) = parse_unittest_log(text, track="permanent", suite_name="LXS")
    assert case.class_name == "pkg.mod.Klass"
    assert case.test_id == "pkg.mod.Klass.test_thing"
    assert case.status == "PASSED"


def test_outcome_vocabulary_mapping():
    text = (
        "t_ok (m.C) ... ok\n"
        "t_fail (m.C) ... FAIL\n"
        "t_err (m.C) ... ERROR\n"
        "t_skip (m.C) ... skipped 'why'\n"
        "t_xfail (m.C) ... expected failure\n"
        "t_usucc (m.C) ... unexpected success\n"
    )
    status = {
        c.name: c.status for c in parse_unittest_log(text, track="permanent", suite_name="LXS")
    }
    assert status == {
        "t_ok": "PASSED",
        "t_fail": "FAILED",
        "t_err": "FAILED",
        "t_skip": "SKIPPED",
        "t_xfail": "PASSED",  # xfail is not a regression
        "t_usucc": "FAILED",  # unexpected success counts as a failure
    }


def test_real_timestamper_html_log_is_stripped_and_parsed():
    """Real stage log is HTML-wrapped (Timestamper) and non-verbose; the failure still surfaces."""
    cases = parse_unittest_log(_log(295), track="permanent_py39", suite_name="SMB Transform")
    (case,) = cases
    assert case.class_name == "ls.smb.tests.transform.lx.cases.LXTransformTestCases"
    assert case.name == "test_39_specbillgrpid_for_micb_elements"
    assert case.status == "FAILED"
    assert case.error_details == "KeyError: 'REDACTED'"
    # The first traceback frame is the test's own location, recovered through the markup.
    assert case.file_path.endswith("/ls/smb/tests/transform/lx/cases.py")
    assert case.line == 177
    # The HTML entity and the timestamper markup are gone from the captured stack.
    assert "<span" not in case.error_stack_trace
    assert "&gt;" not in case.error_stack_trace


def test_html_entities_and_tags_stripped_in_status_lines():
    """A verbose status line wrapped in Timestamper markup still maps to the right outcome."""
    text = (
        '<span class="timestamp"><b>10:00:00</b> </span>'
        '<span style="display: none">[2026-06-26T08:00:00.000Z]</span> '
        "t_ok (pkg.mod.Klass) ... ok\n"
    )
    (case,) = parse_unittest_log(text, track="permanent", suite_name="LXS")
    assert case.test_id == "pkg.mod.Klass.t_ok"
    assert case.status == "PASSED"


def test_unrecognized_outcome_tail_does_not_default_to_passed(caplog):
    """A format drift must surface loudly, not silently turn a real failure green."""
    text = "t_weird (m.C) ... xyzzy\n"
    with caplog.at_level("WARNING"):
        (case,) = parse_unittest_log(text, track="permanent", suite_name="LXS")
    assert case.status == "SKIPPED"
    assert case.status != "PASSED"
    warnings = [r.message for r in caplog.records if "unrecognized outcome tail" in r.message]
    assert warnings
    # The warning names the test but withholds the tail itself — stdout glued onto a status
    # line in these legacy LIMS suites may carry patient data (medical-data invariant).
    assert any("m.C.t_weird" in msg for msg in warnings)
    assert not any("xyzzy" in msg for msg in warnings)


def test_fail_block_overrides_garbled_status_line(caplog):
    """A test that prints to stdout garbles its status-line tail (→ SKIPPED hole), but its
    ``FAIL:`` traceback block is authoritative — the case must surface as FAILED with the
    block's details, not persist as a hole."""
    text = (
        "test_x (pkg.mod.Klass) ... some stdout the test printed\n"
        "======================================================================\n"
        "FAIL: test_x (pkg.mod.Klass)\n"
        "----------------------------------------------------------------------\n"
        "Traceback (most recent call last):\n"
        '  File "/opt/ls/lx/release/permanent/tests/pkg/test_mod.py", line 12, in test_x\n'
        "    self.assertTrue(False)\n"
        "AssertionError: False is not true\n"
        "\n"
        "----------------------------------------------------------------------\n"
        "Ran 1 test in 0.001s\n"
        "\n"
        "FAILED (failures=1)\n"
    )
    with caplog.at_level("WARNING"):
        (case,) = parse_unittest_log(text, track="permanent", suite_name="LXS")
    assert case.test_id == "pkg.mod.Klass.test_x"
    assert case.status == "FAILED"
    assert case.error_details == "AssertionError: False is not true"
    assert case.line == 12
    # The garbled tail still warns (format drift is worth knowing about), it just can't
    # swallow the failure any more.
    assert any("unrecognized outcome tail" in r.message for r in caplog.records)


def test_error_block_overrides_garbled_status_line():
    """Same as the FAIL case: an ``ERROR:`` block wins over the garbled status line."""
    text = (
        "test_y (pkg.mod.Klass) ... more printed junk\n"
        "======================================================================\n"
        "ERROR: test_y (pkg.mod.Klass)\n"
        "----------------------------------------------------------------------\n"
        "Traceback (most recent call last):\n"
        '  File "/opt/ls/lx/release/permanent/tests/pkg/test_mod.py", line 34, in test_y\n'
        "    lookup[key]\n"
        "KeyError: 'REDACTED'\n"
        "\n"
        "----------------------------------------------------------------------\n"
        "Ran 1 test in 0.001s\n"
        "\n"
        "FAILED (errors=1)\n"
    )
    (case,) = parse_unittest_log(text, track="permanent", suite_name="LXS")
    assert case.test_id == "pkg.mod.Klass.test_y"
    assert case.status == "FAILED"
    assert case.error_details == "KeyError: 'REDACTED'"
    assert case.line == 34


def test_empty_log_yields_no_cases():
    assert parse_unittest_log({"text": ""}, track="permanent", suite_name="LXS") == []


def test_non_verbose_failure_block_still_surfaces():
    """No per-test status lines (non-verbose), but a failure block still yields a FAILED case."""
    text = (
        "..F\n"
        "======================================================================\n"
        "FAIL: test_x (pkg.mod.Klass)\n"
        "----------------------------------------------------------------------\n"
        "Traceback (most recent call last):\n"
        '  File "/opt/ls/lx/release/permanent/tests/pkg/test_mod.py", line 12, in test_x\n'
        "    self.assertTrue(False)\n"
        "AssertionError: False is not true\n"
        "\n"
        "----------------------------------------------------------------------\n"
        "Ran 3 tests in 0.001s\n"
        "\n"
        "FAILED (failures=1)\n"
    )
    (case,) = parse_unittest_log(text, track="permanent", suite_name="LXS")
    assert case.test_id == "pkg.mod.Klass.test_x"
    assert case.status == "FAILED"
    assert case.error_details == "AssertionError: False is not true"
    assert case.line == 12
