"""Golden tests for the devUTs JUnit parser against the anonymized #1702 fixture."""

from __future__ import annotations

from uta.ingest.ut_report import parse_test_report


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
    assert case.owner_initials == "kam"


def test_passed_case_has_no_location_or_owner(test_report_1702):
    parsed = parse_test_report(test_report_1702)
    passed = next(c for c in parsed.cases if c.status == "PASSED")
    assert passed.file_path is None
    assert passed.owner_initials is None
