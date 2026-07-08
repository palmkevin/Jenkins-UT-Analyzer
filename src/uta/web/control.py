"""Read-side projection for the control panel (issue #16).

Assembles plain detached dicts (the Slice-0 pattern — templates never touch a live session) for the
three panels: the tunable thresholds with their current-vs-default state, the poller heartbeat +
high-water mark, and the recent ingest jobs.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from uta.config import Settings
from uta.control.ai_accuracy import ai_accuracy
from uta.control.heartbeat import read_heartbeat
from uta.control.jobs import recent_jobs
from uta.control.quarantine import list_quarantine
from uta.control.tunables import TUNABLES, effective_settings, load_overrides
from uta.models import Run


def _tunable_rows(base: Settings, overrides: dict[str, str]) -> list[dict]:
    """One display row per tunable: default (env), current (effective) and override state."""
    effective = effective_settings(base, overrides)
    rows = []
    for t in TUNABLES:
        default = getattr(base, t.key)
        current = getattr(effective, t.key)
        rows.append(
            {
                "key": t.key,
                "label": t.label,
                "group": t.group,
                "kind": t.kind,
                "min": t.minimum,
                "max": t.maximum,
                "step": "any" if t.kind == "float" else "1",
                "help": t.help,
                "default": default,
                "current": current,
                "overridden": t.key in overrides,
            }
        )
    return rows


def _grouped(rows: list[dict]) -> list[dict]:
    """Preserve the registry order while clustering rows under their group heading."""
    groups: list[dict] = []
    index: dict[str, dict] = {}
    for row in rows:
        group = index.get(row["group"])
        if group is None:
            group = {"name": row["group"], "rows": []}
            index[row["group"]] = group
            groups.append(group)
        group["rows"].append(row)
    return groups


def _job_dict(job) -> dict:
    return {
        "id": job.id,
        "build_start": job.build_start,
        "build_end": job.build_end,
        "range": (
            str(job.build_start)
            if job.build_start == job.build_end
            else f"{job.build_start}–{job.build_end}"
        ),
        "status": job.status,
        "builds_total": job.builds_total,
        "builds_done": job.builds_done,
        "error": job.error,
        "requested_by": job.requested_by,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


def _quarantine_dict(row) -> dict:
    return {
        "build_number": row.build_number,
        "attempts": row.attempts,
        "last_error": row.last_error,
        "first_failed_at": row.first_failed_at,
        "quarantined_at": row.quarantined_at,
        "quarantined": row.quarantined_at is not None,
    }


def jobs_panel(session: Session) -> dict:
    """Just the ingest-jobs slice — the HTMX poll fragment re-renders only this (issue #78).

    ``jobs_active`` gates the poll: the fragment carries an ``hx-trigger`` only while a job is
    QUEUED/RUNNING, so once every job is terminal the swapped-in fragment stops the loop.
    """
    jobs = [_job_dict(j) for j in recent_jobs(session)]
    return {
        "jobs": jobs,
        "jobs_active": any(j["status"] in ("QUEUED", "RUNNING") for j in jobs),
    }


def control_panel(session: Session, base_settings: Settings) -> dict:
    """The full control-panel context: tunables, poller health, quarantine, jobs, AI accuracy."""
    overrides = load_overrides(session)
    hb = read_heartbeat(session)
    high_water_mark = session.scalar(select(func.max(Run.build_number)))
    return {
        "groups": _grouped(_tunable_rows(base_settings, overrides)),
        "override_count": len(overrides),
        "poller": {
            "last_poll_at": hb.last_poll_at if hb else None,
            "last_success_at": hb.last_success_at if hb else None,
            "last_processed_count": hb.last_processed_count if hb else None,
            "last_processed": hb.last_processed if hb else None,
            "last_error": hb.last_error if hb else None,
            "last_error_at": hb.last_error_at if hb else None,
            "high_water_mark": high_water_mark,
            "poll_interval_seconds": base_settings.poll_interval_seconds,
            "has_run": hb is not None and hb.last_poll_at is not None,
        },
        "quarantine": [_quarantine_dict(q) for q in list_quarantine(session)],
        "quarantine_after_attempts": base_settings.quarantine_after_attempts,
        **jobs_panel(session),
        "ai_accuracy": ai_accuracy(session),
    }
