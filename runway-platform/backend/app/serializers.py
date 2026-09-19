"""ORM 对象与引擎使用的 dict 之间的序列化。"""
from datetime import datetime

from . import engine


def _dt(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return engine.fmt_ts(engine.parse_ts(value))
    if isinstance(value, datetime):
        return engine.fmt_ts(value)
    return str(value)


def flight_to_dict(f) -> dict:
    route = []
    for step in f.route or []:
        route.append(
            {
                "name": step.get("name"),
                "type": step.get("type", "taxiway"),
                "runway_id": step.get("runway_id"),
                "primary": step.get("primary", False),
                "crossing_duration": step.get("crossing_duration", 30),
                "taxi_seconds": step.get("taxi_seconds", 45),
                "enter_offset": step.get("enter_offset"),
                "vacate_offset": step.get("vacate_offset"),
            }
        )
    return {
        "id": f.id,
        "callsign": f.callsign,
        "operation": f.operation,
        "runway_id": f.runway_id,
        "scheduled_time": _dt(f.scheduled_time),
        "takeoff_time": _dt(f.takeoff_time),
        "landing_time": _dt(f.landing_time),
        "enter_offset": f.enter_offset or 60,
        "vacate_offset": f.vacate_offset or 40,
        "route": route,
        "aircraft_category": f.aircraft_category or "M",
    }


def flight_to_out(f) -> dict:
    d = flight_to_dict(f)
    return {k: v for k, v in d.items() if v is not None or k == "route"}


def runway_to_dict(r) -> dict:
    return {"id": r.id, "name": r.name, "active": bool(r.active)}


def closure_to_dict(c) -> dict:
    return {
        "id": c.id,
        "runway_id": c.runway_id,
        "start_time": _dt(c.start_time),
        "end_time": _dt(c.end_time),
        "reason": c.reason or "",
    }
