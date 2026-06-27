"""Shared offline test fixtures. Nothing here touches a gated external system."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(rel: str) -> dict:
    return json.loads((FIXTURES / rel).read_text())


@pytest.fixture
def test_report_1702() -> dict:
    return _load("jenkins/testReport_1702.json")


@pytest.fixture
def change_sets_1702() -> dict:
    return _load("jenkins/changeSets_1702.json")


@pytest.fixture
def wfapi_1702() -> dict:
    return _load("jenkins/wfapi_1702.json")
