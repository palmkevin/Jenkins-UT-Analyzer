"""The whitelist of runtime-tunable thresholds and how overrides are resolved (issue #16).

A **single source of truth** for *which* settings the control panel may override and their type +
bounds. Everything else in :class:`~uta.config.Settings` — secrets, URLs, connection strings — is
**not** overridable: an override is only ever accepted for a key in :data:`TUNABLES`, so a stray or
malicious key can never reach the DB or shadow a secret.

Resolution is a pure merge: :func:`effective_settings` takes the env-loaded ``Settings`` and the
stored overrides and returns a **copy** with the overridden attributes replaced (coerced to their
declared type). Non-overridden keys — and every non-tunable attribute/property — pass through
untouched, so callers keep using the same ``Settings`` object and its properties.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from uta.config import Settings
from uta.models import SettingOverride


@dataclass(frozen=True)
class Tunable:
    """One overridable threshold: its ``Settings`` attribute name + display/validation metadata.

    ``kind`` is ``"int"`` or ``"float"``; ``minimum``/``maximum`` bound the accepted value (both
    inclusive). ``group`` clusters related knobs in the UI; ``help`` is the one-line explanation
    shown beside the field.
    """

    key: str
    label: str
    group: str
    kind: str
    minimum: float
    maximum: float
    help: str

    def coerce(self, raw: str | int | float) -> int | float:
        """Parse ``raw`` to this tunable's type and validate its bounds. Raises ``ValueError``."""
        try:
            value: int | float = int(raw) if self.kind == "int" else float(raw)
        except (TypeError, ValueError) as exc:
            noun = "an integer" if self.kind == "int" else "a number"
            raise ValueError(f"{self.label} must be {noun}") from exc
        if value < self.minimum or value > self.maximum:
            lo, hi = self._fmt(self.minimum), self._fmt(self.maximum)
            raise ValueError(f"{self.label} must be between {lo} and {hi}")
        return value

    def _fmt(self, value: float) -> str:
        return str(int(value)) if self.kind == "int" else str(value)


# The whitelist. Ordered/grouped for display; the key is the ``Settings`` attribute it overrides.
TUNABLES: tuple[Tunable, ...] = (
    Tunable(
        "flaky_transition_threshold",
        "Flaky threshold",
        "Flakiness",
        "float",
        0.0,
        1.0,
        "Oscillation score above which a test is flagged flaky.",
    ),
    Tunable(
        "flaky_window_days",
        "Flaky window (days)",
        "Flakiness",
        "int",
        1,
        365,
        "How far back the flaky oscillation score looks.",
    ),
    Tunable(
        "pgtrgm_similarity_cutoff",
        "Similarity cutoff",
        "Knowledge base",
        "float",
        0.0,
        1.0,
        "Minimum trigram similarity for a KB match to surface.",
    ),
    Tunable(
        "kb_top_k",
        "KB top-k",
        "Knowledge base",
        "int",
        1,
        50,
        "How many similar past cases to surface per failure.",
    ),
    Tunable(
        "recently_fixed_days",
        "Recently-fixed window (days)",
        "Triage",
        "int",
        1,
        90,
        "How long a fix stays in the recently-fixed bucket.",
    ),
    Tunable(
        "ui_row_limit",
        "Dashboard row cap",
        "Triage",
        "int",
        0,
        5000,
        "Max rows a section renders before a 'Load all' link (0 disables the cap).",
    ),
    Tunable(
        "expected_shards",
        "Expected shards",
        "Ingest",
        "int",
        1,
        10,
        "Shards a build must report to be considered complete.",
    ),
    Tunable(
        "data_change_lookback_hours",
        "Data-change lookback (hours)",
        "Ingest",
        "int",
        0,
        168,
        "How far before a build's start to look for correlated data changes.",
    ),
    Tunable(
        "data_change_tolerance_minutes",
        "Data-change tolerance (min)",
        "Ingest",
        "int",
        0,
        120,
        "Clock-skew margin widening the data-change correlation window.",
    ),
    Tunable(
        "backfill_depth",
        "Back-fill depth",
        "Ingest",
        "int",
        1,
        500,
        "Builds a cold-start poll ingests on an empty store.",
    ),
    Tunable(
        "result_retention_days",
        "Passing-result retention (days)",
        "Retention",
        "int",
        0,
        3650,
        "Days to keep raw passing/skipped results (failures are kept forever; 0 keeps all). "
        "Keep it above the flaky window.",
    ),
    Tunable(
        "ingest_job_retention_days",
        "Ingest-job retention (days)",
        "Retention",
        "int",
        0,
        365,
        "Days to keep finished (done/error) ingest jobs (0 keeps all).",
    ),
)

TUNABLES_BY_KEY: dict[str, Tunable] = {t.key: t for t in TUNABLES}


def load_overrides(session: Session) -> dict[str, str]:
    """The stored overrides as ``{key: raw_value}`` — only recognised (whitelisted) keys.

    A key that is no longer in the whitelist (e.g. a renamed tunable left over in an old DB) is
    ignored rather than applied, so a stale row can never inject an unknown attribute.
    """
    rows = session.scalars(select(SettingOverride)).all()
    return {r.key: r.value for r in rows if r.key in TUNABLES_BY_KEY}


def effective_settings(base: Settings, overrides: dict[str, str]) -> Settings:
    """``base`` with every valid override applied — a copy; non-tunable attributes are untouched.

    An override that fails to coerce (corrupt row, out-of-bounds) is skipped so a bad row can never
    take the whole app down — the env default stands for that key. Returns ``base`` unchanged when
    there are no applicable overrides.
    """
    update: dict[str, int | float] = {}
    for key, raw in overrides.items():
        tunable = TUNABLES_BY_KEY.get(key)
        if tunable is None:
            continue
        try:
            update[key] = tunable.coerce(raw)
        except ValueError:
            continue
    return base.model_copy(update=update) if update else base


def set_override(session: Session, key: str, raw: str, *, actor: str | None = None) -> None:
    """Upsert an override for a whitelisted key after validating its value. Raises ``ValueError``.

    The stored value is the canonical coerced form (so ``"5"`` and ``" 5 "`` normalise identically).
    """
    tunable = TUNABLES_BY_KEY.get(key)
    if tunable is None:
        raise ValueError(f"{key!r} is not an overridable setting")
    value = str(tunable.coerce(raw))
    row = session.get(SettingOverride, key)
    if row is None:
        row = SettingOverride(key=key)
        session.add(row)
    row.value = value
    row.updated_by = actor


def clear_override(session: Session, key: str) -> None:
    """Remove an override, reverting the key to its env default. No-op if none is set."""
    session.execute(delete(SettingOverride).where(SettingOverride.key == key))
