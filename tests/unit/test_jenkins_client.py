"""TLS verification for the Jenkins HTTP client (issue #54) — offline, no network call.

``verify=False`` used to be hardcoded, silently disabling TLS verification for all Jenkins
traffic. It must now default to on and be driven by the typed ``jenkins_verify_tls`` /
``jenkins_ca_bundle`` settings.
"""

from __future__ import annotations

import httpx

from uta.clients import build_client
from uta.config import Settings
from uta.ingest.jenkins import HttpJenkinsClient


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
