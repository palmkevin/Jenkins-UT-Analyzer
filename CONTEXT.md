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
ingest and analysis.
_Avoid_: Run, job

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
back to passing (or was removed). Numbered per test.
_Avoid_: Streak, incident

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

### Triage & causes

**Triage Status**:
How far the human investigation of an episode has progressed: untriaged → investigating →
root-caused → resolved.

**Classification**:
The deterministic, rule-based predicted cause of an episode: code change, data change,
infrastructure, or unknown.
_Avoid_: Hypothesis, prediction

**Hypothesis**:
The LLM's suggested root-cause narrative for an episode, awaiting human confirmation or
correction.
_Avoid_: Classification, AI analysis

**Change Candidate**:
A code change (SVN commit) or data change (`ut_ref` tracking row) that falls in an episode's
lookback window and may explain it.
_Avoid_: Culprit, suspect

**Attribution**:
The human conclusion recorded on an episode — who caused it and why.
_Avoid_: Blame

### Learning

**Provenance**:
How a recorded cause or reason was reached — AI-suggested (unconfirmed or confirmed) or
human-authored (corrected or entered). Weights knowledge-base retrieval.

**Failure Signature**:
The normalized fingerprint of a failure's error text, used to recognize recurrences of the same
failure on the same test.

**Knowledge Base**:
The accumulated record of confirmed causes, retrieved by failure signature to inform the triage of
new failures.
