# Jenkins UT Analyzer — Plan (Output-Focused Design)

## Context

Integration tests ("unittests"/UT) run in a Jenkins job triggered by every commit to the SVN
trunk. The tests run against a `ut` database kept in sync with a reference database (`ut_ref`)
before each run. **One person monitors this pipeline full-time**: after each run they compare
failures against the previous run, isolate *new* failures, and attribute each to a probable
cause — a **code change** (a trunk commit), a **data change** in `ut_ref`, **infrastructure**,
or **other**. They then contact the responsible developer (for code) or the data-change author
plus the UT's main developer (for data, found via tracking tables + SVN history), and watch the
next run to confirm a fix.

This triage is slow, person-dependent, and not reproducible. **This tool automates the
evidence-gathering and presents a clear, persistent picture per test and per run** — and learns
from the human's explanations over time.

> **Scope of this document:** this phase defines **what the tool outputs** — the information it
> presents and tracks. Technical choices are recorded at the end for reference but are *not* the
> focus, and there is **no implementation/execution plan** here yet. A separate **execution /
> phasing plan** (milestones, what v1 ships vs defers) is the planned next document.

## How the pipeline works (inputs the tool relies on)

- **SVN update step:** early in the pipeline the job runs an SVN update; **this step's output is
  the authoritative list of code changes** (revisions, authors, changed paths) pulled into the
  run. The tool reads this rather than querying SVN separately for "what changed this run."
- **Timing matters:** for **data** changes there is *no* changelog — only **timestamp comparison**
  against `ut_ref` tracking tables. So the tool must capture, precisely, **when each run (and each
  parallel shard) started and finished**, to define the time window in which a data change could
  have affected the run. **Clock discipline is therefore load-bearing:** Jenkins, the parallel
  shards, and the Oracle `ut_ref` DB may not share a clock or timezone, and data attribution rests
  *entirely* on these timestamps. All times are **normalized to UTC on ingest**, the **source clock
  is recorded** alongside each timestamp, and the data-change window carries a **configurable
  tolerance margin** to absorb residual skew. Getting this wrong silently corrupts every
  data-change candidate.
- **Parallel execution → one merged report:** test execution is split across multiple parallel
  steps for speed, then **all results are collected and merged into a single global UT execution
  report**. The tool consumes the merged report, but retains **per-shard start/finish times** for
  accurate data-change windowing.
- **Reference DB:** `ut_ref` tracking tables record data changes with a change timestamp and the
  author of the change.

---

## Users & identity (who is acting)

Every human action the tool records — acknowledging a failure, confirming a predicted cause,
entering a reason, overriding the AI — is **attributed to a user**. Attribution is what makes the
triage queue (§0) and the learning loop (§4) work: "not yet acknowledged" only means something if
the tool knows *who* would acknowledge, and the knowledge base is far more valuable when each
entry carries provenance.

Identity is introduced in **two phases**, deliberately decoupled so the tool is useful before any
auth infrastructure exists:

- **Phase 1 — self-declared user (no real authentication).** This phase targets the in-development
  testing period, *not* production. There is no login screen, no passwords, no SSO. The actor is
  obtained the cheapest way that still produces a *meaningful* name: the user **self-declares an
  identity** — a name picker / free-text field stored in the browser (cookie / localStorage), with
  a configurable default of **`test-user`** when none is chosen. All actions are stamped with that
  string and a timestamp. This unblocks the entire workflow from day one — the monitor can
  acknowledge, confirm, and annotate immediately — while letting several real people exercise
  acknowledgement-attribution and the learning provenance during testing (rather than every action
  collapsing to one indistinguishable `test-user`). Every record is already shaped to carry a real
  user id later. **No trust is implied** — a self-declared name is an honesty-system label for the
  dev phase, deliberately not access control.
