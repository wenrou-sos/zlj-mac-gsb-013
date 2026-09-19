from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import engine
from ..database import get_db
from ..models import Flight, Runway, RunwayClosure, SeparationRule
from ..schemas import AnalyzeResponse, AutoResolveResponse, SeparationIn, SeparationOut
from ..serializers import closure_to_dict, flight_to_dict, runway_to_dict

router = APIRouter(prefix="/api", tags=["simulation"])

DEFAULT_MATRIX = {
    "departure": {"departure": 120, "arrival": 90},
    "arrival": {"departure": 90, "arrival": 100},
}
MATRIX_ID = "default"


def _load_snapshot(db: Session) -> tuple[list[dict], list[dict], dict, list[dict]]:
    flights = [flight_to_dict(f) for f in db.query(Flight).all()]
    closures = [closure_to_dict(c) for c in db.query(RunwayClosure).all()]
    runways = [runway_to_dict(r) for r in db.query(Runway).all()]
    rule = db.get(SeparationRule, MATRIX_ID)
    matrix = rule.matrix if rule else DEFAULT_MATRIX
    return flights, closures, matrix, runways


@router.get("/separation", response_model=SeparationOut)
def get_separation(db: Session = Depends(get_db)):
    rule = db.get(SeparationRule, MATRIX_ID)
    return {"matrix": rule.matrix if rule else DEFAULT_MATRIX}


@router.put("/separation", response_model=SeparationOut)
def update_separation(payload: SeparationIn, db: Session = Depends(get_db)):
    rule = db.get(SeparationRule, MATRIX_ID)
    if rule:
        rule.matrix = payload.matrix
    else:
        rule = SeparationRule(id=MATRIX_ID, matrix=payload.matrix)
        db.add(rule)
    db.commit()
    return {"matrix": rule.matrix}


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(db: Session = Depends(get_db)):
    flights, closures, matrix, runways = _load_snapshot(db)
    conflicts = engine.detect_conflicts(flights, closures, matrix)
    resolutions = engine.suggest_resolutions(
        flights, closures, matrix, runways
    )
    return {"conflicts": conflicts, "resolutions": resolutions}


@router.post("/auto-resolve", response_model=AutoResolveResponse)
def auto_resolve(db: Session = Depends(get_db)):
    flights, closures, matrix, _ = _load_snapshot(db)
    return engine.auto_resolve(flights, closures, matrix)
