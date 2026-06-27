"""Typed settings from environment (12-factor). See .env.example for every key."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Jenkins ──────────────────────────────────────────────────────────────
    jenkins_base_url: str = "https://jenkins2.labsolution.lu"
    jenkins_job_path: str = "job/Development/job/lsdevbuild-build-release-permanent"
    jenkins_user: str = ""
    jenkins_api_token: str = ""
    expected_shards: int = 2

    # ── Oracle ut_ref (read-only) ────────────────────────────────────────────
    ut_ref_host: str = "lsdb04"
    ut_ref_port: int = 1521
    ut_ref_service: str = "lsdb04pdb"
    ut_ref_user: str = "utestref01"
    ut_ref_password: str = ""
    ut_ref_thick: bool = False

    # ── PostgreSQL ───────────────────────────────────────────────────────────
    database_url: str = "postgresql+psycopg://uta:uta@db:5432/uta"

    # ── Email (regression-only alert, §5) ────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = 25
    smtp_from: str = ""
    smtp_recipients: str = ""  # comma-separated; empty disables email
    smtp_user: str = ""
    smtp_password: str = ""
    email_recovery_notice: bool = False

    # ── App ──────────────────────────────────────────────────────────────────
    app_default_actor: str = "test-user"
    flaky_transition_threshold: float = 0.3
    flaky_window_days: int = 30  # oscillation window for the flaky score (§3)
    pgtrgm_similarity_cutoff: float = 0.3
    kb_top_k: int = 5  # similar past cases surfaced per failure (§4)
    # §0 "recently fixed" bucket window — a fix stays visible/confirmable this long (PLAN §0).
    recently_fixed_days: int = 7

    # ── LLM hypothesis (§4 / Milestone 5) ────────────────────────────────────
    # Empty key ⇒ NoopHypothesisProvider (no model call; llm_hypothesis stays NULL). The key is a
    # Developer Console key (pay-as-you-go billing, separate from any Claude subscription).
    anthropic_api_key: str = ""
    llm_model: str = "claude-opus-4-8"

    # ── Ingest / correlation windows ───────────────────────────────────────────
    # Data changes precede the nightly run (the run's own window had none on #1702), so look back
    # before the run start; the tolerance margin (B1) absorbs residual clock skew between Jenkins
    # and the Oracle ut_ref clock.
    data_change_lookback_hours: int = 12
    data_change_tolerance_minutes: int = 5
    # Scheduled poll cadence (seconds) for `uta poll`.
    poll_interval_seconds: int = 300

    @property
    def jenkins_job_url(self) -> str:
        return f"{self.jenkins_base_url.rstrip('/')}/{self.jenkins_job_path.strip('/')}"

    @property
    def email_recipients(self) -> tuple[str, ...]:
        return tuple(r.strip() for r in self.smtp_recipients.split(",") if r.strip())


def get_settings() -> Settings:
    return Settings()
