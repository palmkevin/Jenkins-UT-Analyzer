# Overrunning builds are a live signal, not a Build Incident

Issue #172 asks us to make **never-ending** in-progress pipelines visible (so a human can stop one)
and, separately, to flag **duration regressions** on completed builds. ADR-0005 shaped the Build
Incident so the reserved kinds `hung` and `slow` could later be added as incident kinds "with no
schema change." Revisiting the `hung` half: a still-running build has **no recovery event** and
**no error / failing stage / signature** to correlate, enrich, or attribute — the Classification /
Hypothesis / Knowledge-Base machinery a Build Incident carries has nothing to act on. So we decided
an **Overrunning Build is surfaced as an ephemeral, poller-observed live banner on the triage
dashboard — not persisted as a Build Incident**. The durable triage record comes only from the
existing `aborted` incident when a human stops the build. `IncidentKind.HUNG` is therefore
**removed**. (`slow` — a *completed*-build duration regression — remains a real Build Incident kind,
tracked as a separate child of #172.)

## Considered options

- **Persist a `HUNG` Build Incident (ADR-0005's original assumption).** Rejected: an overrunning
  build has no natural close (it is still running), nothing to classify or hypothesise about, and no
  failure signature; a persisted incident would either dangle open forever or duplicate the `aborted`
  incident that already opens the moment someone acts on the banner.
- **Web tier queries Jenkins live on each render.** Rejected: it would break the standing
  "web reads only the DB" boundary (the reason the offline gate and the public demo run with zero
  Jenkins access) and could not be represented in the demo without special-casing. Instead the
  **poller** observes the current in-progress build each tick and writes a single-row snapshot the
  web tier reads like everything else.

## Consequences

- **The poller is the single source of truth for overrunning-ness.** Each tick it fetches Jenkins'
  current in-progress build, compares elapsed against the **Expected Duration** (median wall-clock of
  the last 20 `SUCCESS`/`UNSTABLE` builds — the same baseline the `slow` detector will use), and
  stores an `overrunning` flag on the snapshot. The UI reflects that stored flag for the highlight and
  computes **only** `elapsed = now − started_at` live at render, so the banner ticks up between polls
  while staying a pure reflection of stored facts. The highlight can therefore lag the true crossing
  by up to one poll interval — an accepted trade-off for a dumb, DB-only UI.
- **The poll interval drops to 60 s** (from 300 s) for a near-real-time banner; an idle tick stays
  cheap (a couple of Jenkins calls).
- **One email per overrunning build**, fired on the first tick the poller sets the flag and de-duped
  by persisting that flag (survives a poller restart); it reuses the existing SMTP config/recipients.
  Because the eventual `aborted` incident is already silent, there is no double alert.
- **Revises ADR-0005**: of the two reserved kinds, only `slow` lands as a Build Incident kind;
  `hung` does not exist as an incident. The Overrunning Build and the (shared) Expected Duration are
  recorded in CONTEXT.md.
