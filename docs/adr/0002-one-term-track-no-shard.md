# One term for the parallel lanes: Track (no Shard)

The nightly build runs the full test suite in parallel lanes (`permanent`, `permanent_py39`; more
will follow, differing by interpreter, OS, or other execution environment). The code and docs had
grown two words for this: **track** (the lane, on test identity and results) and **shard** (the
per-build stage-execution record — `BuildShard`, `expected_shards` — and, sloppily, as a plain
synonym for track in `shard_correlated`). We decided **Track is the single canonical term** and
banned "shard" (`_Avoid_` in CONTEXT.md), renaming all depths in one clean break: code identifiers,
the `build_shards` → `build_tracks` table, the `EXPECTED_SHARDS` → `EXPECTED_TRACKS` setting
(breaking for operators, no compat alias — one `.env` edit), and the UI/help text.

Two alternatives were rejected. **Keeping two terms** (Track + a per-build-execution noun like
"Track Run"): the per-build record is 1:1 with track-within-build, triage conversation never needs
it as a standalone noun ("the `permanent_py39` track hadn't finished in build #1702" suffices), so
a second term is glossary weight without discriminating power. **Keeping the word "shard"** for
that record: in CI parlance sharding means *partitioning one test set across executors* — the
lanes here each run the *same* full suite, nothing is partitioned, so the word actively misleads
(and future contributors who know Jenkins would keep re-importing it; hence the `_Avoid_` entry).

Deliberately out of scope: build-completeness semantics stay a track *count*
(`expected_tracks`), not a name allowlist — changing that is behavior, not language.
