from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Flight
from ..schemas import FlightIn, FlightOut
from ..serializers import flight_to_dict

router = APIRouter(prefix="/api/flights", tags=["flights"])


@router.get("", response_model=list[FlightOut])
def list_flights(db: Session = Depends(get_db)):
    return [flight_to_dict(f) for f in db.query(Flight).order_by(Flight.id).all()]


@router.post("", response_model=FlightOut)
def create_flight(payload: FlightIn, db: Session = Depends(get_db)):
    if db.get(Flight, payload.id):
        raise HTTPException(409, f"航班 {payload.id} 已存在")
    flight = Flight(
        **{**payload.model_dump(), "route": [s.model_dump() for s in payload.route]}
    )
    db.add(flight)
    db.commit()
    return flight_to_dict(flight)


@router.get("/{flight_id}", response_model=FlightOut)
def get_flight(flight_id: str, db: Session = Depends(get_db)):
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(404, "航班不存在")
    return flight_to_dict(flight)


@router.put("/{flight_id}", response_model=FlightOut)
def update_flight(flight_id: str, payload: FlightIn, db: Session = Depends(get_db)):
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(404, "航班不存在")
    data = payload.model_dump()
    data["route"] = [s.model_dump() for s in payload.route]
    for k, v in data.items():
        setattr(flight, k, v)
    db.commit()
    return flight_to_dict(flight)


@router.delete("/{flight_id}", status_code=204)
def delete_flight(flight_id: str, db: Session = Depends(get_db)):
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(404, "航班不存在")
    db.delete(flight)
    db.commit()


@router.post("/reset", status_code=204)
def reset_flights(db: Session = Depends(get_db)):
    """清空航班（用于恢复演示场景）。"""
    db.query(Flight).delete()
    db.commit()
