<!--
  The PR description template. Bitbucket Cloud has no in-repo template file (there is no equivalent
  of GitHub's `.github/pull_request_template.md`), so this file is the *source* for
  Repository settings → Pull requests → "Default description": edit here, then re-paste there.

  Keep it short. The issue holds the detail; this is the change + how it was checked.
  `Closes #N` does NOT auto-close on Bitbucket — resolve the issue yourself after merging.
-->

Closes #

## What changed


## How verified
- [ ] Offline gate green (`pytest -m "not live"`, run in batches — the whole suite at once OOM-kills)
- [ ] `ruff check .` **and** `ruff format --check .` both clean
- [ ] `docs-overview-maintainer` considered (invoke it if the app's parts / communications / workflows changed, or if a status/badge/dashboard page/LLM-feedback behavior an end user sees changed — it owns both OVERVIEW.html and the in-app Help page)
