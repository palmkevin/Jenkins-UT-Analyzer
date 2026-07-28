# Jenkins UT Analyzer

Triage support for the LIMS unit-test builds from the Permanent Pipeline: the tool ingests every build's test results
from Jenkins, correlates new failures with code and data changes, and drives a human triage
workflow enriched by a learning knowledge base. This file is the **ubiquitous-language catalogue**
— the single authority for what domain terms mean. (Architecture and workflows live in
[docs/OVERVIEW.html](docs/OVERVIEW.html); this file is a glossary and nothing else.)

## Language

### The Permanent Pipeline

**Permanent Pipeline**:
The continuously-running Jenkins job we analyze (`…build-release-permanent`); it runs one Build
**per commit**, not on a schedule. "Permanent" is its identity and cadence.
_Avoid_: Nightly pipeline (that names a separate pipeline not yet monitored by this app)

**Build**:
One execution of the Permanent Pipeline, identified by its Jenkins build number; the unit of
ingest and analysis. In prose, "Jenkins run" and "pipeline run" are accepted synonyms (Jenkins's
own API calls builds *runs* — e.g. `wfapi/runs` — translated to Build at the ingest boundary);
identifiers, schema, routes, and UI labels always say Build.
_Avoid_: Run (standalone — ambiguous with a single test's execution), job

### Tests & results

**Test**:
The durable identity of a single unit test (`suite/class/method`). Has exactly one lifecycle,
across all tracks.
_Avoid_: Test case (for the identity)

**Test Result**:
The raw outcome of one test in one build and track, exactly as Jenkins reported it.
_Avoid_: TestCaseResult, outcome

**Track**:
A parallel lane in which the Permanent Pipeline executes the test suite, each lane distinguished by
its execution environment — e.g. interpreter version or operating system (currently `permanent` and
`permanent_py39`; the `permanent` prefix just echoes the pipeline name — the distinguishing
attribute is the environment). An attribute of a Test Result — the same test can run, and fail
independently, in several tracks; a Test's identity and lifecycle span all tracks.
_Avoid_: Shard, lane, stage

### Failure lifecycle

**Failure Episode**:
One fail→fix cycle of a test — from the build where it started failing to the build where it came
back to passing. Numbered per test. Closes **only** when the test runs and passes again; if the
test is removed while failing, its episode stays open (disappeared ≠ fixed) — see Open episode /
closed episode below.
_Avoid_: Streak, incident

**Open episode / closed episode**:
An episode's binary state (`FailureEpisode.is_open`). **Open** means the test is currently failing
— or has been removed while failing, since removal never closes an episode. **Closed** means the
test passed again (`fixed_at` is set); "closed" names the *state*, "fixed" names *how* it closed.
This pairing is the canonical vocabulary for a test's failure status outside its own record (e.g.
the test-search results column: "open episode" / "removed" / "closed" / "no failures on record").
_Avoid_: Fixed (as the state label — reserve "fixed" for describing how an episode closed, not for
the closed state itself)

**Lifecycle State**:
Whether a test is currently failing, fixed, or removed. About the result only — independent of
acknowledgement and triage.

**Acknowledgement**:
A human's "I have seen this" mark on a test's current state, recorded with actor and time.
Independent of both lifecycle state and triage status.
_Avoid_: Triaged (that is Triage Status)

**Flakiness**:
How much a test oscillates between pass and fail across builds (state transitions ÷ builds over a
window) — not a fail-rate. A solidly failing test is a regression, not flaky.
_Avoid_: Fail rate, instability

### Build-level incidents

**Build Incident**:
A build-level condition requiring human triage — the pipeline itself failing or being aborted —
as opposed to a single test failing (that is a Failure Episode). Opens on a build whose own
Jenkins result is `FAILURE` or `ABORTED`; a run of consecutive non-green builds collapses into
**one** incident, which closes on the next `SUCCESS` or `UNSTABLE` build. Orthogonal to the test
lifecycle: the same build can carry both a Build Incident and one or more Failure Episodes, and
the two never merge.
_Avoid_: Pipeline failure, Build failure, Incident (standalone — always say "Build Incident";
plain "incident" is also the word to avoid when talking about a Failure Episode, see above)

**Incident Kind**:
What opened a Build Incident: `pipeline_failure` (the build itself failed — gets the full
predicted-cause/hypothesis treatment, same as a Failure Episode) or `aborted` (the build was
aborted — human-documented only, no prediction). `slow` is reserved for a future duration-regression
detector (a *completed* build slower than its Expected Duration). A build that is still running too
long is **not** a Build Incident — it is surfaced live as an Overrunning Build (see Build duration).

