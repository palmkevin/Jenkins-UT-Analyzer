"""Demo mode — a fully synthetic, offline dataset for integration tests and online hosting.

No external system (Jenkins / Oracle ``ut_ref`` / FishEye / SMTP / LLM) is reachable when the app
runs "in the wild" (e.g. the public Render deployment, or CI). This package fabricates a realistic
run history entirely in-process so the whole ingest -> analysis -> dashboard stack can be exercised
against **committed, synthetic** data:

- :mod:`uta.demo.dataset` — a fake Jenkins client + tracking feed that generate deterministic build
  payloads shaped exactly like the real ones (so the real parsers/pipeline run unchanged).
- :mod:`uta.demo.seed` — drives the real :func:`uta.ingest.pipeline.ingest_build` over those builds
  into any session factory, then adds a few human triage actions.
- :mod:`uta.demo.app` — an ephemeral SQLite store, seeded on startup, wired to the real web app.

All data here is invented. It contains **no** LIMS / patient / ``MODDATA`` strings and no real
person names — the same discipline the committed fixtures follow.
"""

from __future__ import annotations

from uta.demo.dataset import SyntheticJenkins, SyntheticTrackingFeed
from uta.demo.seed import seed_demo_data

__all__ = ["SyntheticJenkins", "SyntheticTrackingFeed", "seed_demo_data"]
