"""Runway / taxiway occupancy modelling."""
from __future__ import annotations

from datetime import timedelta

from .types import ConfigInput, FlightInput, FlightWindows, RunwayWindow, TaxiWindow


def _span(route: list[str]) -> int:
    """Number of edges in a route (n nodes => n-1 segments)."""
    return max(0, len(route) - 1)


def runway_window(flight: FlightInput, cfg: ConfigInput) -> RunwayWindow:
    """Occupancy of the runway itself.

    DEP: [take-off, take-off + departure occupancy]
    ARR: [landing - arrival occupancy, landing]
    """
    if flight.operation == "DEP":
        return RunwayWindow(
            start=flight.scheduled,
            end=flight.scheduled + timedelta(seconds=cfg.dep_occupy),
        )
    return RunwayWindow(
        start=flight.scheduled - timedelta(seconds=cfg.arr_occupy),
        end=flight.scheduled,
    )


def taxi_windows(flight: FlightInput) -> list[TaxiWindow]:
    """Occupancy window of every taxiway node along the route.

    The total route time is split evenly across segments. A departure is on
    the route *before* its scheduled time, an arrival *after* it.
    """
    route = flight.route
    span = _span(route)
    if span == 0:
        return []

    total = flight.eta_to_runway if flight.operation == "DEP" else flight.vacate_to_gate
    if total <= 0:
        return []
    seg = total / span

    windows: list[TaxiWindow] = []
    for i, node in enumerate(route):
        if flight.operation == "DEP":
            seg_start = flight.scheduled - timedelta(seconds=total - i * seg)
        else:
            seg_start = flight.scheduled + timedelta(seconds=i * seg)
        windows.append(
            TaxiWindow(
                start=seg_start,
                end=seg_start + timedelta(seconds=seg),
                taxiway=node,
            )
        )
    return windows


def flight_windows(flight: FlightInput, cfg: ConfigInput) -> FlightWindows:
    return FlightWindows(
        flight_id=flight.id,
        runway=flight.runway,
        runway_window=runway_window(flight, cfg),
        taxi_windows=taxi_windows(flight),
    )
