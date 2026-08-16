<!--
  The PR description template. Bitbucket Cloud has no in-repo template file (there is no equivalent
  of GitHub's `.github/pull_request_template.md`), so this file is the *source* for
  Repository settings → Pull requests → "Default description": edit here, then re-paste there.

  Keep it short: the change + how it was checked. There is no issue tracker, so the PR body is the
  detail — cite the `docs/OPEN-WORK.md` slug it finishes, and delete that entry in this same PR.
-->

Closes: `<open-work-slug>` (entry deleted in this PR) — or "n/a" for unplanned work

## What changed


## How verified
- [ ] Offline gate green (`pytest -m "not live"`, run in batches — the whole suite at once OOM-kills)
- [ ] `ruff check .` **and** `ruff format --check .` both clean
- [ ] `docs-overview-maintainer` considered (invoke it if the app's parts / communications / workflows changed, or if a status/badge/dashboard page/LLM-feedback behavior an end user sees changed — it owns both OVERVIEW.html and the in-app Help page)
