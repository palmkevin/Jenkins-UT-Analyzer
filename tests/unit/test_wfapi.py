"""Golden tests for the per-shard timing parser + completeness."""

from __future__ import annotations

from datetime import UTC

from uta.ingest.wfapi import parse_wfapi


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
