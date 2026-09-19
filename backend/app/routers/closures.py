from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/closures", tags=["closures"])


@router.get("", response_model=list[schemas.ClosureOut])
def list_closures(db: Session = Depends(get_db)):
    return (db.query(models.RunwayClosure)
            .order_by(models.RunwayClosure.start).all())


@router.post("", response_model=schemas.ClosureOut, status_code=201)
def create_closure(payload: schemas.ClosureCreate, db: Session = Depends(get_db)):
    if payload.end <= payload.start:
        raise HTTPException(422, "关闭结束时间必须晚于开始时间")
    closure = models.RunwayClosure(**payload.model_dump())
    db.add(closure)
    db.commit()
    db.refresh(closure)
    return closure


@router.put("/{closure_id}", response_model=schemas.ClosureOut)
def update_closure(closure_id: int, payload: schemas.ClosureUpdate,
                   db: Session = Depends(get_db)):
    closure = db.get(models.RunwayClosure, closure_id)
    if closure is None:
        raise HTTPException(404, f"关闭区间 {closure_id} 不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(closure, k, v)
    if closure.end <= closure.start:
        raise HTTPException(422, "关闭结束时间必须晚于开始时间")
    db.commit()
    db.refresh(closure)
    return closure


@router.delete("/{closure_id}", status_code=204)
def delete_closure(closure_id: int, db: Session = Depends(get_db)):
    closure = db.get(models.RunwayClosure, closure_id)
    if closure is None:
        raise HTTPException(404, f"关闭区间 {closure_id} 不存在")
    db.delete(closure)
    db.commit()
