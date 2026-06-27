"""Golden tests for the SVN changeSets parser."""

from __future__ import annotations

from datetime import UTC

from uta.ingest.svn_update import parse_change_sets


def test_change_parsed_with_utc_timestamp(change_sets_1702):
    parsed = parse_change_sets(change_sets_1702)
    assert len(parsed.changes) == 1
    change = parsed.changes[0]
    assert change.commit_id == "135136"
    assert change.author == "deploy"
    assert change.when.tzinfo == UTC
    assert change.message.startswith("LX-0")


def test_changed_paths_carry_edit_type(change_sets_1702):
    change = parse_change_sets(change_sets_1702).changes[0]
    assert len(change.paths) == 3
    assert all(p.edit_type == "edit" for p in change.paths)
    assert all(p.file.startswith("/trunk/lx/") for p in change.paths)
