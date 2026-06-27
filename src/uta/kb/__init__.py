"""Knowledge base & learning loop (PLAN §4) — all on stock Postgres, no vector store.

Three cooperating pieces:

- :mod:`uta.kb.signature` — the **named, test-covered** normalization mask set + hash. It decides
  what "the same failure" means for recurrence, prediction and flakiness grouping, so it is treated
  as a first-class component (PLAN §4 calls it load-bearing).
- :mod:`uta.kb.store` — upsert a :class:`~uta.models.kb.FailureSignature` per failing result at
  ingest and link the result to it; idempotent on re-ingest.
- :mod:`uta.kb.retrieval` — exact recurrence (signature hash) and fuzzy "similar past cases"
  (``pg_trgm`` on Postgres; a difflib fallback offline), both **provenance-weighted** so confirmed/
  corrected human knowledge ranks above unvalidated AI guesses.
"""

from __future__ import annotations
