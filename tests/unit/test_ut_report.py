"""Golden tests for the devUTs JUnit parser against the anonymized #1702 fixture."""

from __future__ import annotations

from uta.ingest.ut_report import extract_zephyr, parse_test_report


def test_both_tracks_parsed(test_report_1702):
    parsed = parse_test_report(test_report_1702)
    assert parsed.tracks == {"permanent", "permanent_py39"}


def test_test_identity_is_track_independent(test_report_1702):
    parsed = parse_test_report(test_report_1702)
    by_track = {
        c.track: c for c in parsed.cases if c.name == "test_inpmode_alternativ_debitor_at_cust"
    }
    # Same test runs in both tracks -> same identity, two results.
    assert set(by_track) == {"permanent", "permanent_py39"}
    assert by_track["permanent"].test_id == by_track["permanent_py39"].test_id
    assert (
        by_track["permanent"].test_id
        == "ut_accounting.ac_csvc.TestClass.test_inpmode_alternativ_debitor_at_cust"
    )


def test_failed_status_set(test_report_1702):
    parsed = parse_test_report(test_report_1702)
    statuses = {c.status for c in parsed.cases}
    assert statuses <= {"PASSED", "FAILED", "REGRESSION", "SKIPPED", "FIXED"}
    assert all(c.failed for c in parsed.cases if c.status in {"FAILED", "REGRESSION"})


def test_file_path_and_line_extracted_from_trace(test_report_1702):
    parsed = parse_test_report(test_report_1702)
    case = next(
        c
        for c in parsed.cases
        if c.name == "test_inpmode_alternativ_debitor_at_cust" and c.track == "permanent"
    )
    assert case.file_path == "/opt/ls/lx/release/permanent/tests/dev/ut_accounting/ac_csvc.py"
    assert case.line == 793


def test_owner_initials_extracted_from_zephyr(test_report_1702):
    parsed = parse_test_report(test_report_1702)
    case = next(
        c
        for c in parsed.cases
        if c.name == "test_inpmode_alternativ_debitor_at_cust" and c.track == "permanent"
    )
    assert case.zephyr_id == "LX-T4447"
    assert case.zephyr_ids == ("LX-T4447",)
    assert case.owner_initials == "kam"


def test_passed_case_has_no_location_or_owner(test_report_1702):
    parsed = parse_test_report(test_report_1702)
    passed = next(c for c in parsed.cases if c.status == "PASSED")
    assert passed.file_path is None
    assert passed.owner_initials is None
    assert passed.zephyr_id is None
    assert passed.zephyr_ids == ()


def test_extract_zephyr_none_without_block():
    # No "ZEPHYR TEST CASE INFO" block -> nothing, even if an LX-T token appears elsewhere.
    assert extract_zephyr(None) == ((), None)
    assert extract_zephyr("AssertionError: expected LX-T9999 somewhere") == ((), None)


def test_extract_zephyr_single_case_with_owner():
    trace = (
        "Traceback (most recent call last):\n"
        "----------------------------------------------------------------------\n\n"
        "ZEPHYR TEST CASE INFO:\n"
        "Unit test referenced by following test case(s): LX-T4792\n"
        '\tLX-T4792 (tha): "Unit Test | SMB: Function and Display of function tests"\n'
    )
    assert extract_zephyr(trace) == (("LX-T4792",), "tha")


def test_extract_zephyr_multiple_cases_deduped_in_order():
    trace = (
        "ZEPHYR TEST CASE INFO:\n"
        "Unit test referenced by following test case(s): LX-T4792, LX-T5001\n"
        '\tLX-T4792 (tha): "first"\n'
        '\tLX-T5001 (kam): "second"\n'
    )
    ids, owner = extract_zephyr(trace)
    assert ids == ("LX-T4792", "LX-T5001")  # deduped, first-seen order
    assert owner == "tha"  # first owner-bearing detail line
