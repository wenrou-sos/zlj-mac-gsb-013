from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas, service
from ..database import get_db

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
def get_config(db: Session = Depends(get_db)):
    service.ensure_config(db)
    row = db.get(models.AppConfig, 1)
    return {
        "runways": row.runways,
        "dep_occupy": row.dep_occupy,
        "arr_occupy": row.arr_occupy,
        "min_sep": row.min_sep,
        "max_delay": row.max_delay,
        "wake_sep": row.wake_sep,
    }


@router.put("", response_model=dict)
def update_config(payload: schemas.ConfigUpdate, db: Session = Depends(get_db)):
    row = service.ensure_config(db)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    return {"status": "ok"}
