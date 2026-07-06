"""Pure SVG-geometry builders for the trend charts (issue #53).

No HTTP/template concerns here — these take plain series data (as already assembled by
:mod:`uta.web.views`) and return the numeric geometry (polyline point strings, bar rects, scale)
that the Jinja templates render as inline ``<svg>`` markup. Keeping the arithmetic here rather than
in Jinja keeps templates declarative and this module unit-testable without a running app, in the
same "views build plain dicts, templates just render them" spirit as :mod:`uta.web.views`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Timeline:
    """Geometry for the run-health timeline: two polylines (failed, regressions) over N runs."""

    width: int
    height: int
    failed_points: str  # SVG polyline "points" attribute value
    regressions_points: str
    max_value: int
    first_build: int
    last_build: int
    runs: int


def run_health_timeline(
    rows: list[dict], *, width: int = 640, height: int = 140, pad_x: int = 8, pad_y: int = 12
) -> Timeline | None:
    """Build timeline geometry from oldest-first ``{"build", "failed", "regressions"}`` rows."""
    if not rows:
        return None
    n = len(rows)
    max_value = max(max(r["failed"], r["regressions"]) for r in rows)
    max_value = max(max_value, 1)  # avoid a divide-by-zero when every run is clean

    def _x(i: int) -> float:
        return pad_x + (i * (width - 2 * pad_x) / (n - 1) if n > 1 else 0.0)

    def _y(value: int) -> float:
        return height - pad_y - (value / max_value) * (height - 2 * pad_y)

    def _points(key: str) -> str:
        return " ".join(f"{_x(i):.1f},{_y(r[key]):.1f}" for i, r in enumerate(rows))

    return Timeline(
        width=width,
        height=height,
        failed_points=_points("failed"),
        regressions_points=_points("regressions"),
        max_value=max_value,
        first_build=rows[0]["build"],
        last_build=rows[-1]["build"],
        runs=n,
    )


@dataclass(frozen=True)
class Sparkline:
    """Geometry for a per-test pass/fail sparkline: one bar per run, oldest-first."""

    width: int
    height: int
    bars: list[dict]  # [{"x": float, "width": float, "failed": bool, "build": int}, ...]


def sparkline(
    points: list[dict],
    *,
    width: int = 120,
    height: int = 22,
    gap: float = 2.0,
    max_points: int = 20,
) -> Sparkline | None:
    """Build sparkline geometry from oldest-first ``{"build", "failed"}`` points.

    Only the most recent ``max_points`` are rendered (oldest-first order preserved) so a long
    flakiness window still renders a legible, compactly-spaced chart rather than hairline bars.
    """
    if not points:
        return None
    recent = points[-max_points:]
    n = len(recent)
    bar_width = (width - gap * (n - 1)) / n
    bars = [
        {
            "x": round(i * (bar_width + gap), 1),
            "width": round(bar_width, 1),
            "failed": p["failed"],
            "build": p["build"],
        }
        for i, p in enumerate(recent)
    ]
    return Sparkline(width=width, height=height, bars=bars)
