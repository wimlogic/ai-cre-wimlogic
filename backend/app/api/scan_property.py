from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.crud.scan_property import scan_property as crud_scan_property
from app.schemas import ScanPropertyCreate, ScanPropertyUpdate, ScanPropertyResponse, ScanPropertyListResponse
from pydantic import BaseModel

router = APIRouter()

class DeleteResponse(BaseModel):
    success: bool = True

@router.post("/", response_model=ScanPropertyResponse, status_code=201)
def create_scan_property(obj_in: ScanPropertyCreate, db: Session = Depends(get_db)):
    return crud_scan_property.create(db, obj_in=obj_in)

@router.get("/{id}", response_model=ScanPropertyResponse)
def get_scan_property(id: int, db: Session = Depends(get_db)):
    db_obj = crud_scan_property.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Scan-property association not found")
    return db_obj

@router.get("/", response_model=ScanPropertyListResponse)
def list_scan_properties(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    scan_id: Optional[int] = Query(None),
    property_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    items, total = crud_scan_property.get_multi(
        db, skip=skip, limit=limit, scan_id=scan_id, property_id=property_id
    )
    return {"count": total, "items": items}

@router.put("/{id}", response_model=ScanPropertyResponse)
def update_scan_property(id: int, obj_in: ScanPropertyUpdate, db: Session = Depends(get_db)):
    db_obj = crud_scan_property.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Scan-property association not found")
    return crud_scan_property.update(db, db_obj=db_obj, obj_in=obj_in)

@router.delete("/{id}", response_model=DeleteResponse)
def delete_scan_property(id: int, db: Session = Depends(get_db)):
    db_obj = crud_scan_property.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Scan-property association not found")
    crud_scan_property.remove(db, id=id)
    return {"success": True}
