from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Flight(Base):
    __tablename__ = "flights"

    id = Column(Integer, primary_key=True, index=True)
    callsign = Column(String(16), nullable=False, index=True)
    operation = Column(String(4), nullable=False)  # 'ARR' | 'DEP'
    runway = Column(String(8), nullable=False)
    wake = Column(String(8), nullable=False, default="M")  # L | M | H
    scheduled = Column(DateTime, nullable=False)  # landing time (ARR) or take-off time (DEP)
    route = Column(JSON, nullable=False, default=list)  # ordered list of taxiway node names
    eta_to_runway = Column(Integer, nullable=False, default=300)  # DEP: route seconds
    vacate_to_gate = Column(Integer, nullable=False, default=240)  # ARR: route seconds
    stand = Column(String(16), nullable=True)
    note = Column(Text, nullable=True)


class RunwayClosure(Base):
    __tablename__ = "runway_closures"

    id = Column(Integer, primary_key=True, index=True)
    runway = Column(String(8), nullable=False, index=True)
    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=False)
    reason = Column(Text, nullable=True)


class AppConfig(Base):
    __tablename__ = "app_config"

    id = Column(Integer, primary_key=True, default=1)
    runways = Column(JSON, nullable=False, default=list)  # available runway ids
    dep_occupy = Column(Integer, nullable=False, default=60)  # departure runway occupancy [s]
    arr_occupy = Column(Integer, nullable=False, default=50)  # arrival runway occupancy [s]
    min_sep = Column(Integer, nullable=False, default=30)  # baseline runway separation [s]
    max_delay = Column(Integer, nullable=False, default=1800)  # max acceptable auto delay [s]
    wake_sep = Column(JSON, nullable=False, default=dict)  # extra seconds: f"{leader}{follower}"
