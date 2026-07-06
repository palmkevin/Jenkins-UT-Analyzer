"""Offline test of the Slice-0 read-only run view (SQLite + injected session factory)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from tests.fakes import FakeJenkinsClient
from uta.db import Base, make_session_factory
from uta.ingest.pipeline import ingest_build
from uta.web.app import create_app


@pytest.fixture
def client():
    # StaticPool + a single shared connection so the request thread sees the same in-memory DB.
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    sf = make_session_factory(engine)
    ingest_build(FakeJenkinsClient(), sf, 1702)
    return TestClient(create_app(session_factory=sf))


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert body["poller"] == "never"  # no heartbeat row — this deployment runs no poller


def test_run_view_renders_results(client):
    resp = client.get("/runs/1702")
    assert resp.status_code == 200
    body = resp.text
    assert "Run #1702" in body
    assert "permanent_py39" in body
    assert "ut_accounting.ac_csvc.TestClass" in body


def test_unknown_run_is_graceful(client):
    resp = client.get("/runs/9999")
    assert resp.status_code == 200
    assert "No run ingested" in resp.text


def test_job_runs_page_lists_the_run(client):
    resp = client.get("/runs")
    assert resp.status_code == 200
    body = resp.text
    assert "Job runs" in body
    # The ingested build is listed and links to its detail page.
    assert 'href="/runs/1702"' in body
    # The run-health timeline chart (issue #53): inline SVG, no JS.
    assert '<svg class="timeline-chart"' in body
    assert '<polyline class="FAILED"' in body
