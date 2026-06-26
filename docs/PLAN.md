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
> focus, and there is **no implementation/execution plan** here yet.

## How the pipeline works (inputs the tool relies on)

- **SVN update step:** early in the pipeline the job runs an SVN update; **this step's output is
  the authoritative list of code changes** (revisions, authors, changed paths) pulled into the
  run. The tool reads this rather than querying SVN separately for "what changed this run."
- **Timing matters:** for **data** changes there is *no* changelog — only **timestamp comparison**
  against `ut_ref` tracking tables. So the tool must capture, precisely, **when each run (and each
  parallel shard) started and finished**, to define the time window in which a data change could
  have affected the run.
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

- **Phase 1 — implicit user (no real authentication).** It is sufficient to identify the actor as
  a single **`test-user`** (display name configurable). No login screen, no passwords, no SSO. All
  actions are stamped with this identity and a timestamp. This unblocks the entire workflow — the
  monitor can acknowledge, confirm, and annotate from day one — and every record is already
  shaped to carry a real user id later.
- **Phase 2 — Keycloak / Kerberos SSO (later).** Real authentication via the existing Keycloak
  (Kerberos SSOT). Because Phase 1 already stamps an identity on every action, this phase only
  swaps *how* the identity is obtained (an auth layer in front of the app + a real user id on the
  session) — **no data-model change**: the `actor` field that held `test-user` now holds the
  authenticated principal. Login, per-user views ("my acknowledgements"), and access control
  become possible but are **not required earlier**.

> **Design rule:** the persisted identity is a plain `actor` string from the start. Phase 1 writes
> `test-user`; Phase 2 writes the Keycloak principal. Nothing downstream needs to know which phase
> produced it.

---

# THE EXPECTED OUTPUT

This is the heart of the plan. The tool produces several output surfaces, all backed by a
persistent history so state and trends survive across runs.

## 0. Main working view — the daily triage queue (primary landing surface)

This is the **first screen the monitor opens** and the view they live in day to day. It is not a
per-run report (that is §2) — it is the **current, cross-run state of everything that needs
attention**, organized into the three buckets the monitor actually thinks in:

1. **★ New failing tests — not yet acknowledged.** Tests in state `NEW`: they started failing and
   **no user has acknowledged them yet**. This is the action queue — the work that has just
   arrived. Each row shows the test identity, when/which run it first failed, the predicted cause
   + confidence, and an **Acknowledge** action (stamps the acting user from §1, moving the test
   from `NEW` to `FAILING`). Sorted newest-first; this bucket should ideally be driven to empty.
2. **★ Tests still failing.** Tests in state `FAILING`: acknowledged and not yet green again —
   the open caseload being worked. Shows age of failure (runs + days), triage status, the
   assigned/causing person, and a one-line cause. This is "what is still broken and being chased."
3. **★ Tests recently fixed.** Tests that flipped to `FIXED` within a recent window (default the
   **last N runs / last 7 days**, configurable) — so a fix is **visible and confirmable** before
   it scrolls out of view. Shows the fixing run + date and the recorded reason. Lets the monitor
   confirm the fix held and close the loop, and gives stakeholders a "what got resolved lately"
   glance.

Each bucket links straight into the per-test record (§1) for full evidence and editing. The
buckets are mutually exclusive and derive directly from the test lifecycle state machine
(`NEW` → `FAILING` → `FIXED`), so no separate bookkeeping is needed — the view is just a
projection of state. Counts per bucket double as the at-a-glance health indicator.

> The distinction between bucket 1 and bucket 2 is **acknowledgement**, which is why a user
> identity (§ Users & identity) is required even in Phase 1: "not yet acknowledged" is defined
> relative to a recorded actor.

## 1. Per-test record (the centerpiece)

For **every test that is or has been failing**, the tool maintains a rich record. Fields the user
explicitly requested are marked ★; the rest are suggestions to consider.

### Identity & lifecycle
- **Test identity** — suite / class / method, and which parallel shard it ran in.
- ★ **Current state** — managed by the app as a small state machine:
  `NEW` → `FAILING` → `FIXED` (and `FLAKY` as a cross-cutting flag; see §3).
- ★ **First failure** — link to the Jenkins run that *first* triggered this failure **+ date/time**.
- ★ **Last failing run** — link to the **UT execution report** of the most recent run where it
  failed **+ date/time**.
