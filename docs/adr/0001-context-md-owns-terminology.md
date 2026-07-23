# CONTEXT.md owns terminology; OVERVIEW.html owns architecture

The repo already had three hand-maintained doc surfaces guarded against rot by the
`docs-overview-maintainer` agent (OVERVIEW.html, the in-app Help page, the README config
reference + `.env.example`); adding a ubiquitous-language catalogue risked a fourth that drifts
silently. We decided that the root `CONTEXT.md` is the **single authority for domain terminology**
(a glossary and nothing else, maintained live during domain-modeling sessions), that
`docs/OVERVIEW.html` remains the authority for architecture and workflows, and that the
`docs-overview-maintainer` agent guards `CONTEXT.md` as a fourth surface so term renames get the
same sync check as every other doc. The alternatives — keeping OVERVIEW.html's Reference section
as the sole vocabulary source, or leaving `CONTEXT.md` session-maintained with no owner — were
rejected because the first defeats the point of a dedicated catalogue and the second guarantees
drift.
