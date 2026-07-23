"""Live Jenkins checks — LOCAL ONLY (needs network to Jenkins). Never build in CI.

Run with: ``pytest -m live tests/live/test_jenkins_live.py``
"""

from __future__ import annotations

import pytest

from uta.config import get_settings
from uta.ingest.jenkins import HttpJenkinsClient
from uta.ingest.unittest_log import parse_unittest_log
from uta.ingest.ut_report import parse_test_report
from uta.ingest.wfapi import find_log_step_node, find_unittest_stages, parse_wfapi

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
    build = parse_wfapi(client.wfapi(BUILD))
    assert build.is_complete(expected_shards=2)


def test_live_unittest_console_log_stages_parse(client):
    """Discover the unittest console-log stages and parse at least one real stage log."""
    stages = find_unittest_stages(client.wfapi(BUILD))
    assert stages, "expected unittest console-log stages on #1702"
    cases = []
    for stage in stages:
        # The console text is on the stage's Shell Script step node, not the stage node itself.
        step_id = find_log_step_node(client.stage_describe(BUILD, stage.node_id)) or stage.node_id
        cases += parse_unittest_log(
            client.stage_log(BUILD, step_id), track=stage.track, suite_name=stage.suite
        )
    # The stages do produce per-test results, both tracks represented.
    assert cases
    assert {c.track for c in cases} <= {"permanent", "permanent_py39"}
