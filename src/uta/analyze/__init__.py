"""Post-ingest analysis (Milestone 2): baseline diff, lifecycle/episodes, classification.

Ingest (``uta.ingest``) persists the raw facts of one run; ``analyze`` turns the accumulated
runs into the cross-run picture the dashboard needs:

- :mod:`uta.analyze.baseline` — pick the most-recent *complete* baseline and diff against it.
- :mod:`uta.analyze.lifecycle` — drive the FAILING/FIXED/REMOVED state machine + failure episodes.
- :mod:`uta.analyze.classify` — deterministic CODE/DATA/INFRA/UNKNOWN from windowed candidates.
- :mod:`uta.analyze.error_type` — derive the per-result error type from status + stack trace.

Everything here is computed only from persisted facts (results, candidates), so re-running the
analysis for an already-processed run is idempotent.
"""

from __future__ import annotations
