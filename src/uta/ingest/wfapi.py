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

# The deferred **unittest console-log** stages report results only in their stage log (no JUnit
# artifact). Their stage name is ``"<suite> - <track>"``; the suite set is configurable because the
# pipeline must not treat unrelated ``"<x> - permanent"`` stages (e.g. "Clean logs") as test stages.
DEFAULT_UNITTEST_SUITES = frozenset(
    {"LXS", "SMB Pricing", "SMB Transform", "ITF Highlevel", "Uniface deploy unit tests"}
)
_LOG_STAGE_RE = re.compile(r"^(?P<suite>.+) - (?P<track>permanent(?:_py39)?)$")


@dataclass(frozen=True)
class LogStage:
    """A unittest console-log stage to ingest: its flow ``node_id`` (for ``wfapi/log``) + track."""

    node_id: str
    suite: str
    track: str
    status: str


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


def find_unittest_stages(
    payload: dict, suites: frozenset[str] | set[str] = DEFAULT_UNITTEST_SUITES
) -> list[LogStage]:
    """The console-log UT stages whose suite is in ``suites`` — one per ``(suite, track)``.

    Used by the pipeline to fetch each stage's ``wfapi/log`` and parse it with
    :mod:`uta.ingest.unittest_log`. The devUTs shard stages are deliberately excluded (they're in
    the JUnit report and matched by :data:`_UT_STAGE_RE`); only the named ``suites`` are returned.
    """
    found: list[LogStage] = []
    for stage in payload.get("stages", []):
        m = _LOG_STAGE_RE.match(stage.get("name", ""))
        if not m or m.group("suite") not in suites:
            continue
        found.append(
            LogStage(
                node_id=str(stage.get("id", "")),
                suite=m.group("suite"),
                track=m.group("track"),
                status=stage.get("status", ""),
            )
        )
    return found


# The step that runs the tests and prints the console output. The stage node's own ``wfapi/log`` is
# empty; the text lives on this child step node.
_LOG_STEP_NAME = "Shell Script"


def find_log_step_node(describe_payload: dict, step_name: str = _LOG_STEP_NAME) -> str | None:
    """The ``node_id`` of the stage's step that holds the console log (its ``Shell Script`` step).

    Returns the first matching ``stageFlowNodes`` entry's id, or ``None`` if the stage has no such
    step (then the caller falls back to the stage node, which simply yields an empty log).
    """
    for node in describe_payload.get("stageFlowNodes", []):
        if node.get("name") == step_name:
            return str(node.get("id", "")) or None
    return None