- **Phase 2 — Keycloak / Kerberos SSO (later).** Real authentication via the existing Keycloak
  (Kerberos SSOT). Because Phase 1 already stamps an identity on every action, this phase only
  swaps *how* the identity is obtained (an auth layer in front of the app + a real user id on the
  session) — **no data-model change**: the `actor` field that held `test-user` now holds the
  authenticated principal. Login, per-user views ("my acknowledgements"), and access control
  become possible but are **not required earlier**.

> **Design rule:** the persisted identity is a plain `actor` string from the start. Phase 1 writes
> the self-declared name (default `test-user`); Phase 2 writes the Keycloak principal. Nothing
> downstream needs to know which phase produced it.

---

# THE EXPECTED OUTPUT

This is the heart of the plan. The tool produces several output surfaces, all backed by a
persistent history so state and trends survive across runs.

## 0. Main working view — the daily triage queue (primary landing surface)

This is the **first screen the monitor opens** and the view they live in day to day. It is not a
per-run report (that is §2) — it is the **current, cross-run state of everything that needs
attention**, organized into the three buckets the monitor actually thinks in:

1. **★ New failing tests — not yet acknowledged.** Tests that are `FAILING` **and have no
   acknowledgement** (including reopened regressions, whose acknowledgement was cleared). This is
   the action queue — the work that has just arrived. Each row shows the test identity, when/which
   run it first failed, the predicted cause + confidence, and an **Acknowledge** action (stamps the
   acting user from §1). Sorted newest-first; this bucket should ideally be driven to empty.
2. **★ Tests still failing.** Tests that are `FAILING` **and acknowledged** — the open caseload
   being worked. Shows age of failure (runs + days), triage status, the assigned/causing person,
   and a one-line cause. This is "what is still broken and being chased." Tests that went `REMOVED`
   while a failure was open are surfaced here with a distinct **Removed** flag (deleted / renamed /
   quarantined — needs a human decision), so a disappearance is never mistaken for a fix.
3. **★ Tests recently fixed.** Tests that transitioned to `FIXED` (ran and passed again) within a
   recent window (default the **last N runs / last 7 days**, configurable) — so a fix is
   **visible and confirmable** before it scrolls out of view. Shows the fixing run + date and the
   recorded reason. Lets the monitor confirm the fix held and close the loop, and gives
   stakeholders a "what got resolved lately" glance.

Each bucket links straight into the per-test record (§1) for full evidence and editing. The
buckets derive directly from the **lifecycle state** (`FAILING` / `FIXED` / `REMOVED`) and the
orthogonal **acknowledgement** attribute (§1), so no separate bookkeeping is needed — the view is
just a projection of state. Counts per bucket double as the at-a-glance health indicator.

> The distinction between bucket 1 and bucket 2 is **acknowledgement**, which is why a user
> identity (§ Users & identity) is required even in Phase 1: "not yet acknowledged" is defined
> relative to a recorded actor.

## 1. Per-test record (the centerpiece)

For **every test that is or has been failing**, the tool maintains a rich record. Fields the user
explicitly requested are marked ★; the rest are suggestions to consider.

### Identity & lifecycle
- **Test identity** — suite / class / method, and which parallel shard it ran in. The persisted
  key is the **canonical fully-qualified name**; renames/moves are handled by aliasing so history
  survives — see *Identity stability* below.
- ★ **Current state** — managed by the app as a small state machine. Two things were deliberately
  separated, because conflating them is what made the earlier `NEW → FAILING → FIXED` model too
  thin:
  - **Lifecycle state** (about the test result): `FAILING` → `FIXED`, plus `REMOVED` and a
    `FLAKY` cross-cutting flag (see §3). Transitions:
    - `FAILING → FIXED` — the test **ran and passed** in a later run.
    - `FIXED → FAILING` (**reopen / regression**) — a previously-fixed test fails again. This does
      **not** overwrite history: it opens a **new failure episode** (see below), increments a
      `reopen_count`, and clears acknowledgement so it re-enters the New bucket.
    - `FAILING → REMOVED` — the test was failing but is **absent from the latest merged report**
      (deleted, renamed, or quarantined). Kept distinct from `FIXED` so a disappearance is never
      silently counted as a fix. A removed test that reappears resumes its lifecycle.
  - **Acknowledgement** is an **orthogonal attribute**, *not* a lifecycle state: a flag +
    acknowledging actor + timestamp. It is what splits the New vs Still-failing buckets (§0); it
    says nothing about whether the test passes. (Previously `NEW`/`FAILING` tried to encode this
    inside the state machine, which muddied both.)