- ★ **Fixed-in run** — link to the Jenkins run that fixed it **+ date/time** (set when the test
  goes green again).
- **Age of failure** — how long it has been broken: number of runs and elapsed days
  from first failure to fix (or to now if still failing). Makes "long-standing vs brand-new"
  obvious at a glance.
- **Error type** — assertion/value mismatch vs error/exception vs timeout/infra,
  derived from the result + stack trace.

### Attribution (gathered by the tool, confirmed by the human)
- **Predicted cause + confidence** — deterministic classification:
  `CODE_CHANGE` / `DATA_CHANGE` / `INFRASTRUCTURE` / `UNKNOWN`, with a confidence score and the
  evidence behind it.
- **Candidate code changes** — revisions from the **SVN update step** in the run
  window, with committer(s) and changed paths, ranked by relevance to the test.
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
checks first. **Baseline = the immediately previous run** (matches the monitor's current habit).

## 3. Flakiness / failure-history tracking

Some tests flicker — they fail more often than others. Because the tool keeps full history, for
**any test it can show** (requested):
- ★ **Has it failed before?** and **when did it last fail.**
- ★ **How often has it failed total**, and **how often in the last X days**
  (**default X = 30 days**, configurable).
- **Fail rate / flakiness score** — failures ÷ runs over a window; a test that
  fails then passes without any code/data change is flagged **FLAKY**.
- **Pattern** — e.g. consecutive-run failures vs intermittent, and whether it tends
  to fail on a specific shard.
- A dedicated **"flaky leaderboard"** view ranking the most unstable tests, so chronic offenders
  get attention separately from genuine regressions.

## 4. Knowledge base & learning loop

Every **reason for failure** and **causing person** — whether AI-suggested-then-confirmed or
human-entered — is stored against a **failure signature** (test identity + normalized error
message/stack trace), **together with its provenance tier** (§1). This turns one-off human
knowledge into a growing, queryable asset:

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
- **Better hypotheses over time** — the LLM summary (§1) is given the most similar past cases as
  context (retrieval-augmented), so its suggestions improve as the knowledge base grows.
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
- **Email report** — a per-run digest (new/fixed/still-failing, predicted causes, suggested
  contacts) for the monitor and stakeholders.

---

## Information model (what must be persisted to produce the above)

- **Runs** — build #, links, SVN revision(s), overall + per-shard start/finish, totals, baseline flag.
- **Test results per run** — identity, status, duration, shard, failure message, stack trace.
- **Test lifecycle** — current state, first-failure run, last-failure run, fixed-in run, age.
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
- **Knowledge base** — failure signatures ↔ entered reasons/causes, for recurrence matching.

## Technical decisions (documented for reference — secondary at this phase)

- **Language:** Python.
- **Reference DB:** Oracle (`ut_ref` + tracking tables), read for data-change correlation.
- **Persistence:** SQLite (local file) for run history, lifecycle, flakiness, knowledge base.
- **Trigger:** scheduled poll of Jenkins (detect a new completed run, then process it); an
  on-demand command remains useful for back-filling history.
- **Automation level:** **assistive** — the tool gathers, predicts, and presents; the human
  confirms cause and reason. Auto-notify / full automation are deliberately later.
- **Identity:** **Phase 1** — implicit single `test-user`, no authentication, so the workflow is
  usable immediately. **Phase 2 (later)** — Keycloak (Kerberos SSOT) auth in front of the app,
  swapping the `actor` value with no data-model change.
- **Learning signal:** the knowledge base weights entries by **provenance tier**; only
  human-confirmed or human-corrected/entered conclusions feed prediction as ground truth, to avoid
  the LLM reinforcing its own unverified guesses.
- **Reasoning:** deterministic correlation for the facts/scoring; optional LLM (provider chosen
  later, behind a swappable interface) for the readable hypothesis and knowledge-base retrieval.

## Open questions to resolve before building (non-blocking for this output plan)

1. Exact `ut_ref` tracking-table schema: change-timestamp column, author column, and how a change
   maps to a table/entity a test depends on.
2. How to relate a failing test to relevant SVN paths / data tables for ranking candidates
   (start with the run time-window; refine with path/name heuristics + the knowledge base).
3. Format/source of the merged UT execution report and the SVN-update step output to parse.
4. The flaky threshold (fail-rate cutoff) within the confirmed 30-day window.

*Resolved during planning:* baseline = previous run; per-test record includes all suggested
fields; flakiness window default = 30 days.
