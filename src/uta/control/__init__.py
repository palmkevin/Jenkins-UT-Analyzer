"""In-app control panel service layer (issue #16).

The dashboard's operational surface — tune thresholds at runtime, trigger ingest / re-analysis on
demand, and read poller health — without editing env and redeploying. Split into:

- :mod:`uta.control.tunables` — the whitelist of overridable thresholds, coercion/validation, and
  merging DB overrides onto the env :class:`~uta.config.Settings`.
- :mod:`uta.control.jobs` — creating and running on-demand ingest jobs (back-fill semantics),
  plus startup recovery of jobs orphaned by a restart (issue #51).
- :mod:`uta.control.heartbeat` — the scheduled poller's heartbeat (read + write).
- :mod:`uta.control.quarantine` — the poller's per-build failure ledger: attempt counting and the
  quarantine that lets ingest advance past a persistently-failing build (issue #51).
- :mod:`uta.control.health` — the real ``/health`` evaluation: DB ping + heartbeat freshness, with
  the latched stale-poller ops alert (issue #51).
"""
