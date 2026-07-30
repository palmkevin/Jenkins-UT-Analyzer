#!/usr/bin/env python3
"""One-shot: recreate the exported GitHub issues in a Bitbucket Cloud issue tracker.

Read `docs/history/github-issues.md` for the frozen record of *all* GitHub issues. This script
exists to move the **still-actionable** ones (open, by default) into Bitbucket so there is a live
tracker again. Kept in-tree as the record of how the move was done; it is idempotent-ish (see
`--dry-run` / the duplicate-title check) but is not meant to be part of any routine flow.

Bitbucket's tracker is poorer than GitHub's, so the mapping is lossy in ways worth knowing:
  * **Numbering cannot be preserved.** Bitbucket issue IDs start at 1 and are separate from PR
    IDs, whereas GitHub shares one sequence across issues and PRs (this repo's #193 is a PR,
    #194 an issue). Every bare `#N` in this repo's commit history therefore refers to the
    GitHub numbering — i.e. to `docs/history/github-issues.md`, not to Bitbucket. Each created
    issue records its GitHub number in a footer so the two can be reconciled by hand.
  * **No free-form labels.** `type:*` maps onto Bitbucket's fixed `kind` field; `area:*` has no
    equivalent (components must be pre-created in repo settings and are read-only over the API),
    so both are also written verbatim into the body.
  * **Authors and timestamps cannot be forged** — everything is created as the calling user, now.
    The original author/dates go into the footer.

Auth — Bitbucket Cloud, either form (Atlassian retired app passwords, so prefer a token):
    export BITBUCKET_EMAIL='you@example.com'      # Atlassian account email
    export BITBUCKET_TOKEN='<api-token>'          # → HTTP Basic
  or, for a repository/workspace access token:
    export BITBUCKET_TOKEN='<access-token>'       # → Bearer (no email set)

Usage:
    python scripts/migrate_issues_to_bitbucket.py <workspace> <repo-slug> [options]

Options:
    --export PATH        Directory holding `issues.json` (default: docs/history)
    --include-closed     Also recreate closed issues, as `resolved`
    --dry-run            Print what would be created; make no API calls that write
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

API_ROOT = "https://api.bitbucket.org/2.0"

# GitHub `type:*` label -> Bitbucket `kind` (one of bug / enhancement / proposal / task).
KIND_BY_TYPE_LABEL = {
    "type:fix": "bug",
    "type:feat": "enhancement",
    "type:perf": "enhancement",
    "type:chore": "task",
    "type:test": "task",
    "documentation": "task",
}
DEFAULT_KIND = "task"

# Bitbucket issue states: new / open / resolved / on hold / invalid / duplicate / wontfix / closed.
STATE_OPEN = "new"
STATE_CLOSED = "resolved"


class BitbucketError(RuntimeError):
    pass


def auth_header() -> str:
    token = os.environ.get("BITBUCKET_TOKEN")
    if not token:
        raise BitbucketError("BITBUCKET_TOKEN is not set — see this script's docstring.")
    email = os.environ.get("BITBUCKET_EMAIL")
    if email:
        raw = f"{email}:{token}".encode()
        return "Basic " + base64.b64encode(raw).decode()
    return f"Bearer {token}"


def request(method: str, path: str, payload: dict | None = None) -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"{API_ROOT}{path}", data=body, method=method)
    req.add_header("Authorization", auth_header())
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            text = resp.read().decode()
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        raise BitbucketError(f"{method} {path} -> HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise BitbucketError(f"{method} {path} -> {exc.reason}") from exc


def kind_for(labels: list[str]) -> str:
    for label in labels:
        if label in KIND_BY_TYPE_LABEL:
            return KIND_BY_TYPE_LABEL[label]
    return DEFAULT_KIND


def build_body(issue: dict, labels: list[str]) -> str:
    """The original body plus a provenance footer covering everything Bitbucket can't hold."""
    original = (issue.get("body") or "_(no description)_").strip()
    author = (issue.get("author") or {}).get("login", "unknown")
    areas = [label for label in labels if label.startswith("area:")] or ["—"]
    return "\n".join(
        [
            original,
            "",
            "---",
            "",
            "*Migrated from GitHub Issues.*",
            "",
            f"- **Original:** GitHub #{issue['number']} — {issue['url']}",
            f"- **Original author:** {author} · **opened** {issue['createdAt'][:10]}"
            + (f" · **closed** {issue['closedAt'][:10]}" if issue.get("closedAt") else ""),
            f"- **Labels:** {', '.join(labels) or '—'} (area: {', '.join(areas)})",
            "- **Note:** bare `#N` references in this repo's commit history use the *GitHub*"
            " numbering — see `docs/history/github-issues.md`, not Bitbucket issue IDs.",
        ]
    )


