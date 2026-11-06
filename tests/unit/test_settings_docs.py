"""The settings reference stays in sync with ``config.py``.

``.env.example`` and the README Configuration tables are hand-maintained, so they rot silently;
these checks pin them to :class:`~uta.config.Settings` (env-example-defaults-diverge).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from uta.config import Settings

ROOT = Path(__file__).resolve().parents[2]

#: ``.env.example`` keys read by compose, not by ``Settings``.
_COMPOSE_ONLY = {"POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "WEB_PORT"}


def _env_example() -> dict[str, str]:
    pairs: dict[str, str] = {}
    for line in (ROOT / ".env.example").read_text().splitlines():
        match = re.match(r"^([A-Z0-9_]+)=(.*)$", line)
        if match:
            pairs[match.group(1)] = match.group(2)
    return pairs


_ENV = _env_example()


@pytest.mark.parametrize("key", sorted(k for k in _ENV if k not in _COMPOSE_ONLY))
def test_env_example_value_matches_the_config_default(key):
    """A copied ``.env.example`` must not silently change behaviour versus an unset variable."""
    name = key.lower()
    assert name in Settings.model_fields, f"{key} in .env.example is not a Settings field"
    default = Settings.model_fields[name].default
    value = _ENV[key]
    parsed = getattr(Settings(_env_file=None, **{name: value}), name)
    if value == "" and default in ("", None):
        return  # an empty placeholder for an unset-by-default key
    assert parsed == default, f"{key}: .env.example has {value!r}, config.py defaults {default!r}"


def _readme_config_vars() -> set[str]:
    """Every ``VAR`` named in a README Configuration table row's first cell."""
    text = (ROOT / "README.md").read_text()
    section = text.split("## Configuration", 1)[1].split("\n## ", 1)[0]
    names: set[str] = set()
    for line in section.splitlines():
        if line.startswith("| `"):
            first_cell = line.split("|")[1]
            names.update(re.findall(r"`([A-Z0-9_]+)`", first_cell))
    return names


def test_every_setting_has_a_readme_configuration_row():
    """Every ``config.py`` field has a README row (readme-config-table-missing-settings)."""
    missing = sorted(
        f.upper() for f in Settings.model_fields if f.upper() not in _readme_config_vars()
    )
    assert missing == [], f"settings with no README Configuration row: {missing}"
