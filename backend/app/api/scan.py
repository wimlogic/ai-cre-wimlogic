from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.crud.scan import scan as crud_scan
from app.schemas import ScanCreate, ScanUpdate, ScanResponse, ScanListResponse
from pydantic import BaseModel

router = APIRouter()

class DeleteResponse(BaseModel):
    success: bool = True

@router.post("/", response_model=ScanResponse, status_code=201)
def create_scan(obj_in: ScanCreate, db: Session = Depends(get_db)):
    if obj_in.scan_uid:
        existing = crud_scan.get_by_uid(db, obj_in.scan_uid)
        if existing:
            raise HTTPException(status_code=400, detail=f"Scan with scan_uid '{obj_in.scan_uid}' already exists")
    return crud_scan.create(db, obj_in=obj_in)

@router.get("/{id}", response_model=ScanResponse)
def get_scan(id: int, db: Session = Depends(get_db)):
    db_obj = crud_scan.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Scan not found")
    return db_obj

@router.get("/by-uid/{scan_uid}", response_model=ScanResponse)
def get_scan_by_uid(scan_uid: str, db: Session = Depends(get_db)):
    db_obj = crud_scan.get_by_uid(db, scan_uid)
    if not db_obj:
        raise HTTPException(status_code=404, detail=f"Scan with UID '{scan_uid}' not found")
    return db_obj

@router.get("/", response_model=ScanListResponse)
def list_scans(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    items, total = crud_scan.get_multi(
        db, skip=skip, limit=limit, project_id=project_id, status=status, search=search
    )
    return {"count": total, "items": items}

@router.put("/{id}", response_model=ScanResponse)
def update_scan(id: int, obj_in: ScanUpdate, db: Session = Depends(get_db)):
    db_obj = crud_scan.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Scan not found")
    if obj_in.scan_uid and obj_in.scan_uid != db_obj.scan_uid:
        existing = crud_scan.get_by_uid(db, obj_in.scan_uid)
        if existing:
            raise HTTPException(status_code=400, detail=f"Scan with scan_uid '{obj_in.scan_uid}' already exists")
    return crud_scan.update(db, db_obj=db_obj, obj_in=obj_in)

@router.delete("/{id}", response_model=DeleteResponse)
def delete_scan(id: int, db: Session = Depends(get_db)):
    db_obj = crud_scan.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Scan not found")
    crud_scan.remove(db, id=id)
    return {"success": True}
