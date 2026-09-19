"""Unit tests for the conflict detection engine."""
from datetime import datetime, timedelta

from app.engine import (
    ClosureInput,
    ConfigInput,
    FlightInput,
    auto_resolve,
    detect_conflicts,
)
from app.engine.scheduler import earliest_feasible_delay, required_separation

T0 = datetime(2026, 9, 18, 8, 0, 0)


def cfg(**kw):
    base = dict(
        runways=["09L", "09R", "18L"],
        dep_occupy=60,
        arr_occupy=50,
        min_sep=30,
        max_delay=1800,
        wake_sep={"ML": 120, "HL": 180, "HM": 120, "HH": 90},
    )
    base.update(kw)
    return ConfigInput(**base)


def flight(fid, callsign, op, runway, t, wake="M", route=None,
           eta=300, vac=240):
    return FlightInput(
        id=fid, callsign=callsign, operation=op, runway=runway,
        scheduled=t, wake=wake, route=route or [],
        eta_to_runway=eta, vacate_to_gate=vac,
    )


# ---------- runway windows --------------------------------------------------


def test_dep_runway_window_starts_at_takeoff():
    from app.engine.windows import runway_window

    f = flight(1, "CA1", "DEP", "09L", T0)
    w = runway_window(f, cfg())
    assert w.start == T0
    assert w.end == T0 + timedelta(seconds=60)


def test_arr_runway_window_ends_at_landing():
    from app.engine.windows import runway_window

    f = flight(1, "CA1", "ARR", "09L", T0)
    w = runway_window(f, cfg())
    assert w.start == T0 - timedelta(seconds=50)
    assert w.end == T0


# ---------- separation ------------------------------------------------------


def test_separation_conflict_detected():
    a = flight(1, "CA1", "DEP", "09L", T0, wake="H")
    b = flight(2, "CA2", "DEP", "09L", T0 + timedelta(seconds=60))
    conflicts, _ = detect_conflicts([a, b], [], cfg())
    sep = [c for c in conflicts if c.type == "SEPARATION"]
    assert len(sep) == 1
    # H -> M needs 30 + 120 = 150s
    assert "150s" in sep[0].message
    assert sep[0].severity == "SOFT"
    assert sep[0].suggestions[0]["action"] == "DELAY"
    assert sep[0].suggestions[0]["flight_id"] == 2


def test_overlapping_runway_use_is_hard():
    a = flight(1, "CA1", "DEP", "09L", T0)
    b = flight(2, "CA2", "DEP", "09L", T0 + timedelta(seconds=20))
    conflicts, _ = detect_conflicts([a, b], [], cfg())
    sep = [c for c in conflicts if c.type == "SEPARATION"]
    assert sep[0].severity == "HARD"


def test_clear_schedule_has_no_conflicts():
    a = flight(1, "CA1", "DEP", "09L", T0)
    b = flight(2, "CA2", "DEP", "09L", T0 + timedelta(seconds=300))
    conflicts, _ = detect_conflicts([a, b], [], cfg())
    assert conflicts == []


def test_different_runways_no_separation_conflict():
    a = flight(1, "CA1", "DEP", "09L", T0)
    b = flight(2, "CA2", "DEP", "09R", T0 + timedelta(seconds=10))
    conflicts, _ = detect_conflicts([a, b], [], cfg())
    assert [c for c in conflicts if c.type == "SEPARATION"] == []


def test_required_separation_uses_wake_matrix():
    heavy = flight(1, "H1", "DEP", "09L", T0, wake="H")
    light = flight(2, "L1", "DEP", "09L", T0, wake="L")
    assert required_separation(heavy, light, cfg()) == 30 + 180


# ---------- closures --------------------------------------------------------


def test_departure_inside_closure_conflicts():
    f = flight(1, "CA1", "DEP", "09L", T0)
    closure = ClosureInput(id=1, runway="09L",
                           start=T0 - timedelta(minutes=5),
                           end=T0 + timedelta(minutes=10))
    conflicts, _ = detect_conflicts([f], [closure], cfg())
    clo = [c for c in conflicts if c.type == "CLOSURE"]
    assert len(clo) == 1
    assert clo[0].severity == "HARD"
    assert clo[0].suggestions[0]["action"] == "DELAY"


def test_departure_after_closure_is_fine():
    f = flight(1, "CA1", "DEP", "09L", T0 + timedelta(minutes=20))
    closure = ClosureInput(id=1, runway="09L",
                           start=T0 - timedelta(minutes=5),
                           end=T0 + timedelta(minutes=10))
    conflicts, _ = detect_conflicts([f], [closure], cfg())
    assert [c for c in conflicts if c.type == "CLOSURE"] == []