### Build duration

**Expected Duration**:
The reference wall-clock a Build is expected to take: the **median** end-to-end duration of the last
20 `SUCCESS`/`UNSTABLE` builds. Undefined until 20 such builds exist. The yardstick for both
overrunning (in-progress) and slow (completed) detection.
_Avoid_: Average duration, estimated duration

**Overrunning Build**:
An **in-progress** Build whose elapsed time has exceeded its Expected Duration by a configured
multiple. Surfaced live as a banner on the triage dashboard so a human can stop it — it is **not** a
Build Incident and is never persisted as one; if the build is then aborted, the ordinary `aborted`
Build Incident records it.
_Avoid_: Hung, never-ending, stuck, long-running build

### Triage & causes

**Triage Status**:
How far the human investigation of an episode or a Build Incident has progressed: untriaged →
investigating → root-caused → resolved.

**Classification**:
The deterministic, rule-based predicted cause of an episode or a Build Incident: code change, data
change, infrastructure, or unknown.
_Avoid_: Hypothesis, prediction

**Hypothesis**:
The LLM's suggested root-cause narrative for an episode or a Build Incident, awaiting human
confirmation or correction.
_Avoid_: Classification, AI analysis

**Change Candidate**:
A code change (SVN commit) or data change (`ut_ref` tracking row) that falls in an episode's or a
Build Incident's correlation window and may explain it.
_Avoid_: Culprit, suspect

**Attribution**:
The human conclusion recorded on an episode or a Build Incident — who caused it and why.
_Avoid_: Blame

**Assignee**:
The person handling the fix for an open Failure Episode or Build Incident — distinct from the
causing person recorded in its Attribution (who caused it vs. who is fixing it).
_Avoid_: Owner (that already names the test's main developer, resolved from `svn blame` — a
different concept)

**Cause Ticket**:
The ticket describing the cause of a Failure Episode or Build Incident.
_Avoid_: Jira ticket (ambiguous now that a Resolution Ticket also exists)

**Resolution Ticket**:
The ticket the Assignee is working on to resolve a Failure Episode or Build Incident — **not** a
claim that it is already resolved.
_Avoid_: Fix ticket, resolved ticket

### Learning

**Provenance**:
How a recorded cause or reason was reached — AI-suggested (unconfirmed or confirmed) or
human-authored (corrected or entered). Weights knowledge-base retrieval.

**Failure Detail**:
The **raw** error text of a Test Result exactly as Jenkins reported it — the failure message
(`error_details`) plus its stack trace (`error_stack_trace`). What the triage queue's
free-text "failure detail" filter searches (substring, case-insensitive). Distinct from the
Failure Signature: this is the unprocessed text, the signature is its normalized fingerprint.
_Avoid_: Error text, failure message (when you mean the whole message+trace surface)

**Failure Signature**:
The normalized fingerprint of a failure's error text, used to recognize recurrences of the same
failure — on the same test for a Failure Episode, or of the same failing pipeline stage for a
Build Incident. The two live side by side but never cross-match.

**Knowledge Base**:
The accumulated record of confirmed causes, retrieved by failure signature to inform the triage of
new failures.

### Alerting

**Alert**:
A single message the tool pushes to humans when a noteworthy build condition occurs — composed once,
channel-neutrally, then delivered to every enabled Alert Channel. Distinct from a Build Incident or
Failure Episode (those are the persisted *conditions*; an Alert is the outbound *notification* about
one).
_Avoid_: Notification (as the canonical noun — accepted in prose, but the code, config, and this
glossary say Alert)

**Alert Kind**:
Which condition an Alert announces — one of `incident` (a `pipeline_failure` Build Incident opened),
`regression` (a build introduced ≥1 new failing test), `recovery` (the suite went back to green),
`overrun` (an in-progress build exceeded its Expected Duration), or `ops` (a poller-health/quarantine
condition). The unit an Alert Channel subscribes to.
_Avoid_: Alert type, event type

**Alert Channel**:
A destination an Alert is delivered to — currently **Email** (SMTP) or **Teams** (a Microsoft Teams
incoming webhook). Each channel is enabled independently by its own configuration and subscribes to
its own set of Alert Kinds, so the same Alert can reach one channel, both, or neither. Delivery is
best-effort and independent per channel: one channel failing never blocks another or the ingest.
_Avoid_: Transport, notifier, sink
