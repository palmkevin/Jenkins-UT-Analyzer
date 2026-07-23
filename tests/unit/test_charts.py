"""Pure geometry for the trend charts (issue #53) — no DB, no HTTP, no templates."""

from __future__ import annotations

from uta.web import charts


def test_build_health_timeline_empty_is_none():
    assert charts.build_health_timeline([]) is None


def test_build_health_timeline_scales_to_max_value():
    rows = [
        {"number": 1, "failed": 0, "regressions": 0},
        {"number": 2, "failed": 4, "regressions": 2},
        {"number": 3, "failed": 2, "regressions": 0},
    ]
    tl = charts.build_health_timeline(rows, width=100, height=50, pad_x=0, pad_y=0)
    assert tl.max_value == 4
    assert tl.first_build == 1
    assert tl.last_build == 3
    assert tl.builds == 3
    # Three points spread evenly across the width: x = 0, 50, 100.
    xs = [p.split(",")[0] for p in tl.failed_points.split(" ")]
    assert xs == ["0.0", "50.0", "100.0"]
    # Failed=0 at build 1 -> bottom (y=height); failed=4 (the max) at build 2 -> top (y=0).
    ys = [p.split(",")[1] for p in tl.failed_points.split(" ")]
    assert ys[0] == "50.0"
    assert ys[1] == "0.0"


def test_build_health_timeline_single_run_does_not_divide_by_zero():
    tl = charts.build_health_timeline([{"number": 7, "failed": 1, "regressions": 0}])
    assert tl.builds == 1
    assert tl.failed_points  # renders one point without raising


def test_build_health_timeline_all_clean_avoids_divide_by_zero():
    rows = [{"number": i, "failed": 0, "regressions": 0} for i in range(1, 4)]
    tl = charts.build_health_timeline(rows)
    assert tl.max_value == 1  # floored so 0/0 never happens


def test_sparkline_empty_is_none():
    assert charts.sparkline([]) is None


def test_sparkline_one_bar_per_point():
    points = [{"number": i, "failed": i % 2 == 0} for i in range(1, 6)]
    spark = charts.sparkline(points, width=100, height=20, gap=2.0)
    assert len(spark.bars) == 5
    assert [b["failed"] for b in spark.bars] == [False, True, False, True, False]
    assert [b["number"] for b in spark.bars] == [1, 2, 3, 4, 5]
    # Bars are laid out left-to-right without overlap.
    for i in range(1, len(spark.bars)):
        prev = spark.bars[i - 1]
        assert spark.bars[i]["x"] >= prev["x"] + prev["width"]


def test_sparkline_failed_bars_taller_than_passed_bars():
    """Height is a second, non-hue pass/fail channel (issue #144): failed = full, passed = short."""
    points = [{"number": 1, "failed": True}, {"number": 2, "failed": False}]
    spark = charts.sparkline(points, width=100, height=20, gap=2.0)
    failed, passed = spark.bars
    assert failed["y"] == 0.0 and failed["height"] == 20.0  # full-height
    assert 0 < passed["height"] < failed["height"]  # visibly shorter
    assert passed["y"] + passed["height"] == spark.height  # bottom-aligned


def test_sparkline_caps_to_most_recent_points():
    points = [{"number": i, "failed": False} for i in range(1, 31)]
    spark = charts.sparkline(points, max_points=20)
    assert len(spark.bars) == 20
    assert spark.bars[0]["number"] == 11  # oldest of the trailing 20
    assert spark.bars[-1]["number"] == 30  # most recent
