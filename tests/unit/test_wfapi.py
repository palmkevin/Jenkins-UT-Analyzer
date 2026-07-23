"""Golden tests for the per-shard timing parser + completeness."""

from __future__ import annotations

import copy
from datetime import UTC

import pytest

from uta.ingest.wfapi import find_log_step_node, find_unittest_stages, parse_wfapi


def _with_ut_stage_status(payload: dict, track: str, status: str) -> dict:
    """The fixture payload with one UT shard stage's status replaced."""
    payload = copy.deepcopy(payload)
    for stage in payload["stages"]:
        if stage["name"] == f"devUTs: Execute - {track}":
            stage["status"] = status
            return payload
    raise AssertionError(f"no UT stage for track {track!r} in fixture")


def test_both_ut_shards_parsed(wfapi_1702):
    build = parse_wfapi(wfapi_1702)
    assert set(build.shards) == {"permanent", "permanent_py39"}


def test_shard_timings_are_utc(wfapi_1702):
    build = parse_wfapi(wfapi_1702)
    for shard in build.shards.values():
        assert shard.start.tzinfo == UTC
        assert shard.end > shard.start


def test_completeness_uses_expected_shard_count(wfapi_1702):
    build = parse_wfapi(wfapi_1702)
    assert build.is_complete(expected_shards=2)
    assert not build.is_complete(expected_shards=3)


@pytest.mark.parametrize("status", ["SUCCESS", "UNSTABLE", "FAILED"])
def test_completeness_accepts_finished_stage_statuses(wfapi_1702, status):
    """UNSTABLE/FAILED are test outcomes, not truncation — the shard still ran to the end."""
    build = parse_wfapi(_with_ut_stage_status(wfapi_1702, "permanent_py39", status))
    assert build.is_complete(expected_shards=2)


@pytest.mark.parametrize(
    "status",
    ["ABORTED", "IN_PROGRESS", "PAUSED", "PAUSED_PENDING_INPUT", "NOT_EXECUTED", "SOME_NEW_STATUS"],
)
def test_completeness_rejects_unfinished_stage_statuses(wfapi_1702, status):
    """An aborted build still lists both UT stages, so the shard count alone lies (issue #83);
    unknown statuses fail safe to incomplete."""
    build = parse_wfapi(_with_ut_stage_status(wfapi_1702, "permanent_py39", status))
    assert set(build.shards) == {"permanent", "permanent_py39"}  # both stages present…
    assert not build.is_complete(expected_shards=2)  # …yet the build is not complete


def test_window_spans_all_shards(wfapi_1702):
    build = parse_wfapi(wfapi_1702)
    start, end = build.window
    assert start == min(s.start for s in build.shards.values())
    assert end == max(s.end for s in build.shards.values())


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


def test_find_log_step_node_returns_shell_script_child():
    """The console text lives on the stage's Shell Script step node, not the stage node itself."""
    describe = {
        "id": "292",
        "stageFlowNodes": [
            {"id": "294", "name": "Set environment variables", "status": "SUCCESS"},
            {"id": "295", "name": "Shell Script", "status": "FAILED"},
            {"id": "296", "name": "Set stage result to unstable", "status": "SUCCESS"},
        ],
    }
    assert find_log_step_node(describe) == "295"


def test_find_log_step_node_returns_none_without_a_shell_step():
    """No Shell Script step → None, so the caller falls back to the (empty) stage node."""
    assert find_log_step_node({"id": "292", "stageFlowNodes": []}) is None
    assert find_log_step_node({}) is None
