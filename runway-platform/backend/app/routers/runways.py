from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Runway
from ..schemas import RunwayIn, RunwayOut
from ..serializers import runway_to_dict

router = APIRouter(prefix="/api/runways", tags=["runways"])


@router.get("", response_model=list[RunwayOut])
def list_runways(db: Session = Depends(get_db)):
    return [runway_to_dict(r) for r in db.query(Runway).order_by(Runway.id).all()]


@router.post("", response_model=RunwayOut)
def create_runway(payload: RunwayIn, db: Session = Depends(get_db)):
    if db.get(Runway, payload.id):
        raise HTTPException(409, f"跑道 {payload.id} 已存在")
    runway = Runway(**payload.model_dump())
    db.add(runway)
    db.commit()
    return runway_to_dict(runway)


@router.put("/{runway_id}", response_model=RunwayOut)
def update_runway(runway_id: str, payload: RunwayIn, db: Session = Depends(get_db)):
    runway = db.get(Runway, runway_id)
    if not runway:
        raise HTTPException(404, "跑道不存在")
    for k, v in payload.model_dump().items():
        setattr(runway, k, v)
    db.commit()
    return runway_to_dict(runway)


@router.delete("/{runway_id}", status_code=204)
def delete_runway(runway_id: str, db: Session = Depends(get_db)):
    runway = db.get(Runway, runway_id)
    if not runway:
        raise HTTPException(404, "跑道不存在")
    db.delete(runway)
    db.commit()
