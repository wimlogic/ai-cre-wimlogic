from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.crud.scan_job import scan_job as crud_scan_job
from app.schemas import ScanJobCreate, ScanJobUpdate, ScanJobResponse, ScanJobListResponse
from pydantic import BaseModel

router = APIRouter()

class DeleteResponse(BaseModel):
    success: bool = True

@router.post("/", response_model=ScanJobResponse, status_code=201)
def create_scan_job(obj_in: ScanJobCreate, db: Session = Depends(get_db)):
    if obj_in.scan_id:
        existing = crud_scan_job.get_by_scan_id(db, obj_in.scan_id)
        if existing:
            raise HTTPException(status_code=400, detail=f"Scan job with scan_id '{obj_in.scan_id}' already exists")
    return crud_scan_job.create(db, obj_in=obj_in)

@router.get("/{id}", response_model=ScanJobResponse)
def get_scan_job(id: int, db: Session = Depends(get_db)):
    db_obj = crud_scan_job.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return db_obj

@router.get("/by-scan-id/{scan_id}", response_model=ScanJobResponse)
def get_scan_job_by_scan_id(scan_id: str, db: Session = Depends(get_db)):
    db_obj = crud_scan_job.get_by_scan_id(db, scan_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail=f"Scan job with scan ID '{scan_id}' not found")
    return db_obj

@router.get("/", response_model=ScanJobListResponse)
def list_scan_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    items, total = crud_scan_job.get_multi(
        db, skip=skip, limit=limit, project_id=project_id, status=status, search=search
    )
    return {"count": total, "items": items}

@router.put("/{id}", response_model=ScanJobResponse)
def update_scan_job(id: int, obj_in: ScanJobUpdate, db: Session = Depends(get_db)):
    db_obj = crud_scan_job.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Scan job not found")
    if obj_in.scan_id and obj_in.scan_id != db_obj.scan_id:
        existing = crud_scan_job.get_by_scan_id(db, obj_in.scan_id)
        if existing:
            raise HTTPException(status_code=400, detail=f"Scan job with scan_id '{obj_in.scan_id}' already exists")
    return crud_scan_job.update(db, db_obj=db_obj, obj_in=obj_in)

@router.delete("/{id}", response_model=DeleteResponse)
def delete_scan_job(id: int, db: Session = Depends(get_db)):
    db_obj = crud_scan_job.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Scan job not found")
    crud_scan_job.remove(db, id=id)
    return {"success": True}
