# The data-change correlation window is relative to the previous build, not a fixed hour count

The `ut_ref` data-change correlation window used a fixed `DATA_CHANGE_LOOKBACK_HOURS = 12` lower
bound, sized when a build was assumed to be an overnight event. Once the true cadence was understood
(ADR-0003: the Permanent Pipeline runs **one build per commit**, ~15-20 builds per active weekday), a
12h window was shown to reach back over ~20 neighbouring builds — so a single data change was attached
as a candidate to ~20 builds at once, spuriously flipping episodes to `DATA_CHANGE`, skewing the
relevance tie-break, and suggesting the wrong `V_TRACKING` `USRCODE` as the contact. We changed the
window's lower bound to the **previous build's start**, so each change is a candidate for the first
build that ran after it. This self-adapts to cadence (a busy afternoon yields minute-scale windows; a
quiet weekend stretches to cover the whole gap), which no fixed hour count can do.

## Considered options

- **Keep a fixed lookback (12h, or shrink to ~1h).** Rejected: any fixed count is simultaneously too
  wide during commit bursts (overlapping many builds) and too narrow across weekend/holiday gaps
  (missing a real change that preceded the next build). It treats a symptom.
- **Anchor at the previous build's *end*.** Rejected in favour of its *start*. `ut_ref` data can
  change *during* a build's run: a test that already executed in the previous build misses the change
  and passes, while the next build runs fully against the changed data and fails — so the causal
  change occurred *inside the previous build's run window*. Anchoring at the previous build's end
  would exclude it and the real cause would be invisible. Anchoring at the start keeps it a candidate.

## Consequences

- A change that lands during build N-1's run is, by design, a candidate for **both** N-1 and N (the
  windows overlap by one build's run). This is deliberate: for a triage-*support* tool a spurious
  candidate is cheap (a human reviews it), a missing cause is expensive (it is invisible). Coverage is
  chosen over a clean partition.
- A new setting, **`data_change_max_lookback_days`** (default 30), caps how far back the lower bound
  reaches and is the fallback when there is no usable previous build (the first-ever build / cold
  start). 30 days comfortably covers any weekend/holiday gap while bounding a pathological outage. The
  old `data_change_lookback_hours` is removed (its fixed-window role no longer exists); the
  `data_change_tolerance_minutes` skew margin is unchanged.
- Attribution now depends on the previous build's `started_at` being present in the store. Cold-start
  back-fill ingests oldest-first and incremental polling sits above the high-water mark, so the
  predecessor is always available except for the first-ever build, which uses the cap fallback.
- This governs **data**-change candidates only. Code-change candidates come from the build's own
  Jenkins `changeSets` and are unaffected.
