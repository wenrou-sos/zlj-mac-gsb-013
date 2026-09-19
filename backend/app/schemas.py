"""Pydantic schemas for the REST API."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---- requests -------------------------------------------------------------


class FlightBase(BaseModel):
    callsign: str = Field(..., examples=["CA1201"])
    operation: str = Field("DEP", pattern="^(ARR|DEP)$")
    runway: str
    wake: str = Field("M", pattern="^[LMH]$")
    scheduled: datetime
    route: list[str] = Field(default_factory=list)
    eta_to_runway: int = Field(300, ge=0, le=7200)
    vacate_to_gate: int = Field(240, ge=0, le=7200)
    stand: Optional[str] = None
    note: Optional[str] = None

    @field_validator("callsign")
    @classmethod
    def _callsign_upper(cls, v: str) -> str:
        return v.strip().upper()


class FlightCreate(FlightBase):
    pass


class FlightUpdate(BaseModel):
    callsign: Optional[str] = None
    operation: Optional[str] = Field(None, pattern="^(ARR|DEP)$")
    runway: Optional[str] = None
    wake: Optional[str] = Field(None, pattern="^[LMH]$")
    scheduled: Optional[datetime] = None
    route: Optional[list[str]] = None
    eta_to_runway: Optional[int] = Field(None, ge=0, le=7200)
    vacate_to_gate: Optional[int] = Field(None, ge=0, le=7200)
    stand: Optional[str] = None
    note: Optional[str] = None


class ClosureCreate(BaseModel):
    runway: str
    start: datetime
    end: datetime
    reason: Optional[str] = None


class ClosureUpdate(BaseModel):
    runway: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    reason: Optional[str] = None


class ConfigUpdate(BaseModel):
    runways: Optional[list[str]] = None
    dep_occupy: Optional[int] = Field(None, ge=10, le=900)
    arr_occupy: Optional[int] = Field(None, ge=10, le=900)
    min_sep: Optional[int] = Field(None, ge=0, le=900)
    max_delay: Optional[int] = Field(None, ge=30, le=14400)
    wake_sep: Optional[dict[str, int]] = None


class AdjustRequest(BaseModel):
    flight_id: int
    action: str = Field(pattern="^(DELAY|CHANGE_RUNWAY)$")
    delay_seconds: Optional[int] = Field(None, ge=-3600, le=14400)
    to_runway: Optional[str] = None
    new_scheduled: Optional[datetime] = None


# ---- responses ------------------------------------------------------------


class FlightOut(FlightBase):
    id: int

    class Config:
        from_attributes = True


class ClosureOut(ClosureCreate):
    id: int

    class Config:
        from_attributes = True


class SuggestionOut(BaseModel):
    action: str
    flight_id: int
    callsign: str
    delay_seconds: Optional[int] = None
    new_scheduled: Optional[datetime] = None
    to_runway: Optional[str] = None
    from_runway: Optional[str] = None
    note: Optional[str] = None


class ConflictOut(BaseModel):
    id: str
    type: str
    severity: str
    runway: Optional[str]
    taxiway: Optional[str]
    flight_ids: list[int]
    flights: list[str]
    message: str
    start: datetime
    end: datetime
    suggestions: list[SuggestionOut]


class TaxiBarOut(BaseModel):
    taxiway: str
    start: datetime
    end: datetime


class WindowOut(BaseModel):
    flight_id: int
    callsign: str
    operation: str
    runway: str
    runway_start: datetime
    runway_end: datetime
    taxi: list[TaxiBarOut]


class RehearsalOut(BaseModel):
    conflicts: list[ConflictOut]
    windows: list[WindowOut]
    closures: list[ClosureOut]
    conflict_count: int
    hard_count: int


class AutoResolveOut(BaseModel):
    delays: dict[str, int]
    runway_changes: dict[str, str] = Field(default_factory=dict)
    new_times: dict[str, datetime]
    remaining: list[ConflictOut]
    log: list[str]
    resolved_count: int
