"""Golden tests for the per-shard timing parser + completeness."""

from __future__ import annotations

from datetime import UTC

from uta.ingest.wfapi import find_unittest_stages, parse_wfapi


def test_both_ut_shards_parsed(wfapi_1702):
    run = parse_wfapi(wfapi_1702)
    assert set(run.shards) == {"permanent", "permanent_py39"}


def test_shard_timings_are_utc(wfapi_1702):
    run = parse_wfapi(wfapi_1702)
    for shard in run.shards.values():
        assert shard.start.tzinfo == UTC
        assert shard.end > shard.start


def test_completeness_uses_expected_shard_count(wfapi_1702):
    run = parse_wfapi(wfapi_1702)
    assert run.is_complete(expected_shards=2)
    assert not run.is_complete(expected_shards=3)


def test_window_spans_all_shards(wfapi_1702):
    run = parse_wfapi(wfapi_1702)
    start, end = run.window
    assert start == min(s.start for s in run.shards.values())
    assert end == max(s.end for s in run.shards.values())


def test_find_unittest_stages_picks_named_suites_both_tracks(wfapi_1702):
    stages = find_unittest_stages(wfapi_1702)
    # Every default suite is discovered across the tracks it ran in.
    suites = {s.suite for s in stages}
    assert {
        "LXS",
        "SMB Pricing",
        "SMB Transform",
        "ITF Highlevel",
        "Uniface deploy unit tests",
    } <= suites
    transform = sorted(s.track for s in stages if s.suite == "SMB Transform")
    assert transform == ["permanent", "permanent_py39"]
    # Node ids are the wfapi flow-node ids used for the per-stage log fetch.
    assert all(s.node_id.isdigit() for s in stages)


def test_find_unittest_stages_excludes_devuts_and_non_test_stages(wfapi_1702):
    stages = find_unittest_stages(wfapi_1702)
    names = {f"{s.suite} - {s.track}" for s in stages}
    # devUTs is in the JUnit report; "Clean logs"/"Tests for ..." are not unittest stages.
    assert not any("devUTs" in n for n in names)
    assert not any(s.suite in {"Clean logs", "Tests for"} for s in stages)


def test_find_unittest_stages_respects_a_restricted_suite_set(wfapi_1702):
    stages = find_unittest_stages(wfapi_1702, suites={"SMB Transform"})
    assert {s.suite for s in stages} == {"SMB Transform"}
    assert {s.node_id for s in stages} == {"274", "292"}
