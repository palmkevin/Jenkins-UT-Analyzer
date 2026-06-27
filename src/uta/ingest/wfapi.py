"""Parser for ``/<build>/wfapi/describe`` — per-shard UT stage timing & completeness.

The UT execution stages are ``devUTs: Execute - permanent`` and ``devUTs: Execute - permanent_py39``
(one per track). Each carries ``startTimeMillis`` + ``durationMillis`` (Jenkins epoch-millis, UTC).
"completeness" = all expected tracks reported a stage. Used to build the complete-run baseline and
the data-change correlation window.

Golden-tested against ``tests/fixtures/jenkins/wfapi_1702.json``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from .clock import from_jenkins_millis

# The UT shard stages, e.g. "devUTs: Execute - permanent_py39".
_UT_STAGE_RE = re.compile(r"^devUTs: Execute - (permanent(?:_py39)?)$")


@dataclass(frozen=True)
class ShardTiming:
    track: str
    status: str
    start: datetime  # aware UTC
    end: datetime  # aware UTC

    @property
    def duration(self) -> timedelta:
        return self.end - self.start


@dataclass
class RunTiming:
    name: str
    status: str
    start: datetime
    end: datetime
    shards: dict[str, ShardTiming]

    def is_complete(self, expected_shards: int) -> bool:
        return len(self.shards) >= expected_shards

    @property
    def window(self) -> tuple[datetime, datetime]:
        """The span covering all UT shards (falls back to the overall run span)."""
        if self.shards:
            start = min(s.start for s in self.shards.values())
            end = max(s.end for s in self.shards.values())
            return start, end
        return self.start, self.end


def parse_wfapi(payload: dict) -> RunTiming:
    start = from_jenkins_millis(int(payload["startTimeMillis"]))
    end = start + timedelta(milliseconds=int(payload.get("durationMillis", 0)))
    shards: dict[str, ShardTiming] = {}
    for stage in payload.get("stages", []):
        m = _UT_STAGE_RE.match(stage.get("name", ""))
        if not m:
            continue
        track = m.group(1)
        s_start = from_jenkins_millis(int(stage["startTimeMillis"]))
        s_end = s_start + timedelta(milliseconds=int(stage.get("durationMillis", 0)))
        shards[track] = ShardTiming(
            track=track,
            status=stage.get("status", ""),
            start=s_start,
            end=s_end,
        )
    return RunTiming(
        name=payload.get("name", ""),
        status=payload.get("status", ""),
        start=start,
        end=end,
        shards=shards,
    )
