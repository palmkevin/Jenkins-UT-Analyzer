"""Pure geometry for the trend charts (issue #53) — no DB, no HTTP, no templates."""

from __future__ import annotations

from uta.web import charts


def test_run_health_timeline_empty_is_none():
    assert charts.run_health_timeline([]) is None


def test_run_health_timeline_scales_to_max_value():
    rows = [
        {"build": 1, "failed": 0, "regressions": 0},
        {"build": 2, "failed": 4, "regressions": 2},
        {"build": 3, "failed": 2, "regressions": 0},
    ]
    tl = charts.run_health_timeline(rows, width=100, height=50, pad_x=0, pad_y=0)
    assert tl.max_value == 4
    assert tl.first_build == 1
    assert tl.last_build == 3
    assert tl.runs == 3
    # Three points spread evenly across the width: x = 0, 50, 100.
    xs = [p.split(",")[0] for p in tl.failed_points.split(" ")]
    assert xs == ["0.0", "50.0", "100.0"]
    # Failed=0 at build 1 -> bottom (y=height); failed=4 (the max) at build 2 -> top (y=0).
    ys = [p.split(",")[1] for p in tl.failed_points.split(" ")]
    assert ys[0] == "50.0"
    assert ys[1] == "0.0"


def test_run_health_timeline_single_run_does_not_divide_by_zero():
    tl = charts.run_health_timeline([{"build": 7, "failed": 1, "regressions": 0}])
    assert tl.runs == 1
    assert tl.failed_points  # renders one point without raising


def test_run_health_timeline_all_clean_avoids_divide_by_zero():
    rows = [{"build": i, "failed": 0, "regressions": 0} for i in range(1, 4)]
    tl = charts.run_health_timeline(rows)
    assert tl.max_value == 1  # floored so 0/0 never happens


def test_sparkline_empty_is_none():
    assert charts.sparkline([]) is None


def test_sparkline_one_bar_per_point():
    points = [{"build": i, "failed": i % 2 == 0} for i in range(1, 6)]
    spark = charts.sparkline(points, width=100, height=20, gap=2.0)
    assert len(spark.bars) == 5
    assert [b["failed"] for b in spark.bars] == [False, True, False, True, False]
    assert [b["build"] for b in spark.bars] == [1, 2, 3, 4, 5]
    # Bars are laid out left-to-right without overlap.
    for i in range(1, len(spark.bars)):
        prev = spark.bars[i - 1]
        assert spark.bars[i]["x"] >= prev["x"] + prev["width"]


def test_sparkline_caps_to_most_recent_points():
    points = [{"build": i, "failed": False} for i in range(1, 31)]
    spark = charts.sparkline(points, max_points=20)
    assert len(spark.bars) == 20
    assert spark.bars[0]["build"] == 11  # oldest of the trailing 20
    assert spark.bars[-1]["build"] == 30  # most recent
