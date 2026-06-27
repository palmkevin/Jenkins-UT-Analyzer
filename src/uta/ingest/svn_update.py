"""Parser for the SVN changeSets of a build — the candidate **code-change** source.

Source: ``GET /<build>/api/json?tree=changeSets[kind,items[commitId,timestamp,author[fullName],
msg,paths[editType,file]]]``. Timestamps are Jenkins epoch-millis (UTC).

Golden-tested against ``tests/fixtures/jenkins/changeSets_1702.json``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .clock import from_jenkins_millis


@dataclass(frozen=True)
class ChangedPath:
    edit_type: str  # "add" | "edit" | "delete"
    file: str


@dataclass(frozen=True)
class SvnChange:
    commit_id: str
    author: str
    when: datetime  # aware UTC
    message: str
    paths: tuple[ChangedPath, ...]


@dataclass
class ParsedChangeSets:
    changes: list[SvnChange] = field(default_factory=list)


def parse_change_sets(payload: dict) -> ParsedChangeSets:
    parsed = ParsedChangeSets()
    for change_set in payload.get("changeSets", []):
        for item in change_set.get("items", []):
            author = (item.get("author") or {}).get("fullName", "")
            paths = tuple(
                ChangedPath(edit_type=p.get("editType", ""), file=p.get("file", ""))
                for p in item.get("paths", [])
            )
            parsed.changes.append(
                SvnChange(
                    commit_id=str(item.get("commitId", "")),
                    author=author,
                    when=from_jenkins_millis(int(item["timestamp"])),
                    message=item.get("msg", ""),
                    paths=paths,
                )
            )
    return parsed
