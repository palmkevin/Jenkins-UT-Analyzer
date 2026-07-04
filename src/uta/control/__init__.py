"""In-app control panel service layer (issue #16).

The dashboard's operational surface — tune thresholds at runtime, trigger ingest / re-analysis on
demand, and read poller health — without editing env and redeploying. Split into:

- :mod:`uta.control.tunables` — the whitelist of overridable thresholds, coercion/validation, and
  merging DB overrides onto the env :class:`~uta.config.Settings`.
- :mod:`uta.control.jobs` — creating and running on-demand ingest jobs (back-fill semantics).
- :mod:`uta.control.heartbeat` — the scheduled poller's heartbeat (read + write).
"""