- **Failure episodes** — the record keeps a **history of episodes** (one per fail→fix cycle), each
  with its own first-failure run, fixed-in run, cause/reason, and age. "Current state" reflects the
  latest episode; counts and flakiness (§3) aggregate across all of them. This is what makes
  regressions first-class instead of erasing the prior story.
- ★ **First failure** — link to the Jenkins run that *first* triggered the **current episode's**
  failure **+ date/time** (the all-time first failure is also retained across episodes).
- ★ **Last failing run** — link to the **UT execution report** of the most recent run where it
  failed **+ date/time**.
- ★ **Fixed-in run** — link to the Jenkins run that fixed it **+ date/time**, set **only when the
  test ran and passed again** — explicitly *not* set on `REMOVED` (disappeared ≠ fixed).
- **Age of failure** — how long the current episode has been broken: number of runs and elapsed
  days from its first failure to fix (or to now if still failing). Makes "long-standing vs
  brand-new" obvious at a glance.
- **Identity stability** — tests get renamed or moved between classes; a naive key would reset all
  lifecycle and flakiness history on a rename. The tool keeps an **alias table**: a `test_identity`
  row may carry an `alias_of` pointer, and all history/flakiness queries follow it. When a failing
  test disappears in the same run that a closely-matching new identity appears (same method name in
  a new class, same class new method, or near-identical failure signature), the tool **suggests an
  alias** which the monitor **confirms with one click** (kept human-confirmed, matching the
  assistive philosophy; a manual "merge identities" action also exists). Until confirmed, the old
  identity is treated as `REMOVED` and the new one as `FAILING`, so nothing is lost either way.
  **Phasing:** the **manual "merge identities" action ships in v1**; the **automatic alias
  *suggestion*** is a fuzzy-matching subsystem of its own and is **post-v1** — the
  `REMOVED`/`FAILING` fallback already loses no history while it is absent, so it can be added later
  without redesign.
- **Error type** — assertion/value mismatch vs error/exception vs timeout/infra,
  derived from the result + stack trace.

