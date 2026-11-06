"""TLS verification for the Jenkins HTTP client (issue #54) — offline, no network call.

``verify=False`` used to be hardcoded, silently disabling TLS verification for all Jenkins
traffic. It must now default to on and be driven by the typed ``jenkins_verify_tls`` /
``jenkins_ca_bundle`` settings.
"""

from __future__ import annotations

import httpx
import pytest

from uta.clients import build_client
from uta.config import Settings
from uta.ingest.jenkins import HttpJenkinsClient, LastBuild


def _client_with_response(payload: dict) -> HttpJenkinsClient:
    """An HttpJenkinsClient whose transport returns ``payload`` for any GET (no real network)."""
    client = HttpJenkinsClient("https://jenkins.example/job")
    client._client = httpx.Client(
        transport=httpx.MockTransport(lambda _req: httpx.Response(200, json=payload))
    )
    return client


def test_last_build_parses_in_progress_build():
    client = _client_with_response(
        {"lastBuild": {"number": 1710, "building": True, "timestamp": 1712000000000}}
    )
    assert client.last_build() == LastBuild(number=1710, building=True, timestamp=1712000000000)


def test_last_build_parses_completed_build():
    client = _client_with_response(
        {"lastBuild": {"number": 1710, "building": False, "timestamp": 1712000000000}}
    )
    assert client.last_build() == LastBuild(number=1710, building=False, timestamp=1712000000000)


def test_last_build_none_when_no_build_yet():
    assert _client_with_response({"lastBuild": None}).last_build() is None
    assert _client_with_response({}).last_build() is None


def _captured_verify(monkeypatch) -> dict:
    """Capture the ``verify`` kwarg httpx.Client is constructed with, without opening a real
    connection or touching the filesystem for a CA bundle path that may not exist in the test env.
    """
    captured = {}

    def fake_init(self, *args, **kwargs):
        captured["verify"] = kwargs.get("verify")

    monkeypatch.setattr(httpx.Client, "__init__", fake_init)
    return captured


def test_default_client_verifies_tls(monkeypatch):
    captured = _captured_verify(monkeypatch)
    HttpJenkinsClient("https://jenkins.example/job")
    assert captured["verify"] is True


def test_client_can_disable_verification_explicitly(monkeypatch):
    captured = _captured_verify(monkeypatch)
    HttpJenkinsClient("https://jenkins.example/job", verify=False)
    assert captured["verify"] is False


def test_build_client_defaults_to_verifying_tls(monkeypatch):
    captured = _captured_verify(monkeypatch)
    build_client(Settings(jenkins_verify_tls=True, jenkins_ca_bundle=""))
    assert captured["verify"] is True


def test_build_client_honors_verify_tls_false_setting(monkeypatch):
    captured = _captured_verify(monkeypatch)
    build_client(Settings(jenkins_verify_tls=False, jenkins_ca_bundle=""))
    assert captured["verify"] is False


def test_build_client_ca_bundle_wins_over_verify_flag(monkeypatch):
    captured = _captured_verify(monkeypatch)
    build_client(Settings(jenkins_verify_tls=False, jenkins_ca_bundle="/etc/ssl/internal-ca.pem"))
    assert captured["verify"] == "/etc/ssl/internal-ca.pem"


def _client_with_routes(routes: dict[str, httpx.Response]) -> HttpJenkinsClient:
    """An HttpJenkinsClient answering by URL path suffix; anything unrouted 404s."""

    def handler(req: httpx.Request) -> httpx.Response:
        for suffix, resp in routes.items():
            if req.url.path.endswith(suffix):
                return resp
        return httpx.Response(404)

    client = HttpJenkinsClient("https://jenkins.example/job")
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    return client


def test_test_report_404_is_an_empty_report():
    """A run that published no JUnit results 404s on testReport — that's "no tests", not "gone"
    (testreport-404-quarantines-failed-builds)."""
    assert _client_with_routes({}).test_report(1702) == {"suites": []}


def test_test_report_other_http_errors_still_raise():
    client = _client_with_routes({"/testReport/api/json": httpx.Response(500)})
    with pytest.raises(httpx.HTTPStatusError) as info:
        client.test_report(1702)
    assert info.value.response.status_code == 500


def test_build_meta_404_still_raises():
    with pytest.raises(httpx.HTTPStatusError) as info:
        _client_with_routes({}).build_meta(1702)
    assert info.value.response.status_code == 404