def test_alt_runway_suggested_when_available():
    f = flight(1, "CA1", "DEP", "09L", T0)
    closure = ClosureInput(id=1, runway="09L",
                           start=T0 - timedelta(minutes=5),
                           end=T0 + timedelta(minutes=10))
    conflicts, _ = detect_conflicts([f], [closure], cfg())
    actions = {(s["action"], s.get("to_runway"))
               for s in conflicts[0].suggestions}
    assert ("CHANGE_RUNWAY", "09R") in actions


# ---------- taxiways --------------------------------------------------------


def test_taxiway_node_conflict_detected():
    # two DEPs cross node B3 at overlapping times
    a = flight(1, "CA1", "DEP", "09L", T0 + timedelta(seconds=30),
               route=["G1", "C1", "B3", "A", "R09L"], eta=300)
    b = flight(2, "CA2", "DEP", "09R", T0 + timedelta(seconds=30),
               route=["G2", "C2", "B3", "A2", "R09R"], eta=300)
    conflicts, _ = detect_conflicts([a, b], [], cfg())
    tax = [c for c in conflicts if c.type == "TAXIWAY"]
    assert tax and tax[0].taxiway == "B3"
    assert set(tax[0].flight_ids) == {1, 2}


def test_staggered_taxi_no_conflict():
    a = flight(1, "CA1", "DEP", "09L", T0 + timedelta(seconds=60),
               route=["G1", "C1", "B3", "A", "R09L"], eta=200)
    b = flight(2, "CA2", "DEP", "09R", T0 + timedelta(seconds=360),
               route=["G2", "C2", "B3", "A2", "R09R"], eta=200)
    conflicts, _ = detect_conflicts([a, b], [], cfg())
    assert [c for c in conflicts if c.type == "TAXIWAY"] == []


# ---------- feasibility helper ----------------------------------------------


def test_earliest_feasible_delay_returns_zero_when_clear():
    a = flight(1, "CA1", "DEP", "09L", T0)
    b = flight(2, "CA2", "DEP", "09L", T0 + timedelta(seconds=600))
    assert earliest_feasible_delay(b, [a], [], cfg(), 1800) == 0


def test_earliest_feasible_delay_finds_gap():
    a = flight(1, "CA1", "DEP", "09L", T0, wake="M")
    b = flight(2, "CA2", "DEP", "09L", T0 + timedelta(seconds=60), wake="M")
    # a occupies [T0, T0+60], need 30s gap -> b at T0+90 => delay 30
    d = earliest_feasible_delay(b, [a], [], cfg(min_sep=30), 1800)
    assert d is not None
    shifted = b
    from datetime import timedelta as td
    shifted = FlightInput(
        id=b.id, callsign=b.callsign, operation=b.operation,
        runway=b.runway, scheduled=b.scheduled + td(seconds=d),
        wake=b.wake)
    remaining, _ = detect_conflicts([a, shifted], [], cfg(min_sep=30))
    assert [c for c in remaining if c.type == "SEPARATION"] == []


# ---------- auto resolver ---------------------------------------------------


def test_auto_resolve_clears_separation_and_closure():
    flights = [
        flight(1, "CA1", "DEP", "09L", T0, wake="H"),
        flight(2, "CA2", "DEP", "09L", T0 + timedelta(seconds=30), wake="M"),
        flight(3, "CA3", "DEP", "09L", T0 + timedelta(minutes=20)),
    ]
    closures = [ClosureInput(
        id=1, runway="09L",
        start=T0 + timedelta(minutes=10),
        end=T0 + timedelta(minutes=45))]
    c0 = cfg()
    before, _ = detect_conflicts(flights, closures, c0)
    assert len(before) >= 2

    delays, runway_changes, remaining, log = auto_resolve(flights, closures, c0)
    assert remaining == []
    assert delays[2] > 0
    assert delays[3] >= 25 * 60
    assert any("调度完成" in line for line in log)


def test_auto_resolve_respects_max_delay():
    flights = [
        flight(1, "CA1", "DEP", "09L", T0),
        flight(2, "CA2", "DEP", "09L", T0 + timedelta(seconds=30)),
    ]
    # single runway + zero delay budget -> nothing can be resolved
    c = cfg(max_delay=0, runways=["09L"])
    delays, runway_changes, remaining, _ = auto_resolve(flights, [], c)
    assert delays[2] == 0
    assert runway_changes == {}
    assert remaining
