from datetime import datetime, timedelta, timezone

import pytest

from app import engine

T0 = datetime(2026, 9, 19, 8, 0, 0, tzinfo=timezone.utc)


def iso(offset_seconds: float) -> str:
    return engine.fmt_ts(T0 + timedelta(seconds=offset_seconds))


def make_flight(fid, op, runway, ref_offset, route=None, **kw):
    key = "takeoff_time" if op == engine.DEPARTURE else "landing_time"
    return {
        "id": fid,
        "callsign": fid,
        "operation": op,
        "runway_id": runway,
        key: iso(ref_offset),
        "enter_offset": kw.get("enter_offset", 60),
        "vacate_offset": kw.get("vacate_offset", 40),
        "route": route or [],
    }


def test_separation_conflict_detected():
    # 两架同跑道离场，间隔 90s < 规定 120s
    f1 = make_flight("F1", engine.DEPARTURE, "09L", 0)
    f2 = make_flight("F2", engine.DEPARTURE, "09L", 90)
    matrix = {"departure": {"departure": 120}}
    conflicts = engine.detect_conflicts([f1, f2], None, matrix)
    kinds = {c["type"] for c in conflicts}
    assert "SEPARATION" in kinds
    sep = next(c for c in conflicts if c["type"] == "SEPARATION")
    assert sep["actual_gap_seconds"] == 90
    assert sep["required_gap_seconds"] == 120


def test_occupancy_overlap_conflict():
    # 间隔 60s，占用窗口 [-60,+40] 与 [0,+100] 重叠
    f1 = make_flight("F1", engine.DEPARTURE, "09L", 0)
    f2 = make_flight("F2", engine.DEPARTURE, "09L", 60)
    conflicts = engine.detect_conflicts([f1, f2], None, None)
    assert any(c["type"] == "OCCUPANCY" for c in conflicts)


def test_no_conflict_when_separated():
    f1 = make_flight("F1", engine.DEPARTURE, "09L", 0)
    f2 = make_flight("F2", engine.DEPARTURE, "09L", 300)
    assert engine.detect_conflicts([f1, f2]) == []


def test_different_runways_no_conflict():
    f1 = make_flight("F1", engine.DEPARTURE, "09L", 0)
    f2 = make_flight("F2", engine.DEPARTURE, "09R", 10)
    assert engine.detect_conflicts([f1, f2]) == []


def test_closure_conflict():
    f1 = make_flight("F1", engine.DEPARTURE, "09L", 0)
    closure = {
        "id": "C1",
        "runway_id": "09L",
        "start_time": iso(-30),
        "end_time": iso(30),
    }
    conflicts = engine.detect_conflicts([f1], [closure])
    assert len(conflicts) == 1
    assert conflicts[0]["type"] == "CLOSURE"


def test_crossing_conflict():
    # HU 离场路线先穿越 18 号跑道（taxi 60s 前），CA 在 18 落地
    hu_route = [
        {"name": "X", "type": "runway", "runway_id": "18",
         "crossing_duration": 30, "taxi_seconds": 60},
        {"name": "RWY09R", "type": "runway", "runway_id": "09R", "primary": True},
    ]
    hu = make_flight("HU", engine.DEPARTURE, "09R", 0, route=hu_route)
    ca = make_flight("CA", engine.ARRIVAL, "18", -50)
    conflicts = engine.detect_conflicts([hu, ca])
    assert any(c["type"] == "CROSSING" for c in conflicts)


def test_delay_suggestion_resolves():
    f1 = make_flight("F1", engine.DEPARTURE, "09L", 0)
    f2 = make_flight("F2", engine.DEPARTURE, "09L", 60)
    sugs = engine.suggest_resolutions(
        [f1, f2], None, {"departure": {"departure": 120}},
        runways=[{"id": "09L", "active": True}],
    )
    f2_sug = next(s for s in sugs if s["flight_id"] == "F2")
    delay = next(o for o in f2_sug["options"] if o["kind"] == "DELAY")
    # 至少顺延到 120s 间隔
    assert delay["delta_seconds"] >= 60
    moved = engine.shift_flight(f2, delay["delta_seconds"])
    assert engine.detect_conflicts([f1, moved]) == []


def test_change_runway_option():
    f1 = make_flight("F1", engine.DEPARTURE, "09L", 0)
    f2 = make_flight("F2", engine.DEPARTURE, "09L", 60)
    sugs = engine.suggest_resolutions(
        [f1, f2], None, None,
        runways=[{"id": "09L", "active": True}, {"id": "09R", "active": True}],
    )
    f2_sug = next(s for s in sugs if s["flight_id"] == "F2")
    assert any(o["kind"] == "CHANGE_RUNWAY" and o["new_runway_id"] == "09R"
               for o in f2_sug["options"])


def test_auto_resolve_eliminates_conflicts():
    f1 = make_flight("F1", engine.DEPARTURE, "09L", 0)
    f2 = make_flight("F2", engine.DEPARTURE, "09L", 60)
    f3 = make_flight("F3", engine.DEPARTURE, "09L", 100)
    result = engine.auto_resolve(
        [f1, f2, f3], None, {"departure": {"departure": 120}}
    )
    assert result["remaining_conflicts"] == []
    assert result["total_delay_seconds"] > 0
    # 自动排程后每架航班的起飞时刻单调不减且满足间隔
    times = sorted(engine.base_time(f) for f in result["flights"])
    assert (times[1] - times[0]).total_seconds() >= 120
    assert (times[2] - times[1]).total_seconds() >= 120


def test_auto_resolve_with_closure():
    f1 = make_flight("F1", engine.DEPARTURE, "09L", 0)
    closure = {
        "id": "C1", "runway_id": "09L",
        "start_time": iso(-30), "end_time": iso(120),
    }
    result = engine.auto_resolve([f1], [closure])
    assert result["remaining_conflicts"] == []
    assert result["adjustments"][0]["delta_seconds"] >= 150


def test_shift_flight_moves_all_times():
    f1 = make_flight("F1", engine.DEPARTURE, "09L", 0)
    f1["scheduled_time"] = iso(0)
    moved = engine.shift_flight(f1, 300)
    assert engine.parse_ts(moved["takeoff_time"]) == T0 + timedelta(seconds=300)
    assert engine.parse_ts(moved["scheduled_time"]) == T0 + timedelta(seconds=300)
