"""Service layer: ORM <-> engine mapping and rehearsal orchestration."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .engine import (
    ClosureInput,
    ConfigInput,
    FlightInput,
    auto_resolve,
    detect_conflicts,
)
from . import models

DEFAULT_RUNWAYS = ["09L", "09R", "18L"]
DEFAULT_WAKE_SEP = {
    "LL": 0, "LM": 0, "LH": 0,
    "ML": 120, "MM": 0, "MH": 0,
    "HL": 180, "HM": 120, "HH": 90,
}


# ---------------------------------------------------------------------------
# ORM -> engine
# ---------------------------------------------------------------------------


def _parse_dt(v) -> datetime:
    """SQLite may hand back strings; always return datetime."""
    if isinstance(v, datetime):
        return v
    return datetime.fromisoformat(v)


def load_config(db: Session) -> ConfigInput:
    row = db.get(models.AppConfig, 1)
    if row is None:
        return ConfigInput(runways=list(DEFAULT_RUNWAYS),
                           wake_sep=dict(DEFAULT_WAKE_SEP))
    return ConfigInput(
        runways=list(row.runways or DEFAULT_RUNWAYS),
        dep_occupy=row.dep_occupy,
        arr_occupy=row.arr_occupy,
        min_sep=row.min_sep,
        max_delay=row.max_delay,
        wake_sep=dict(row.wake_sep or DEFAULT_WAKE_SEP),
    )


def load_flights(db: Session) -> list[FlightInput]:
    return [
        FlightInput(
            id=f.id,
            callsign=f.callsign,
            operation=f.operation,
            runway=f.runway,
            wake=f.wake,
            scheduled=_parse_dt(f.scheduled),
            route=list(f.route or []),
            eta_to_runway=f.eta_to_runway,
            vacate_to_gate=f.vacate_to_gate,
            stand=f.stand,
        )
        for f in db.query(models.Flight).order_by(models.Flight.scheduled).all()
    ]


def load_closures(db: Session) -> list[ClosureInput]:
    return [
        ClosureInput(
            id=c.id,
            runway=c.runway,
            start=_parse_dt(c.start),
            end=_parse_dt(c.end),
            reason=c.reason,
        )
        for c in db.query(models.RunwayClosure)
        .order_by(models.RunwayClosure.start).all()
    ]


# ---------------------------------------------------------------------------
# serialisation
# ---------------------------------------------------------------------------


def _conflict_dict(c, flights_by_id) -> dict:
    return {
        "id": c.id,
        "type": c.type,
        "severity": c.severity,
        "runway": c.runway,
        "taxiway": c.taxiway,
        "flight_ids": c.flight_ids,
        "flights": c.flights,
        "message": c.message,
        "start": c.start.isoformat(),
        "end": c.end.isoformat(),
        "suggestions": c.suggestions,
    }


def rehearsal_payload(db: Session) -> dict:
    cfg = load_config(db)
    flights = load_flights(db)
    closures = load_closures(db)
    conflicts, windows = detect_conflicts(flights, closures, cfg)
    fmap = {f.id: f for f in flights}

    window_payload = []
    for w in windows:
        f = fmap[w.flight_id]
        window_payload.append({
            "flight_id": w.flight_id,
            "callsign": f.callsign,
            "operation": f.operation,
            "runway": w.runway,
            "runway_start": w.runway_window.start.isoformat(),
            "runway_end": w.runway_window.end.isoformat(),
            "taxi": [
                {"taxiway": t.taxiway,
                 "start": t.start.isoformat(),
                 "end": t.end.isoformat()}
                for t in w.taxi_windows
            ],
        })

    closure_payload = [
        {
            "id": c.id,
            "runway": c.runway,
            "start": c.start.isoformat(),
            "end": c.end.isoformat(),
            "reason": c.reason,
        }
        for c in closures
    ]

    conflict_payload = [_conflict_dict(c, fmap) for c in conflicts]
    return {
        "conflicts": conflict_payload,
        "windows": window_payload,
        "closures": closure_payload,
        "conflict_count": len(conflicts),
        "hard_count": sum(1 for c in conflicts if c.severity == "HARD"),
    }


# ---------------------------------------------------------------------------
# mutations
# ---------------------------------------------------------------------------


def apply_adjustment(db: Session, req) -> dict:
    flight = db.get(models.Flight, req.flight_id)
    if flight is None:
        raise LookupError(f"航班 {req.flight_id} 不存在")

    if req.action == "CHANGE_RUNWAY":
        if not req.to_runway:
            raise ValueError("CHANGE_RUNWAY 需要指定 to_runway")
        cfg = load_config(db)
        if req.to_runway not in cfg.runways:
            raise ValueError(f"跑道 {req.to_runway} 不在可用跑道列表中")
        flight.runway = req.to_runway
    elif req.action == "DELAY":
        if req.new_scheduled is not None:
            new_time = req.new_scheduled
            if isinstance(new_time, str):
                new_time = datetime.fromisoformat(new_time)
        elif req.delay_seconds is not None:
            new_time = _parse_dt(flight.scheduled) + timedelta(
                seconds=req.delay_seconds)
        else:
            raise ValueError("DELAY 需要 delay_seconds 或 new_scheduled")
        flight.scheduled = new_time

    db.commit()
    return rehearsal_payload(db)


def apply_auto_resolve(db: Session) -> dict:
    cfg = load_config(db)
    flights = load_flights(db)
    closures = load_closures(db)

    before, _ = detect_conflicts(flights, closures, cfg)
    delays, runway_changes, remaining, log = auto_resolve(
        flights, closures, cfg)

    new_times: dict[str, str] = {}
    rows = {f.id: f for f in db.query(models.Flight).all()}
    for fid, secs in delays.items():
        if secs:
            row = rows[fid]
            t = _parse_dt(row.scheduled) + timedelta(seconds=secs)
            row.scheduled = t
            new_times[str(fid)] = t.isoformat()
    for fid, runway in runway_changes.items():
        rows[fid].runway = runway
    db.commit()

    fmap = {f.id: f for f in flights}
    return {
        "delays": {str(k): v for k, v in delays.items() if v},
        "runway_changes": {str(k): v for k, v in runway_changes.items()},
        "new_times": new_times,
        "remaining": [_conflict_dict(c, fmap) for c in remaining],
        "log": log,
        "resolved_count": len(before) - len(remaining),
    }


def ensure_config(db: Session) -> models.AppConfig:
    row = db.get(models.AppConfig, 1)
    if row is None:
        row = models.AppConfig(
            id=1,
            runways=list(DEFAULT_RUNWAYS),
            dep_occupy=60,
            arr_occupy=50,
            min_sep=30,
            max_delay=1800,
            wake_sep=dict(DEFAULT_WAKE_SEP),
        )
        db.add(row)
        db.commit()
    return row
