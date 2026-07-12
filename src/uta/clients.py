"""Build the external clients from settings — shared by the CLI, the poller and the control panel.

These translate the env :class:`~uta.config.Settings` into the concrete Jenkins client, Oracle feed,
SMTP sender and LLM provider (or their no-op / ``None`` fallbacks when a credential is absent). They
live here — not in ``cli`` — so the in-app on-demand ingest (issue #16) constructs exactly the same
clients the CLI back-fill does, with the same "no credential ⇒ skip that source" rules.
"""

from __future__ import annotations

from datetime import timedelta

from uta.config import Settings


def build_client(settings: Settings):
    from uta.ingest.jenkins import HttpJenkinsClient

    return HttpJenkinsClient(
        settings.jenkins_job_url,
        user=settings.jenkins_user,
        token=settings.jenkins_api_token,
        verify=settings.jenkins_verify,
    )


def build_feed(settings: Settings):
    """The Oracle ut_ref feed, or ``None`` if no password is set (data candidates skipped)."""
    if not settings.ut_ref_password:
        return None
    from uta.refdb.oracle import OracleTrackingFeed

    return OracleTrackingFeed(
        settings.ut_ref_host,
        settings.ut_ref_port,
        settings.ut_ref_service,
        settings.ut_ref_user,
        settings.ut_ref_password,
        thick=settings.ut_ref_thick,
    )


def build_svn_blame_client(settings: Settings):
    """The SVN blame client (test ownership = main developer, #114), or ``None`` when disabled.

    Gated by ``SVN_BLAME_ENABLED`` and a configured ``SVN_REPO_BASE_URL`` — with either unset no
    client is built and ``main_developer`` stays NULL, so the offline gate and demo never touch SVN.
    """
    if not settings.svn_blame_enabled or not settings.svn_repo_base_url:
        return None
    from uta.refdb.svn import SvnCliBlameClient

    return SvnCliBlameClient(
        settings.svn_repo_base_url,
        username=settings.svn_user,
        password=settings.svn_password,
    )


def windows(settings: Settings) -> tuple[timedelta, timedelta]:
    return (
        timedelta(hours=settings.data_change_lookback_hours),
        timedelta(minutes=settings.data_change_tolerance_minutes),
    )


def build_email_sender(settings: Settings):
    """The SMTP sender, or ``None`` when email is not configured (host + recipients required)."""
    if not settings.smtp_host or not settings.email_recipients:
        return None
    from uta.delivery.email import SmtpEmailSender

    return SmtpEmailSender(
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_from,
        user=settings.smtp_user,
        password=settings.smtp_password,
        starttls=settings.smtp_starttls,
    )


def build_hypothesis_provider(settings: Settings):
    """The configured LLM provider (Anthropic or OpenAI), or Noop when no key is set.

    ``LLM_PROVIDER`` picks explicitly; empty auto-selects whichever key is configured (Anthropic
    wins if both). A chosen provider with no key falls back to Noop (no model call).
    """
    from uta.llm import NoopHypothesisProvider

    choice = (settings.llm_provider or "").lower()
    if not choice:
        if settings.anthropic_api_key:
            choice = "anthropic"
        elif settings.openai_api_key:
            choice = "openai"

    if choice == "anthropic" and settings.anthropic_api_key:
        from uta.llm.claude import AnthropicHypothesisProvider

        return AnthropicHypothesisProvider(
            settings.anthropic_api_key, model=settings.anthropic_model
        )
    if choice == "openai" and settings.openai_api_key:
        from uta.llm.openai_provider import OpenAIHypothesisProvider

        return OpenAIHypothesisProvider(settings.openai_api_key, model=settings.openai_model)
    return NoopHypothesisProvider()
