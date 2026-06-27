"""Jenkins API client behind a narrow interface so the ingest pipeline can be tested offline.

The :class:`JenkinsClient` protocol is the seam: production uses :class:`HttpJenkinsClient`
(network), the offline suite uses ``tests/fakes`` fixtures-backed fakes. Only raw JSON crosses this
boundary — parsing lives in :mod:`uta.ingest.ut_report` / ``svn_update`` / ``wfapi``.
"""

from __future__ import annotations

from typing import Protocol

import httpx

_CHANGESETS_TREE = (
    "changeSets[kind,items[commitId,timestamp,author[fullName],msg,paths[editType,file]]]"
)


class JenkinsClient(Protocol):
    def build_meta(self, build: int) -> dict: ...
    def test_report(self, build: int) -> dict: ...
    def change_sets(self, build: int) -> dict: ...
    def wfapi(self, build: int) -> dict: ...
    def last_completed_build(self) -> int | None: ...


class HttpJenkinsClient:
    """Live client. Anonymous read works; a user+token is used if configured."""

    def __init__(
        self,
        job_url: str,
        *,
        user: str = "",
        token: str = "",
        verify: bool = False,
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

    def last_completed_build(self) -> int | None:
        """The job's most recent *completed* build number (the poll high-water mark)."""
        payload = self._get_json("api/json", {"tree": "lastCompletedBuild[number]"})
        last = payload.get("lastCompletedBuild") or {}
        return last.get("number")

    def close(self) -> None:
        self._client.close()
