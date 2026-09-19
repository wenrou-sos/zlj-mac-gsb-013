from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class RunwayIn(BaseModel):
    id: str
    name: str
    active: bool = True


class RunwayOut(RunwayIn):
    pass


class RouteStep(BaseModel):
    name: str
    type: Literal["runway", "taxiway"]
    runway_id: Optional[str] = None
    primary: bool = False
    crossing_duration: int = 30
    taxi_seconds: int = 45
    enter_offset: Optional[int] = None
    vacate_offset: Optional[int] = None


class FlightIn(BaseModel):
    id: str
    callsign: str
    operation: Literal["arrival", "departure"]
    runway_id: str
    scheduled_time: Optional[datetime] = None
    takeoff_time: Optional[datetime] = None
    landing_time: Optional[datetime] = None
    enter_offset: int = 60
    vacate_offset: int = 40
    route: list[RouteStep] = Field(default_factory=list)
    aircraft_category: str = "M"

    @model_validator(mode="after")
    def _check_time(self):
        if self.operation == "departure" and self.takeoff_time is None:
            raise ValueError("离场航班必须提供 takeoff_time")
        if self.operation == "arrival" and self.landing_time is None:
            raise ValueError("进场航班必须提供 landing_time")
        return self


class FlightOut(FlightIn):
    pass


class ClosureIn(BaseModel):
    id: str
    runway_id: str
    start_time: datetime
    end_time: datetime
    reason: str = ""

    @model_validator(mode="after")
    def _check_range(self):
        if self.end_time <= self.start_time:
            raise ValueError("关闭结束时间必须晚于开始时间")
        return self


class ClosureOut(ClosureIn):
    pass


class ConflictOut(BaseModel):
    id: str
    type: str
    runway_id: str
    flight_ids: list[str]
    message: str
    time: datetime
    severity: str
    actual_gap_seconds: Optional[int] = None
    required_gap_seconds: Optional[int] = None
    closure_id: Optional[str] = None
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None


class ResolutionOption(BaseModel):
    kind: str
    delta_seconds: Optional[int] = None
    new_runway_id: Optional[str] = None
    description: str
    residual_conflicts: Optional[int] = None


class ResolutionOut(BaseModel):
    flight_id: str
    callsign: str
    conflict_ids: list[str]
    options: list[ResolutionOption]


class AnalyzeResponse(BaseModel):
    conflicts: list[dict[str, Any]]
    resolutions: list[dict[str, Any]]


class AutoResolveRequest(BaseModel):
    pass


class AutoResolveResponse(BaseModel):
    flights: list[dict[str, Any]]
    adjustments: list[dict[str, Any]]
    total_delay_seconds: int
    remaining_conflicts: list[dict[str, Any]]


class SeparationIn(BaseModel):
    matrix: dict[str, dict[str, int]]


class SeparationOut(SeparationIn):
    pass
