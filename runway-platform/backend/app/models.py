from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String

from .database import Base


class Runway(Base):
    __tablename__ = "runways"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    active = Column(Boolean, default=True)


class Flight(Base):
    __tablename__ = "flights"

    id = Column(String, primary_key=True)
    callsign = Column(String, nullable=False)
    operation = Column(String, nullable=False)  # arrival | departure
    runway_id = Column(String, nullable=False)
    scheduled_time = Column(DateTime(timezone=True))
    takeoff_time = Column(DateTime(timezone=True))
    landing_time = Column(DateTime(timezone=True))
    enter_offset = Column(Integer, default=60)
    vacate_offset = Column(Integer, default=40)
    route = Column(JSON, default=list)
    aircraft_category = Column(String, default="M")


class RunwayClosure(Base):
    __tablename__ = "runway_closures"

    id = Column(String, primary_key=True)
    runway_id = Column(String, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    reason = Column(String, default="")


class SeparationRule(Base):
    """安全间隔矩阵（秒），以 leader_operation/follower_operation 为键。"""

    __tablename__ = "separation_rules"

    id = Column(String, primary_key=True)
    matrix = Column(JSON, nullable=False)
