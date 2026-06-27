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

    # ── App ──────────────────────────────────────────────────────────────────
    app_default_actor: str = "test-user"
    flaky_transition_threshold: float = 0.3
    pgtrgm_similarity_cutoff: float = 0.3

    @property
    def jenkins_job_url(self) -> str:
        return f"{self.jenkins_base_url.rstrip('/')}/{self.jenkins_job_path.strip('/')}"


def get_settings() -> Settings:
    return Settings()
