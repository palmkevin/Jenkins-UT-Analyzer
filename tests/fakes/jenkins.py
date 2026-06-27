"""Fixtures-backed fake implementing the JenkinsClient protocol."""

from __future__ import annotations

import json
from pathlib import Path

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "jenkins"


class FakeJenkinsClient:
    """Serves the committed #1702 golden fixtures. Unknown builds raise KeyError."""

    def __init__(self, build: int = 1702, fixtures_dir: Path = _FIXTURES) -> None:
        self._build = build
        self._dir = fixtures_dir

    def _load(self, name: str, build: int) -> dict:
        if build != self._build:
            raise KeyError(f"no fixture for build {build}")
        return json.loads((self._dir / name).read_text())

    def build_meta(self, build: int) -> dict:
        return self._load(f"build_{self._build}.json", build)

    def test_report(self, build: int) -> dict:
        return self._load(f"testReport_{self._build}.json", build)

    def change_sets(self, build: int) -> dict:
        return self._load(f"changeSets_{self._build}.json", build)

    def wfapi(self, build: int) -> dict:
        return self._load(f"wfapi_{self._build}.json", build)
