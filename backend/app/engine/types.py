"""Engine domain types (plain dataclasses, independent of the ORM)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class FlightInput:
    id: int
    callsign: str
    operation: str  # 'ARR' | 'DEP'
    runway: str
    scheduled: datetime
    route: list[str] = field(default_factory=list)
    eta_to_runway: int = 300
    vacate_to_gate: int = 240
    wake: str = "M"
    stand: Optional[str] = None


@dataclass
class ClosureInput:
    id: int
    runway: str
    start: datetime
    end: datetime
    reason: Optional[str] = None


@dataclass
class ConfigInput:
    runways: list[str] = field(default_factory=list)
    dep_occupy: int = 60
    arr_occupy: int = 50
    min_sep: int = 30
    max_delay: int = 1800
    wake_sep: dict[str, int] = field(default_factory=dict)


@dataclass
class Window:
    start: datetime
    end: datetime


@dataclass
class RunwayWindow(Window):
    kind: str = "runway"


@dataclass
class TaxiWindow(Window):
    taxiway: str = ""


@dataclass
class FlightWindows:
    flight_id: int
    runway: str
    runway_window: RunwayWindow
    taxi_windows: list[TaxiWindow] = field(default_factory=list)


@dataclass
class Conflict:
    id: str
    type: str  # 'SEPARATION' | 'CLOSURE' | 'TAXIWAY'
    severity: str  # 'HARD' | 'SOFT'
    runway: Optional[str]
    taxiway: Optional[str]
    flight_ids: list[int]
    flights: list[str]  # callsigns
    message: str
    start: datetime
    end: datetime
    suggestions: list[dict] = field(default_factory=list)


@dataclass
class RehearsalResult:
    conflicts: list[Conflict]
    windows: list[FlightWindows]
    closures: list[ClosureInput]
    adjusted: dict[int, int]  # flight_id -> total applied delay seconds
    remaining_conflicts: list[Conflict]
    resolver_log: list[str]
