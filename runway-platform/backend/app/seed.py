"""首启时写入演示场景：3 条跑道、6 个航班、1 个关闭区间，内含若干冲突。"""
from sqlalchemy.orm import Session

from . import engine as eng
from .models import Flight, Runway, RunwayClosure, SeparationRule
from .routers.simulation import DEFAULT_MATRIX, MATRIX_ID


def _dt(value):
    return eng.parse_ts(value) if value else None

DEMO_DATE = "2026-09-19"

DEMO_RUNWAYS = [
    {"id": "09L", "name": "09 左跑道", "active": True},
    {"id": "09R", "name": "09 右跑道", "active": True},
    {"id": "18", "name": "18 号跑道", "active": True},
]

DEMO_FLIGHTS = [
    {
        "id": "CA1201",
        "callsign": "CCA1201",
        "operation": "departure",
        "runway_id": "09L",
        "scheduled_time": f"{DEMO_DATE}T08:00:00Z",
        "takeoff_time": f"{DEMO_DATE}T08:00:00Z",
        "enter_offset": 60,
        "vacate_offset": 40,
        "aircraft_category": "H",
        "route": [
            {"name": "A1", "type": "taxiway", "taxi_seconds": 60},
            {"name": "等待点 W9", "type": "taxiway", "taxi_seconds": 45},
            {"name": "RWY09L", "type": "runway", "runway_id": "09L",
             "primary": True, "enter_offset": 60, "vacate_offset": 40},
        ],
    },
    {
        "id": "MU5102",
        "callsign": "CES5102",
        "operation": "departure",
        "runway_id": "09L",
        "scheduled_time": f"{DEMO_DATE}T08:01:30Z",
        "takeoff_time": f"{DEMO_DATE}T08:01:30Z",
        "enter_offset": 60,
        "vacate_offset": 40,
        "aircraft_category": "M",
        "route": [
            {"name": "A2", "type": "taxiway", "taxi_seconds": 60},
            {"name": "RWY09L", "type": "runway", "runway_id": "09L",
             "primary": True, "enter_offset": 60, "vacate_offset": 40},
        ],
    },
    {
        "id": "CZ3305",
        "callsign": "CSN3305",
        "operation": "arrival",
        "runway_id": "09L",
        "scheduled_time": f"{DEMO_DATE}T08:03:00Z",
        "landing_time": f"{DEMO_DATE}T08:03:00Z",
        "enter_offset": 50,
        "vacate_offset": 50,
        "aircraft_category": "M",
        "route": [
            {"name": "RWY09L", "type": "runway", "runway_id": "09L",
             "primary": True, "enter_offset": 50, "vacate_offset": 50},
            {"name": "A3", "type": "taxiway", "taxi_seconds": 60},
            {"name": "B7", "type": "taxiway", "taxi_seconds": 45},
        ],
    },
    {
        "id": "HU7801",
        "callsign": "CHH7801",
        "operation": "departure",
        "runway_id": "09R",
        "scheduled_time": f"{DEMO_DATE}T08:05:00Z",
        "takeoff_time": f"{DEMO_DATE}T08:05:00Z",
        "enter_offset": 60,
        "vacate_offset": 40,
        "aircraft_category": "M",
        "route": [
            {"name": "A5", "type": "taxiway", "taxi_seconds": 50},
            {"name": "穿越 18", "type": "runway", "runway_id": "18",
             "crossing_duration": 30, "taxi_seconds": 40},
            {"name": "RWY09R", "type": "runway", "runway_id": "09R",
             "primary": True, "enter_offset": 60, "vacate_offset": 40},
        ],
    },
    {
        "id": "CA1888",
        "callsign": "CCA1888",
        "operation": "arrival",
        "runway_id": "18",
        "scheduled_time": f"{DEMO_DATE}T08:05:20Z",
        "landing_time": f"{DEMO_DATE}T08:05:20Z",
        "enter_offset": 50,
        "vacate_offset": 50,
        "aircraft_category": "M",
        "route": [
            {"name": "RWY18", "type": "runway", "runway_id": "18",
             "primary": True, "enter_offset": 50, "vacate_offset": 50},
            {"name": "D2", "type": "taxiway", "taxi_seconds": 55},
        ],
    },
    {
        "id": "MU5208",
        "callsign": "CES5208",
        "operation": "departure",
        "runway_id": "09R",
        "scheduled_time": f"{DEMO_DATE}T08:12:00Z",
        "takeoff_time": f"{DEMO_DATE}T08:12:00Z",
        "enter_offset": 60,
        "vacate_offset": 40,
        "aircraft_category": "M",
        "route": [
            {"name": "A6", "type": "taxiway", "taxi_seconds": 50},
            {"name": "RWY09R", "type": "runway", "runway_id": "09R",
             "primary": True, "enter_offset": 60, "vacate_offset": 40},
        ],
    },
]

DEMO_CLOSURES = [
    {
        "id": "CL-09R-AM",
        "runway_id": "09R",
        "start_time": f"{DEMO_DATE}T08:10:00Z",
        "end_time": f"{DEMO_DATE}T08:20:00Z",
        "reason": "道面维护",
    }
]


def seed_if_empty(db: Session) -> bool:
    if db.query(Runway).first():
        return False
    db.add_all([Runway(**r) for r in DEMO_RUNWAYS])
    db.add_all(
        [
            Flight(
                **{
                    **f,
                    "scheduled_time": _dt(f.get("scheduled_time")),
                    "takeoff_time": _dt(f.get("takeoff_time")),
                    "landing_time": _dt(f.get("landing_time")),
                }
            )
            for f in DEMO_FLIGHTS
        ]
    )
    db.add_all(
        [
            RunwayClosure(
                **{
                    **c,
                    "start_time": eng.parse_ts(c["start_time"]),
                    "end_time": eng.parse_ts(c["end_time"]),
                }
            )
            for c in DEMO_CLOSURES
        ]
    )
    db.add(SeparationRule(id=MATRIX_ID, matrix=DEFAULT_MATRIX))
    db.commit()
    return True