### Attribution (gathered by the tool, confirmed by the human)
- **Predicted cause + confidence** — deterministic classification:
  `CODE_CHANGE` / `DATA_CHANGE` / `INFRASTRUCTURE` / `UNKNOWN`, with the evidence behind it.
  *v1 commitment:* the **time-window filtering** below — "these changes fall inside this run's
  window" — which is deterministic and stands on its own; the human attributes the cause from that
  evidence. A **relevance ranking + confidence score** is an **explicit later enhancement**, fed by
  the §4 knowledge base once it has confirmed-reason history to rank against (e.g. "this test
  historically fails on `ut_ref` changes to table X"). Emitting a confidence number against an empty
  KB on day one would be a fabricated number, so it is deliberately deferred rather than guessed.
- **Candidate code changes** — revisions from the **SVN update step** that fall inside the run's
  time window, with committer(s) and changed paths, presented **chronologically** (relevance
  ranking is the later enhancement noted above).
- **Candidate data changes** — `ut_ref` tracking-table changes inside the run's
  time window, with the **change author** and change timestamp.
- **UT ownership** — the test's main developer from SVN history/blame, as a fallback contact.
- **LLM hypothesis** — a short, human-readable summary of the most likely cause,
  written from the deterministic signals **and** similar past cases from the knowledge base (§4).
- ★ **Causing person** — **entered by the person in charge** (may differ from the predicted one).
- ★ **Reason for failure** — **entered by the person in charge**; free text. This is the key input
  that feeds the knowledge base (§4).
- **Conclusion provenance + confidence tier** — every cause/reason carries *how it was reached*,
  because the knowledge base (§4) weights entries by this, not just by their text:
  - `AI_UNCONFIRMED` — LLM/deterministic suggestion, nobody has validated it yet (treated as a
    guess; weak learning signal).
  - `AI_CONFIRMED` — a user clicked **Confirm** on the AI suggestion (strong positive signal).
  - `HUMAN_CORRECTED` — the AI suggested X, the user overrode it to Y (the *strongest* signal:
    disagreements are where the system learns most — the original AI value is retained alongside
    the correction).
  - `HUMAN_ENTERED` — entered with no AI suggestion in play (ground truth).
  A one-click **Confirm** action sits next to each AI suggestion. It is deliberately cheap so a
  full-time monitor produces a high volume of *validated* labels; corrections are rarer but carry
  the most weight. **Who** confirmed/corrected and **when** is stamped from the acting user
  (§ Users & identity).
- **Triage status** — `UNTRIAGED` / `INVESTIGATING` / `ROOT-CAUSED` / `RESOLVED`,
  plus who acknowledged it, so two monitors don't duplicate work.

### Context links
- Direct links to: the failing test's section in the merged UT report, the full Jenkins console
  log, the stack trace, and the relevant SVN revision(s).

## 2. Run-level summary

For each processed Jenkins run: build link, SVN revision(s), start/finish (overall + per shard),
totals (pass/fail/skip), and the diff vs the baseline run:
**new failures (regressions)**, **newly fixed**, **still failing**, and **flaky** — each row
linking to the per-test record above. This is the "what changed since last run" view the monitor
checks first.

**Baseline = the most recent *complete* run** — not blindly the immediately previous one. A run is
**complete** when it finished (not aborted/cancelled) and **all expected shards reported** their
merged results; otherwise it is `incomplete`. Diffing against a partial or aborted run produces
phantom "regressions" and "fixes" (tests look failed/missing only because a shard never ran), so:
- Incomplete runs are still **stored and shown**, but **flagged** and **skipped** when picking a
  baseline — the tool walks back to the last complete run.
- The expected shard count is **configurable**; a run missing shards is marked incomplete
  automatically.
- The run summary states **which run was used as baseline**, so the diff is never ambiguous.

This still matches the monitor's habit ("compare to the last good run") while being robust to the
real-world cases where a run doesn't fully complete.

## 3. Flakiness / failure-history tracking

Some tests flicker — they fail more often than others. Because the tool keeps full history, for
**any test it can show** (requested):
- ★ **Has it failed before?** and **when did it last fail.**
- ★ **How often has it failed total**, and **how often in the last X days**
  (**default X = 30 days**, configurable).
- **Flakiness score — based on *oscillation*, not on "no change."** Because **every** run is
  triggered by a trunk commit, "fails then passes *without any code/data change*" is almost never
  true and can't be the test — there is always a change in play. Instead the tool measures how much
  a test **flip-flops**:
  - Over the window, count **state transitions** in its pass/fail sequence (`pass→fail→pass→fail…`).
    A clean regression is **one** transition (`pass→fail`, then stays failing); a clean fix is one
    (`fail→pass`, then stays passing). **Many transitions = flaky.**
  - **Gaps are not transitions.** Incomplete runs (§2) and runs where the test was absent leave
    *holes* in the sequence; these are treated as **missing data points, not state changes**, so a
    shard that never reported is never miscounted as a `fail→pass` flip. The sequence is built only
    from runs in which the test actually produced a result.
  - **Flakiness score = transitions ÷ runs** over the window (equivalently, a fail-rate strictly
    between 0 and 1 *combined with* ≥1 back-and-forth flip). A test that is solidly failing
    (fail-rate ≈ 1, no flips) is a **regression**, not flaky; a test that bounces is **FLAKY**.
  - This needs **no** "was there a change?" determination, so it's well-defined for this pipeline.
    The correlation signals (candidate code/data changes) are still attached for triage, but they
    do **not** gate the flaky flag.
- **Pattern** — e.g. consecutive-run failures vs intermittent, and whether it tends
  to fail on a specific shard (shard-correlated flips are a strong infra/flaky tell).
- A dedicated **"flaky leaderboard"** view ranking the most unstable tests, so chronic offenders
  get attention separately from genuine regressions.

## 4. Knowledge base & learning loop

Every **reason for failure** and **causing person** — whether AI-suggested-then-confirmed or
human-entered — is stored against a **failure signature** (test identity + normalized error
message/stack trace), **together with its provenance tier** (§1). This turns one-off human
knowledge into a growing, queryable asset:

> **What "normalized signature" means (and why it's load-bearing).** Two runs of the same bug
> almost never produce byte-identical error text — line numbers, timestamps, object ids, temp
> paths, memory addresses and dynamic values differ every time. If we keyed the knowledge base on
> the *raw* message, nothing would ever match itself and the whole learning loop would be dead. So
> before hashing, the tool **normalizes** the error/stack into a stable shape by masking the noisy
> parts. Concretely:
>
> | raw fragment | normalized |
> |---|---|
> | `expected 42 but was 37` | `expected <NUM> but was <NUM>` |
> | `User 0x7f3a9c not found at 2026-06-26T14:03:11` | `User <HEX> not found at <TS>` |
> | `…/tmp/build-8821/Foo.java:317` | `…/tmp/build-<NUM>/Foo.java:<LINE>` |
> | `Connection refused: 10.2.3.4:5432` | `Connection refused: <IP>:<PORT>` |
>
> The **signature = test identity + the normalized text** (and we store a hash of it for fast exact
> lookup). Normalization is a small, ordered set of regex masks (numbers, hex/addresses,
> timestamps, IPs/ports, UUIDs, temp paths, line numbers) plus keeping the **exception type** and
> the **top N stack frames** of *our* packages. It is deliberately tunable: too aggressive and
> distinct bugs collide under one signature; too timid and the same bug never recurs. Because this
> single function decides what "the same failure" means for recurrence (below), prediction (§1),
> and flakiness grouping, it is treated as a **named, test-covered component**, not an
> afterthought — and the exact mask set is an open question (see Open questions).

> **Why confirmation matters (and not just "who said it").** It is *not* sufficient to let the
> system learn from the LLM's own unconfirmed conclusions: feeding back unvalidated guesses as if
> they were truth produces **self-confirmation bias** — the model reinforces its own mistakes and
> its confidence drifts from reality. The signal that actually teaches is **validation**: a
> human-**confirmed** conclusion (strong positive) and especially a human-**correction** (the AI
> was wrong — the most informative case). Whether the human or the AI *authored* the conclusion is
> irrelevant; whether it was *validated* is what counts. Hence retrieval and confidence below are
> weighted by provenance tier, and `AI_UNCONFIRMED` entries are treated as weak hints, not facts.

- **Recurrence recognition** — when a new failure matches a past signature, the record surfaces
  *"this looks like the failure on &lt;run/date&gt;; previous reason was &lt;…&gt;; caused by &lt;…&gt;."*
- **Similarity without a vector database.** Retrieval runs entirely on **stock PostgreSQL** — no
  embeddings, no extra service to operate. Two cheap layers, deliberately chosen for low
  build/maintenance cost and immediate user value:
  1. **Exact recurrence** — match on the **signature hash** (test identity + normalized text).
     Instant, index-backed, zero false positives. This alone delivers "we've seen this exact
     failure before" — the highest-value, lowest-effort win.
  2. **Fuzzy "similar past cases"** — the built-in **`pg_trgm`** extension (a single
     `CREATE EXTENSION pg_trgm`, ships with Postgres) gives trigram `similarity()` over the
     normalized error text with a GIN index; full-text search (`tsvector`) covers keyword overlap.
     `ORDER BY similarity(sig_text, :new) DESC LIMIT k` returns the top-k nearest historical
     failures. Good enough to catch "same kind of failure, slightly different wording," and trivial
     to maintain.
- **Better hypotheses over time** — the LLM summary (§1) is given those top-k similar past cases
  (retrieved as above) as context (retrieval-augmented), so its suggestions improve as the
  knowledge base grows — using only Postgres similarity, no vector store. If semantic recall ever
  proves insufficient, `pgvector` is a later drop-in **behind the same retrieval interface**; it is
  explicitly out of scope now.
- **Improving prediction** — accumulated **confirmed/corrected** reasons let the deterministic
  classifier and the LLM raise confidence for repeat patterns (e.g. "this test historically fails
  on `ut_ref` changes to table X"), nudging future runs toward the right cause and the right
  contact automatically. Unconfirmed AI guesses do not feed this loop as ground truth.
- **Auditability** — a searchable log of past failures, their causes, who caused them, **how the
  conclusion was reached (AI-confirmed vs human-corrected vs human-entered) and who validated it**,
  and how they were resolved.

## 5. Delivery surfaces

- **Web dashboard** — primary surface, opening on the **main working view (§0)**: the
  three-bucket triage queue (new-unacknowledged / still-failing / recently-fixed), then run
  summaries, per-test records (with the editable "causing person" / "reason" fields, the
  one-click **Confirm** on AI suggestions, and the **Acknowledge** action), flaky leaderboard,
  and knowledge-base search. The acting user is shown in the header (`test-user` in Phase 1).
- **Email report — sent only when the UT situation *worsened*.** Since every commit triggers a run,
  a per-run digest would be constant noise. The tool emails **only when a processed run introduces
  ≥1 new failing test** (a regression vs the baseline). Runs with no new failures send **nothing**
  — silence means "no worse than before." The email leads with the **new failures** (predicted
  cause + suggested contact each), and includes still-failing / newly-fixed counts as context. A
  recovery notice ("back to green / no new failures for N runs") is an optional, separately
  toggleable exception; everything else stays in the dashboard.

---

## Information model (what must be persisted to produce the above)

- **Runs** — build #, links, SVN revision(s), overall + per-shard start/finish, totals, baseline flag.
- **Test results per run** — identity, status, duration, shard, failure message, stack trace.
- **Test identity & aliases** — canonical fully-qualified name, optional `alias_of` pointer (so
  renames/moves keep their history), and whether an alias is suggested vs human-confirmed.
- **Test lifecycle** — current **lifecycle state** (`FAILING` / `FIXED` / `REMOVED`), the `FLAKY`
  flag, `reopen_count`, and the **acknowledgement** attribute (flag + acknowledger + timestamp) as
  a separate field from state.
- **Failure episodes** — one row per fail→fix cycle: first-failure run, fixed-in run (only when
  passed again, never on removal), cause/reason, and age — so regressions accumulate instead of
  overwriting.
- **Signals** — candidate code changes (from SVN update step), candidate data changes (from
  `ut_ref` tracking), infra indicators, ownership — each linked to the failure that generated it.
- **Classifications** — predicted cause, confidence, suggested contact, LLM hypothesis.
- **Users** — an `actor` identity on every human action (Phase 1: `test-user`; Phase 2: Keycloak
  principal) — a single field shared by acknowledgements, confirmations, and entered reasons.
- **Human input** — causing person, reason text, triage status, **acknowledger + acknowledged-at**,
  and for each conclusion its **provenance tier** (`AI_UNCONFIRMED` / `AI_CONFIRMED` /
  `HUMAN_CORRECTED` / `HUMAN_ENTERED`), the **original AI value** when corrected, and **who
  confirmed/corrected it + when**.
- **Failure history / flakiness** — every historical failure per test (for counts, last-failed,
  fail rate, windows).
- **Knowledge base** — failure signatures (normalized error text **+ its hash** for exact lookup,
  with a `pg_trgm` GIN index for fuzzy similarity) ↔ entered reasons/causes, for recurrence
  matching and retrieval — all in PostgreSQL, no vector store.

## Technical decisions (documented for reference — secondary at this phase)

- **Language:** Python.
- **Reference DB:** Oracle (`ut_ref` + tracking tables), read for data-change correlation.
- **Persistence:** the **existing PostgreSQL** database for run history, lifecycle, flakiness, and
  knowledge base — chosen over a local SQLite file because it already exists (no new infra), scales
  comfortably to full history (many tests × runs/day × years), supports concurrent access for
  multiple monitors in Phase 2, and provides the **`pg_trgm` / full-text** similarity used by the
  knowledge base (§4) natively — no vector database. (The Oracle `ut_ref` DB is separate and
  read-only; PostgreSQL is the app's own store.)
- **Trigger:** scheduled poll of Jenkins (detect a new completed run, then process it); an
  on-demand command remains useful for back-filling history.
- **Automation level:** **assistive** — the tool gathers, predicts, and presents; the human
  confirms cause and reason. Auto-notify / full automation are deliberately later.
- **Identity:** **Phase 1 (in-development testing)** — self-declared name stored in the browser
  (default `test-user`), no authentication, so the workflow is usable immediately and multiple real
  people can exercise attribution during testing. **Phase 2 (later, production)** — Keycloak
  (Kerberos SSOT) auth in front of the app, swapping the `actor` value with no data-model change.
- **Learning signal:** the knowledge base weights entries by **provenance tier**; only
  human-confirmed or human-corrected/entered conclusions feed prediction as ground truth, to avoid
  the LLM reinforcing its own unverified guesses.
- **Reasoning:** deterministic correlation for the facts/scoring; optional LLM (provider chosen
  later, behind a swappable interface) for the readable hypothesis and knowledge-base retrieval.

## Open questions to resolve before building

> **Blocking vs. non-blocking.** Most of these can be settled while building and don't change the
> output design. **#3 is the exception — it is a hard prerequisite:** nothing in the tool works
> until the merged UT report and the SVN-update step output can be parsed, and their formats may
> constrain the data model. It is the **first execution milestone**, not a parallel open question.

1. Exact `ut_ref` tracking-table schema: change-timestamp column, author column, and how a change
   maps to a table/entity a test depends on.
2. How to relate a failing test to relevant SVN paths / data tables — only needed for the **later
   relevance-ranking enhancement** (§1), *not* for v1, which presents window-filtered candidates
   chronologically and lets the human attribute. Refine later with path/name heuristics + the
   knowledge base.
3. **(Blocking — first milestone.)** Format/source of the merged UT execution report and the
   SVN-update step output to parse.
4. The flaky **transition** threshold (how many flips ÷ runs counts as FLAKY) within the 30-day
   window, and the trigram `similarity()` cutoff for "similar past cases" (§4).
5. The exact **normalization mask set** for failure signatures (§4) — which patterns to mask and
   how many stack frames to keep — since it defines what "the same failure" means everywhere.

*Resolved during planning:* baseline = most recent **complete** run; flaky = **oscillation**-based
(no "no-change" determination); identity = self-declared in Phase 1 (default `test-user`),
Keycloak in Phase 2; persistence = existing **PostgreSQL**; similarity = **`pg_trgm` / full-text**
(no vector DB); per-test record includes all suggested fields; flakiness window default = 30 days;
email sent **only on new failures**; lifecycle separates state (`FAILING`/`FIXED`/`REMOVED`) from
acknowledgement, with failure episodes for regressions.
