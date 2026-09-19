from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas, service
from ..database import get_db

router = APIRouter(prefix="/api/rehearse", tags=["rehearsal"])


@router.get("", response_model=schemas.RehearsalOut)
def rehearse(db: Session = Depends(get_db)):
    """Run conflict detection against the current schedule."""
    return service.rehearsal_payload(db)


@router.post("/adjust", response_model=schemas.RehearsalOut)
def adjust(req: schemas.AdjustRequest, db: Session = Depends(get_db)):
    """Apply a single suggested adjustment and re-run detection."""
    try:
        return service.apply_adjustment(db, req)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.post("/auto-resolve", response_model=schemas.AutoResolveOut)
def auto_resolve_route(db: Session = Depends(get_db)):
    """Automatically delay flights to clear all resolvable conflicts."""
    return service.apply_auto_resolve(db)


@router.post("/reset-demo")
def reset_demo(db: Session = Depends(get_db)):
    """Reset the database to the built-in demonstration scenario."""
    from ..seed import seed_database

    seed_database(db, wipe=True)
    return {"status": "ok", **service.rehearsal_payload(db)}
