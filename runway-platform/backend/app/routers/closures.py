from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import RunwayClosure
from ..schemas import ClosureIn, ClosureOut
from ..serializers import closure_to_dict

router = APIRouter(prefix="/api/closures", tags=["closures"])


@router.get("", response_model=list[ClosureOut])
def list_closures(db: Session = Depends(get_db)):
    return [
        closure_to_dict(c)
        for c in db.query(RunwayClosure).order_by(RunwayClosure.start_time).all()
    ]


@router.post("", response_model=ClosureOut)
def create_closure(payload: ClosureIn, db: Session = Depends(get_db)):
    if db.get(RunwayClosure, payload.id):
        raise HTTPException(409, f"关闭区间 {payload.id} 已存在")
    closure = RunwayClosure(**payload.model_dump())
    db.add(closure)
    db.commit()
    return closure_to_dict(closure)


@router.put("/{closure_id}", response_model=ClosureOut)
def update_closure(closure_id: str, payload: ClosureIn, db: Session = Depends(get_db)):
    closure = db.get(RunwayClosure, closure_id)
    if not closure:
        raise HTTPException(404, "关闭区间不存在")
    for k, v in payload.model_dump().items():
        setattr(closure, k, v)
    db.commit()
    return closure_to_dict(closure)


@router.delete("/{closure_id}", status_code=204)
def delete_closure(closure_id: str, db: Session = Depends(get_db)):
    closure = db.get(RunwayClosure, closure_id)
    if not closure:
        raise HTTPException(404, "关闭区间不存在")
    db.delete(closure)
    db.commit()
