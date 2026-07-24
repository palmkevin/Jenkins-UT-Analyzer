# The analyzed pipeline is the Permanent Pipeline (per commit), not a nightly build

We had described the analyzed Jenkins job (`…build-release-permanent`) as the "nightly build"
throughout the code and docs. That was factually wrong: the job runs **permanently — one build per
commit** (hence its name), which is precisely *why* the poller polls Jenkins continuously (a nightly
job would make frequent polling pointless). We corrected the language, scrubbing "nightly" as a
descriptor of this pipeline.

We also introduced **Permanent Pipeline** as a first-class term in CONTEXT.md, rather than just
fixing the **Build** definition inline. Monitoring the org's *actual* nightly pipeline is a plausible
future addition (out of scope now), so "Build" can no longer mean "one execution of *the* pipeline" —
there may be more than one pipeline, and builds will need to be keyed by which one they came from.
Giving the pipeline concept an explicit home now makes that a purely additive change later, and it
gives "permanent" — a load-bearing concept smeared across the Build and Track definitions — a single
place to live. The Track entry now points at it, defusing the collision with the `permanent` /
`permanent_py39` track names (that `permanent` prefix merely echoes the pipeline; a track's
distinguishing attribute is its execution environment).

Consequently, **"nightly" is reserved, not banned**: it correctly names a separate pipeline **not yet
monitored by this app**. CONTEXT.md's `_Avoid_` note on Permanent Pipeline records the reservation so
the same mistake cannot recur.

The rejected alternative was fixing **Build**'s definition in place with no new term — cheaper today,
but it leaves "permanent" homeless and forces a re-modelling the moment a second pipeline arrives.
