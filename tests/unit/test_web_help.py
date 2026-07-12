"""The in-app help/docs page (/help) — a static explainer, no seeded data required."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from uta.db import Base, make_session_factory
from uta.web.app import create_app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    sf = make_session_factory(engine)
    return TestClient(create_app(session_factory=sf))


def test_help_page_renders(client):
    resp = client.get("/help")
    assert resp.status_code == 200
    body = resp.text
    assert "How the LLM contributes" in body
    assert "HUMAN_CORRECTED" in body


def test_help_link_in_navbar_and_highlighted(client):
    resp = client.get("/help")
    assert resp.status_code == 200
    body = resp.text
    assert '<a class="nav-link active" aria-current="page" href="/help">Help</a>' in body


def test_help_not_highlighted_on_other_pages(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert '<a class="nav-link" href="/help">Help</a>' in resp.text