def existing_titles(workspace: str, repo: str) -> set[str]:
    """Titles already in the tracker, so a re-run doesn't duplicate them."""
    titles: set[str] = set()
    path: str | None = f"/repositories/{workspace}/{repo}/issues?pagelen=50"
    while path:
        page = request("GET", path)
        titles.update(item["title"] for item in page.get("values", []))
        next_url = page.get("next")
        path = next_url[len(API_ROOT) :] if next_url else None
    return titles


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("workspace", help="Bitbucket workspace ID (the slug in the repo URL)")
    parser.add_argument("repo", help="Bitbucket repository slug")
    parser.add_argument("--export", default="docs/history", help="directory holding issues.json")
    parser.add_argument("--include-closed", action="store_true", help="also recreate closed issues")
    parser.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    args = parser.parse_args()

    export = pathlib.Path(args.export) / "issues.json"
    if not export.is_file():
        print(f"error: {export} not found — re-run the gh export first.", file=sys.stderr)
        return 1

    issues = json.loads(export.read_text())
    issues.sort(key=lambda i: i["number"])
    selected = [i for i in issues if args.include_closed or i["state"] == "OPEN"]
    if not selected:
        print("Nothing to migrate.")
        return 0

    print(
        f"{len(selected)} issue(s) selected of {len(issues)} exported "
        f"({'open + closed' if args.include_closed else 'open only'}) "
        f"-> bitbucket.org/{args.workspace}/{args.repo}"
    )

    if args.dry_run:
        for issue in selected:
            labels = sorted(label["name"] for label in issue["labels"])
            state = STATE_OPEN if issue["state"] == "OPEN" else STATE_CLOSED
            plan = f"[{kind_for(labels):11s} / {state:8s}]"
            print(f"  would create {plan} #{issue['number']} {issue['title']}")
        return 0

    # The tracker is off by default on a fresh Bitbucket repo; POSTing an issue would 404.
    print("Enabling the issue tracker ...")
    request("PUT", f"/repositories/{args.workspace}/{args.repo}", {"has_issues": True})

    already = existing_titles(args.workspace, args.repo)
    if already:
        print(f"  {len(already)} issue(s) already present — matching titles will be skipped.")

    created = skipped = 0
    for issue in selected:
        if issue["title"] in already:
            print(f"  skip (already present): #{issue['number']} {issue['title']}")
            skipped += 1
            continue
        labels = sorted(label["name"] for label in issue["labels"])
        payload = {
            "title": issue["title"],
            "content": {"raw": build_body(issue, labels)},
            "kind": kind_for(labels),
            "priority": "major",
            "state": STATE_OPEN if issue["state"] == "OPEN" else STATE_CLOSED,
        }
        result = request("POST", f"/repositories/{args.workspace}/{args.repo}/issues", payload)
        origin = f"GitHub #{issue['number']}"
        print(f"  created Bitbucket #{result.get('id')} <- {origin}: {issue['title']}")
        created += 1

    print(f"Done: {created} created, {skipped} skipped.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BitbucketError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
