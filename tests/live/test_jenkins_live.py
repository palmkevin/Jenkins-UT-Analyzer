"""Live Jenkins checks — LOCAL ONLY (needs network to Jenkins). Never run in CI.

Run with: ``pytest -m live tests/live/test_jenkins_live.py``
"""

from __future__ import annotations

import pytest

from uta.config import get_settings
from uta.ingest.jenkins import HttpJenkinsClient
from uta.ingest.ut_report import parse_test_report
from uta.ingest.wfapi import parse_wfapi

pytestmark = pytest.mark.live

BUILD = 1702


@pytest.fixture(scope="module")
def client():
    s = get_settings()
    return HttpJenkinsClient(s.jenkins_job_url, user=s.jenkins_user, token=s.jenkins_api_token)


def test_live_report_has_both_tracks(client):
    parsed = parse_test_report(client.test_report(BUILD))
    assert parsed.tracks == {"permanent", "permanent_py39"}
    # The real #1702 has ~25k results — far more than the trimmed fixture.
    assert len(parsed.cases) > 1000


def test_live_wfapi_shards_complete(client):
    run = parse_wfapi(client.wfapi(BUILD))
    assert run.is_complete(expected_shards=2)
