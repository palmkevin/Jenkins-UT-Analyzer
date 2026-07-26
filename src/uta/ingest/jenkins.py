"""Jenkins API client behind a narrow interface so the ingest pipeline can be tested offline.

The :class:`JenkinsClient` protocol is the seam: production uses :class:`HttpJenkinsClient`
(network), the offline suite uses ``tests/fakes`` fixtures-backed fakes. Only raw JSON crosses this
boundary — parsing lives in :mod:`uta.ingest.ut_report` / ``svn_update`` / ``wfapi``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

_CHANGESETS_TREE = (
    "changeSets[kind,items[commitId,timestamp,author[fullName],msg,paths[editType,file]]]"
)


@dataclass(frozen=True)
class LastBuild:
    """The job's most recent build — completed *or* still running (issue #184).

    ``building`` is Jenkins' own in-progress flag; when it is ``True`` this is the current
    in-progress build the overrunning detector observes. ``timestamp`` is the build's start
    (epoch millis, UTC — the same clock as :meth:`build_meta`'s ``timestamp``).
    """

    number: int
    building: bool
    timestamp: int


class JenkinsClient(Protocol):
    def build_meta(self, build: int) -> dict: ...
    def test_report(self, build: int) -> dict: ...
    def change_sets(self, build: int) -> dict: ...
    def wfapi(self, build: int) -> dict: ...
    def stage_describe(self, build: int, node_id: str) -> dict: ...
    def stage_log(self, build: int, node_id: str) -> dict: ...
    def last_completed_build(self) -> int | None: ...
    def last_build(self) -> LastBuild | None: ...


class HttpJenkinsClient:
    """Live client. Anonymous read works; a user+token is used if configured."""

    def __init__(
        self,
        job_url: str,
        *,
        user: str = "",
        token: str = "",
        verify: bool | str = True,
        timeout: float = 60.0,
    ) -> None:
        self._job_url = job_url.rstrip("/")
        auth = (user, token) if user and token else None
        self._client = httpx.Client(auth=auth, verify=verify, timeout=timeout)

    def _get_json(self, path: str, params: dict | None = None) -> dict:
        resp = self._client.get(f"{self._job_url}/{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    def build_meta(self, build: int) -> dict:
        return self._get_json(
            f"{build}/api/json",
            {"tree": "number,result,timestamp,duration,url,fullDisplayName"},
        )

    def test_report(self, build: int) -> dict:
        return self._get_json(f"{build}/testReport/api/json")

    def change_sets(self, build: int) -> dict:
        return self._get_json(f"{build}/api/json", {"tree": _CHANGESETS_TREE})

    def wfapi(self, build: int) -> dict:
        return self._get_json(f"{build}/wfapi/describe")

    def stage_describe(self, build: int, node_id: str) -> dict:
        """A stage's flow graph — its child step nodes (``stageFlowNodes``).

        The unittest console-log text lives on the stage's *Shell Script* step node, not the stage
        node itself (whose own ``wfapi/log`` is empty), so the ingest descends here to find it.
        """
        return self._get_json(f"{build}/execution/node/{node_id}/wfapi/describe")

    def stage_log(self, build: int, node_id: str) -> dict:
        """One pipeline stage's console log (the unittest console-log UT stages live only here)."""
        return self._get_json(f"{build}/execution/node/{node_id}/wfapi/log")

    def last_completed_build(self) -> int | None:
        """The job's most recent *completed* build number (the poll high-water mark)."""
        payload = self._get_json("api/json", {"tree": "lastCompletedBuild[number]"})
        last = payload.get("lastCompletedBuild") or {}
        return last.get("number")

    def last_build(self) -> LastBuild | None:
        """The job's most recent build — running or completed — for overrunning detection (#184)."""
        payload = self._get_json("api/json", {"tree": "lastBuild[number,building,timestamp]"})
        last = payload.get("lastBuild") or {}
        if last.get("number") is None or last.get("timestamp") is None:
            return None
        return LastBuild(
            number=last["number"],
            building=bool(last.get("building")),
            timestamp=last["timestamp"],
        )

    def close(self) -> None:
        self._client.close()
