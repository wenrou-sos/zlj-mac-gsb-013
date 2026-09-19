"""Built-in demonstration scenario (a single busy morning bank)."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from . import models, service


def _today(hour: int, minute: int, second: int = 0) -> datetime:
    base = datetime.combine(datetime.now().date(),
                            datetime.min.time())
    return base + timedelta(hours=hour, minutes=minute, seconds=second)


def demo_rows():
    """Return (flights, closures) ORM-ready dicts for the demo scenario."""
    t = _today
    flights = [
        dict(callsign="CA1201", operation="ARR", runway="09L", wake="H",
             scheduled=t(8, 0, 0),
             route=["R09L", "A", "B3", "GATE101"],
             eta_to_runway=300, vacate_to_gate=240, stand="101",
             note="重载客班，09L 落地"),
        dict(callsign="CA9021", operation="DEP", runway="09L", wake="H",
             scheduled=t(8, 0, 30),
             route=["GATE102", "C1", "B3", "A", "R09L"],
             eta_to_runway=300, vacate_to_gate=240, stand="102",
             note="与 CA1201 间隔不足"),
        dict(callsign="MU2310", operation="DEP", runway="09L", wake="M",
             scheduled=t(8, 1, 0),
             route=["GATE103", "C2", "B3", "A", "R09L"],
             eta_to_runway=300, vacate_to_gate=240, stand="103",
             note="紧随 CA9021 起飞"),
        dict(callsign="HU7788", operation="DEP", runway="09L", wake="M",
             scheduled=t(8, 20, 0),
             route=["GATE104", "C2", "B4", "A", "R09L"],
             eta_to_runway=300, vacate_to_gate=240, stand="104",
             note="计划落在 09L 关闭窗口内"),
        dict(callsign="CZ6602", operation="DEP", runway="18L", wake="M",
             scheduled=t(8, 2, 30),
             route=["GATE201", "D1", "E2", "R18L"],
             eta_to_runway=300, vacate_to_gate=240, stand="201",
             note="独立跑道起飞"),
        dict(callsign="3U8805", operation="ARR", runway="09R", wake="L",
             scheduled=t(8, 5, 0),
             route=["R09R", "A5", "B1", "GATE301"],
             eta_to_runway=300, vacate_to_gate=240, stand="301",
             note="09R 轻型进港"),
        dict(callsign="9C8805", operation="DEP", runway="09R", wake="M",
             scheduled=t(8, 5, 20),
             route=["GATE302", "B1", "A5", "R09R"],
             eta_to_runway=300, vacate_to_gate=240, stand="302",
             note="09R 紧随进港，间隔紧张"),
    ]
    closures = [
        dict(runway="09L", start=t(8, 10, 0), end=t(8, 45, 0),
             reason="例行道面检查"),
    ]
    return flights, closures


def seed_database(db: Session, wipe: bool = True) -> None:
    service.ensure_config(db)
    if wipe:
        db.query(models.Flight).delete()
        db.query(models.RunwayClosure).delete()
    flights, closures = demo_rows()
    for row in flights:
        db.add(models.Flight(**row))
    for row in closures:
        db.add(models.RunwayClosure(**row))
    db.commit()
