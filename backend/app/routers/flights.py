from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/flights", tags=["flights"])


@router.get("", response_model=list[schemas.FlightOut])
def list_flights(db: Session = Depends(get_db)):
    return db.query(models.Flight).order_by(models.Flight.scheduled).all()


@router.post("", response_model=schemas.FlightOut, status_code=201)
def create_flight(payload: schemas.FlightCreate, db: Session = Depends(get_db)):
    flight = models.Flight(**payload.model_dump())
    db.add(flight)
    db.commit()
    db.refresh(flight)
    return flight


@router.put("/{flight_id}", response_model=schemas.FlightOut)
def update_flight(flight_id: int, payload: schemas.FlightUpdate,
                  db: Session = Depends(get_db)):
    flight = db.get(models.Flight, flight_id)
    if flight is None:
        raise HTTPException(404, f"航班 {flight_id} 不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(flight, k, v)
    db.commit()
    db.refresh(flight)
    return flight


@router.delete("/{flight_id}", status_code=204)
def delete_flight(flight_id: int, db: Session = Depends(get_db)):
    flight = db.get(models.Flight, flight_id)
    if flight is None:
        raise HTTPException(404, f"航班 {flight_id} 不存在")
    db.delete(flight)
    db.commit()
