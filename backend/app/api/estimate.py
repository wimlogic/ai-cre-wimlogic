from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.crud.estimate import estimate as crud_estimate
from app.schemas import EstimateCreate, EstimateUpdate, EstimateResponse, EstimateListResponse
from pydantic import BaseModel

router = APIRouter()

class DeleteResponse(BaseModel):
    success: bool = True

@router.post("/", response_model=EstimateResponse, status_code=201)
def create_estimate(obj_in: EstimateCreate, db: Session = Depends(get_db)):
    return crud_estimate.create(db, obj_in=obj_in)

@router.get("/{id}", response_model=EstimateResponse)
def get_estimate(id: int, db: Session = Depends(get_db)):
    db_obj = crud_estimate.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return db_obj

@router.get("/", response_model=EstimateListResponse)
def list_estimates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    property_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    items, total = crud_estimate.get_multi(
        db, skip=skip, limit=limit, property_id=property_id, search=search
    )
    return {"count": total, "items": items}

@router.put("/{id}", response_model=EstimateResponse)
def update_estimate(id: int, obj_in: EstimateUpdate, db: Session = Depends(get_db)):
    db_obj = crud_estimate.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return crud_estimate.update(db, db_obj=db_obj, obj_in=obj_in)

@router.delete("/{id}", response_model=DeleteResponse)
def delete_estimate(id: int, db: Session = Depends(get_db)):
    db_obj = crud_estimate.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Estimate not found")
    crud_estimate.remove(db, id=id)
    return {"success": True}
