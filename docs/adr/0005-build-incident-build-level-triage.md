# Build Incident: a build-level triage entity, not a test-level one

The whole triage/enrichment/knowledge-base machinery hung off the **Failure Episode**, which is
strictly *test-level* — keyed to a `suite/class/method`, one fail→fix cycle per test. That leaves a
gap: a Build whose *pipeline* fails or is aborted (a `FAILURE`/`ABORTED` Jenkins result, usually
with no usable test report because the run died around or before the UT stage) has no test identity
to attach to, so it was invisible to triage (issue #171). We introduced a **Build Incident** — a new,
first-class, *build-level* triage entity that is the build-level counterpart to the Failure Episode —
rather than stretching the test-level episode to cover it. An incident **spans a streak** of
consecutive non-green builds (opened by the first `FAILURE`/`ABORTED`, closed by the next
`SUCCESS`/`UNSTABLE`), carries an **Incident Kind** (`pipeline_failure` / `aborted`), and reuses the
existing Classification / Hypothesis / Attribution / provenance surfaces. It is deliberately shaped
so the reserved kinds `hung` and `slow` (issue #172 — never-ending and duration-regressed builds) can
be added later as new detectors with **no schema change**.

## Considered options

- **Reuse the Failure Episode entity.** Rejected: an episode is defined by a test identity and its
  per-test lifecycle; a pipeline failure has neither. Overloading it with a nullable test identity
  would corrupt the "one lifecycle per `suite/class/method`" invariant (ADR-0002) and every
  test-scoped query (fail-rate windows, flakiness, baseline diff) would have to learn to exclude the
  test-less rows. The two concepts share *downstream* surfaces (triage, KB, attribution), not
  *identity*.
- **A narrow, failure-only entity (e.g. `BuildFailure`).** Rejected because issue #172 is explicitly
  in view: its "never-ending" and "ran-too-long" cases are also *build-level conditions a human must
  document with KB + LLM help* — the same downstream workflow, a different detector. A failure-only
  entity would force either a second near-identical entity or a migration when #172 lands. A general
  **Build Incident** with a kind discriminator absorbs #172 by adding enum values, not tables.
- **One incident per bad build (no streak).** Rejected: a pipeline stays red across several
  consecutive builds until someone fixes it, so per-build incidents would flood the triage queue with
  near-duplicate rows to dismiss. Collapsing a consecutive non-green run into one incident (mirroring
  how an episode collapses a consecutive fail run) keeps one triage unit per real problem. Mixed kinds
  within a streak stay one incident (kind = whatever opened it).

## Consequences

- **Recovery keys off the top-level Jenkins result only.** Any `SUCCESS` *or* `UNSTABLE` build closes
  an open incident, independent of the `EXPECTED_TRACKS` completeness check — an `UNSTABLE` build
  proves the pipeline itself is healthy again, and its failing tests are the Failure Episode
  subsystem's concern. In-progress builds are ignored here (that is #172's job).
- **Detection folds into the existing ingest path**, gated by `INGEST_BUILD_INCIDENTS` (default on,
  mirroring `INGEST_UNITTEST_STAGES`). It must run **even when test analysis is skipped** (a
  `FAILURE` build is usually "incomplete"), and the high-water mark must still advance past a failed
  build so the *next* build's recovery is seen. No new poller/service.
- **Enrichment is split by kind.** `pipeline_failure` gets the full stack — Change Candidates over the
  same previous-build-anchored window (ADR-0004), deterministic Classification (`infrastructure`
  becomes load-bearing), an LLM Hypothesis, and the Confirm/correct provenance loop. `aborted` is
  human-documented only (a human deliberately stopped it — nothing to correlate, no signature).
- **Failure Signatures are namespaced (`TEST` vs `INCIDENT`), never cross-matched.** An incident's
  signature comes from the *failing stage's* log (fallback: console tail); a broken-deploy-stage error
  and a test assertion are different domains, so matching one against the other would pollute both
  knowledge bases. The signature machinery (normalize→hash→`pg_trgm`) is shared; the lookup is
  filtered by kind.
- **The single ticket field is generalized and renamed**, on *both* Failure Episodes and Build
  Incidents: the old `jira_ticket` becomes **Cause Ticket** (the ticket describing the cause) and two
  fields are added — **Resolution Ticket** (the ticket the assignee is working on to resolve it, *not*
  a resolved-claim) and **Assignee** (who is fixing it, distinct from the causing person in
  Attribution). These answer issue #171's "who is managing it / related tickets" and are useful on
  test episodes too, so they were not scoped to incidents.
- Incidents are kept **forever** like episodes (retention prunes neither). Email alerts fire only on a
  *newly opened* `pipeline_failure` (not every build in the streak, not `aborted`, not recovery);
  Teams-channel delivery is deferred to issue #181.
