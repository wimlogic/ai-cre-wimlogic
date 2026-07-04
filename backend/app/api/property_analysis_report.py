from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.crud.property_analysis_report import property_analysis_report as crud_property_analysis_report
from app.schemas import PropertyAnalysisReportCreate, PropertyAnalysisReportUpdate, PropertyAnalysisReportResponse, PropertyAnalysisReportListResponse
from pydantic import BaseModel

router = APIRouter()

class DeleteResponse(BaseModel):
    success: bool = True

@router.post("/", response_model=PropertyAnalysisReportResponse, status_code=201)
def create_property_analysis_report(obj_in: PropertyAnalysisReportCreate, db: Session = Depends(get_db)):
    return crud_property_analysis_report.create(db, obj_in=obj_in)

@router.get("/{id}", response_model=PropertyAnalysisReportResponse)
def get_property_analysis_report(id: int, db: Session = Depends(get_db)):
    db_obj = crud_property_analysis_report.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Property analysis report not found")
    return db_obj

@router.get("/", response_model=PropertyAnalysisReportListResponse)
def list_property_analysis_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    project_id: Optional[str] = Query(None),
    property_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    items, total = crud_property_analysis_report.get_multi(
        db, skip=skip, limit=limit, project_id=project_id, property_id=property_id, search=search
    )
    return {"count": total, "items": items}

@router.put("/{id}", response_model=PropertyAnalysisReportResponse)
def update_property_analysis_report(id: int, obj_in: PropertyAnalysisReportUpdate, db: Session = Depends(get_db)):
    db_obj = crud_property_analysis_report.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Property analysis report not found")
    return crud_property_analysis_report.update(db, db_obj=db_obj, obj_in=obj_in)

@router.delete("/{id}", response_model=DeleteResponse)
def delete_property_analysis_report(id: int, db: Session = Depends(get_db)):
    db_obj = crud_property_analysis_report.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Property analysis report not found")
    crud_property_analysis_report.remove(db, id=id)
    return {"success": True}
