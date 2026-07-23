"""Typed settings from environment (12-factor). See .env.example for every key."""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Jenkins ──────────────────────────────────────────────────────────────
    jenkins_base_url: str = "https://jenkins2.labsolution.lu"
    jenkins_job_path: str = "job/Development/job/lsdevbuild-build-release-permanent"
    jenkins_user: str = ""
    jenkins_api_token: str = ""
    # TLS verification is on by default. Set false only as a stopgap for an internal CA the host
    # doesn't trust yet; prefer pointing jenkins_ca_bundle at that CA's PEM instead of disabling.
    jenkins_verify_tls: bool = True
    # Path to a CA bundle (PEM) for verifying Jenkins' cert, e.g. an internal CA. Takes precedence
    # over jenkins_verify_tls when set (verification stays on, against this bundle).
    jenkins_ca_bundle: str = ""
    expected_tracks: int = 2
    # Also ingest the unittest console-log UT stages (no JUnit artifact — parsed from stage logs).
    ingest_unittest_stages: bool = True
    unittest_suites: str = "LXS,SMB Pricing,SMB Transform,ITF Highlevel,Uniface deploy unit tests"

    # ── Oracle ut_ref (read-only) ────────────────────────────────────────────
    ut_ref_host: str = "lsdb04"
    ut_ref_port: int = 1521
    ut_ref_service: str = "lsdb04pdb"
    ut_ref_user: str = "utestref01"
    ut_ref_password: str = ""
    ut_ref_thick: bool = False

    # ── SVN blame (test ownership = main developer, issue #114) ──────────────
    # Off by default: with it off no blame client is built, so the offline gate, local dev and the
    # public demo never shell out to `svn` — exactly like the Oracle/LLM live paths. Turn it on in a
    # deployment that can reach the SVN server to populate the dashboard "Owner" (the modal blame
    # author of each test's source file).
    svn_blame_enabled: bool = False
    # SVN URL under which a test's repo-relative `tests/dev/…` path resolves, e.g.
    # https://svn.labsolution.lu/svn/ls/trunk/lx . Tune to the real layout; empty disables blame.
    svn_repo_base_url: str = ""
    svn_user: str = ""  # optional — anonymous read works on some repos
    svn_password: str = ""

    # ── PostgreSQL ───────────────────────────────────────────────────────────
    database_url: str = "postgresql+psycopg://uta:uta@db:5432/uta"

    # ── Email (regression-only alert) ────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = 25
    smtp_from: str = ""
    smtp_recipients: str = ""  # comma-separated; empty disables email
    smtp_user: str = ""
    smtp_password: str = ""
    # STARTTLS before sending. Unset (None) defaults to on exactly when smtp_user is set —
    # credentials should not cross the wire in the clear. Set explicitly to force it either way.
    smtp_starttls: bool | None = None
    email_recovery_notice: bool = False

    # ── Auth / Keycloak OIDC (Phase-2, off by default; see .env.example) ──────
    # With the flag off the app is the Phase-1 honesty-system app (self-declared actor cookie) and
    # needs zero Keycloak access — local dev and the offline CI gate stay untouched.
    auth_enabled: bool = False
    oidc_server_metadata_url: str = (
        "https://auth.labsolution.lu/realms/labsolution/.well-known/openid-configuration"
    )
    oidc_client_id: str = "internal-ut-analyzer"
    oidc_client_secret: str = ""  # from Vault / deployment secret store — never committed
    oidc_post_logout_redirect: str = ""  # external base URL of this tool, e.g. https://uta.example/
    session_secret: str = ""  # signs the session cookie; required when auth_enabled

    # ── App ──────────────────────────────────────────────────────────────────
    app_default_actor: str = "test-user"
    # Externally reachable base URL of this dashboard, e.g. http://host:8000 — enables deep links
    # into the per-test record / build summary in alert emails when set. Empty (default) keeps the
    # emails link-free.
    app_base_url: str = ""
    flaky_transition_threshold: float = 0.3
    flaky_window_days: int = 30  # oscillation window for the flaky score
    pgtrgm_similarity_cutoff: float = 0.3
    kb_top_k: int = 5  # similar past cases surfaced per failure
    # "recently fixed" bucket window — a fix stays visible/confirmable this long.
    recently_fixed_days: int = 7
    # Max test rows rendered per dashboard section before it is capped with a "Load all N Tests"
    # link (keeps huge lists — the ~25k build-results table — responsive). 0 disables the cap.
    ui_row_limit: int = 50
    # Cold-start back-fill: on an empty store, ingest the last N completed builds oldest-first
    # (age N → age 1) before incremental polling takes over. Caps the bootstrap so a fresh DB does
    # not try to ingest every historical build from #1.
    backfill_depth: int = 10
    # Retention (issue #52): raw *passing/skipped* results are dropped once their build is older
    # than
    # this many days (failing results, builds, episodes, lifecycles, attributions and KB signatures
    # are kept forever). 0 keeps everything. Keep it comfortably above FLAKY_WINDOW_DAYS so the
    # flakiness sequence never loses in-window pass points.
    result_retention_days: int = 90
    # Finished (done/error) on-demand ingest jobs are dropped after this many days. 0 keeps all.
    ingest_job_retention_days: int = 30

    # ── External links (read-only deep links surfaced in the UI) ──────────────
    # Jira base for ticket links: {jira_base_url}/browse/<TICKET>.
    jira_base_url: str = "https://labsolution.atlassian.net"
    # FishEye changelog for SVN revisions: {fisheye_changelog_url}?cs=<revision>.
    fisheye_changelog_url: str = "https://fisheye.labsolution.lu/changelog/LS_TRUNK"
    # ZEPHYR (Kanoah Test Management) test-case deep link: {zephyr_test_case_url_prefix}<LX-T…>.
    zephyr_test_case_url_prefix: str = (
        "https://labsolution.atlassian.net/projects/LX?selectedItem="
        "com.atlassian.plugins.atlassian-connect-plugin:"
        "com.kanoah.test-manager__main-project-page#!/v2/testCase/"
    )

    # ── LLM hypothesis ────────────────────────────────────
    # Provider: "anthropic", "openai", or "" to auto-pick from whichever key is set (Anthropic wins
    # when both are). A chosen provider with no key ⇒ NoopHypothesisProvider (no model call;
    # llm_hypothesis stays NULL). Both keys are Platform/Console keys (pay-as-you-go), separate from
    # any Claude.ai or ChatGPT subscription.
    llm_provider: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # ── Ingest / correlation windows ───────────────────────────────────────────
    # Data changes precede the nightly build (the build's own window had none on #1702), so look
    # back
    # before the build start; the tolerance margin (B1) absorbs residual clock skew between Jenkins
    # and the Oracle ut_ref clock.
    data_change_lookback_hours: int = 12
    data_change_tolerance_minutes: int = 5
    # Scheduled poll cadence (seconds) for `uta poll`.
    poll_interval_seconds: int = 300

    # ── Poller resilience (issue #51) ──────────────────────────────────────────
    # In-tick attempts per build for *transient* errors (network/5xx/DB blips) — exponential
    # backoff between attempts, base doubling each time (2s, 4s, 8s, …).
    poll_retry_attempts: int = 3
    poll_retry_base_seconds: float = 2.0
    # Failing ticks (one attempt per tick) before a build is quarantined: recorded, alerted, and
    # skipped so the high-water mark advances past it.
    quarantine_after_attempts: int = 3
    # /health flags the poller stale after this many poll intervals without a *successful* tick.
    poller_stale_after_intervals: int = 5

    @field_validator("smtp_starttls", mode="before")
    @classmethod
    def _empty_smtp_starttls_is_unset(cls, v: object) -> object:
        # .env.example lists every key, so a copied `SMTP_STARTTLS=` (empty) must mean "unset"
        # (credential-derived default), not a boolean parse error at startup.
        return None if v == "" else v

    @property
    def jenkins_job_url(self) -> str:
        return f"{self.jenkins_base_url.rstrip('/')}/{self.jenkins_job_path.strip('/')}"

    @property
    def jenkins_verify(self) -> bool | str:
        """httpx's ``verify`` value: a CA bundle path if set, else the on/off flag."""
        return self.jenkins_ca_bundle or self.jenkins_verify_tls

    @property
    def email_recipients(self) -> tuple[str, ...]:
        return tuple(r.strip() for r in self.smtp_recipients.split(",") if r.strip())

    @property
    def unittest_suite_set(self) -> frozenset[str]:
        return frozenset(s.strip() for s in self.unittest_suites.split(",") if s.strip())


def get_settings() -> Settings:
    return Settings()
