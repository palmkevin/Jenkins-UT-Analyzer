"""Unit tests for the SVN blame boundary: path mapping + blame-XML tally (issue #114).

No `svn` binary, no network — the pure helpers are exercised directly, and the CLI client's
failure path is proven by pointing it at a binary that does not exist.
"""

from __future__ import annotations

from uta.refdb.svn import (
    SvnCliBlameClient,
    main_developer_from_blame_xml,
    to_repo_path,
)


def test_to_repo_path_strips_volatile_checkout_prefix():
    assert (
        to_repo_path("/opt/ls/lx/release/permanent/tests/dev/ut_core/co_time.py")
        == "tests/dev/ut_core/co_time.py"
    )
    # py39 track checkout resolves to the same repo path (track is not part of the SVN tree).
    assert (
        to_repo_path("/opt/ls/lx/release/permanent_py39/tests/dev/ut_core/co_time.py")
        == "tests/dev/ut_core/co_time.py"
    )


def test_to_repo_path_none_when_not_a_dev_test_or_missing():
    assert to_repo_path(None) is None
    assert to_repo_path("") is None
    assert to_repo_path("/opt/ls/lx/product/co_time.py") is None  # no tests/dev segment


def _blame_xml(entries: list[tuple[int, str | None, int]]) -> str:
    """Build `svn blame --xml`-shaped output from (line_no, author, revision) tuples."""
    rows = []
    for line_no, author, rev in entries:
        if author is None:
            rows.append(f'<entry line-number="{line_no}"></entry>')
        else:
            rows.append(
                f'<entry line-number="{line_no}">'
                f'<commit revision="{rev}"><author>{author}</author>'
                f"<date>2026-01-01T00:00:00Z</date></commit></entry>"
            )
    return f'<?xml version="1.0"?><blame><target path=".">{"".join(rows)}</target></blame>'


def test_blame_tally_picks_the_modal_author():
    xml = _blame_xml([(1, "jdoe", 10), (2, "jdoe", 11), (3, "asmith", 12)])
    assert main_developer_from_blame_xml(xml) == "jdoe"


def test_blame_tie_breaks_toward_the_more_recent_author():
    # One line each: tie on count -> the author with the higher (more recent) revision wins.
    xml = _blame_xml([(1, "olddev", 5), (2, "newdev", 99)])
    assert main_developer_from_blame_xml(xml) == "newdev"


def test_blame_ignores_uncommitted_lines_and_empty_input():
    xml = _blame_xml([(1, None, 0), (2, "jdoe", 7)])
    assert main_developer_from_blame_xml(xml) == "jdoe"
    assert main_developer_from_blame_xml(_blame_xml([(1, None, 0)])) is None


def test_blame_returns_none_on_unparsable_xml():
    assert main_developer_from_blame_xml("not xml <<<") is None


def test_cli_client_returns_none_when_svn_is_missing():
    client = SvnCliBlameClient(
        "https://svn.example/svn/ls/trunk/lx", svn_binary="uta-no-such-svn-binary"
    )
    assert client.main_developer("tests/dev/ut_core/co_time.py") is None
