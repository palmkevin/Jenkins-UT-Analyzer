"""Block until the configured Postgres accepts connections, then exit.

Bitbucket Pipelines has no equivalent of GitHub Actions' service ``--health-cmd``, so a step
can start while its `postgres` service container is still booting. The migration tests *skip*
rather than fail when Postgres is unreachable (by design, so `pytest -m "not live"` stays green
on a dev box without one) — which means a startup race would silently drop the destructive
migration test from the merge gate instead of breaking the build. This closes that hole.

Exits non-zero if the database never becomes reachable within the timeout.
"""

from __future__ import annotations

import sys
import time

from sqlalchemy import text

from uta.config import get_settings
from uta.db import make_engine

TIMEOUT_SECONDS = 60.0
POLL_INTERVAL_SECONDS = 1.0


def main() -> int:
    url = get_settings().database_url
    if not url.startswith("postgresql"):
        print(f"wait_for_db: DATABASE_URL is not Postgres ({url!r}) — nothing to wait for.")
        return 0

    deadline = time.monotonic() + TIMEOUT_SECONDS
    attempt = 0
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        attempt += 1
        engine = make_engine(url)
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"wait_for_db: Postgres ready after {attempt} attempt(s).")
            return 0
        except Exception as exc:  # noqa: BLE001 — any failure to connect means "not ready yet"
            last_error = exc
            time.sleep(POLL_INTERVAL_SECONDS)
        finally:
            engine.dispose()

    print(
        f"wait_for_db: Postgres still unreachable after {TIMEOUT_SECONDS:.0f}s "
        f"({attempt} attempts). Last error: {last_error}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
