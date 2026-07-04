from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.services.workflow_result_service import workflow_result_service
from app.schemas import (
    WorkflowResultCreate, WorkflowResultUpdate, WorkflowResultResponse, WorkflowResultListResponse,
    ResultSectionResponse, ResultSectionListResponse, ResultSectionCreate,
    PropertyAnalysisReportResponse, PropertyAnalysisReportListResponse, PropertyAnalysisReportCreate
)
from pydantic import BaseModel

router = APIRouter()

class DeleteResponse(BaseModel):
    success: bool = True

@router.post("/", response_model=WorkflowResultResponse, status_code=201)
def create_workflow_result(obj_in: WorkflowResultCreate, db: Session = Depends(get_db)):
    return workflow_result_service.create_result(db, result_in=obj_in)

@router.get("/{id}", response_model=WorkflowResultResponse)
def get_workflow_result(id: int, db: Session = Depends(get_db)):
    db_obj = workflow_result_service.get_result(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Workflow result not found")
    return db_obj

@router.get("/", response_model=WorkflowResultListResponse)
def list_workflow_results(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    execution_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    items, total = workflow_result_service.get_results(
        db, skip=skip, limit=limit, execution_id=execution_id, search=search
    )
    return {"count": total, "items": items}

@router.put("/{id}", response_model=WorkflowResultResponse)
def update_workflow_result(id: int, obj_in: WorkflowResultUpdate, db: Session = Depends(get_db)):
    db_obj = workflow_result_service.get_result(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Workflow result not found")
    return workflow_result_service.update_result(db, result_id=id, result_in=obj_in)

@router.delete("/{id}", response_model=DeleteResponse)
def delete_workflow_result(id: int, db: Session = Depends(get_db)):
    db_obj = workflow_result_service.get_result(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Workflow result not found")
    workflow_result_service.delete_result(db, result_id=id)
    return {"success": True}

# Parsed result sections sub-resource
@router.get("/{id}/sections", response_model=ResultSectionListResponse)
def list_workflow_result_sections(
    id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    section_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    db_obj = workflow_result_service.get_result(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Workflow result not found")
    items, total = workflow_result_service.get_sections(
        db, skip=skip, limit=limit, result_id=id, section_type=section_type, search=search
    )
    return {"count": total, "items": items}

@router.post("/{id}/sections", response_model=ResultSectionResponse, status_code=201)
def create_workflow_result_section(
    id: int,
    obj_in: ResultSectionCreate,
    db: Session = Depends(get_db)
):
    db_obj = workflow_result_service.get_result(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Workflow result not found")
    # Force result ID match
    obj_in.result_id = id
    return workflow_result_service.create_section(db, section_in=obj_in)
