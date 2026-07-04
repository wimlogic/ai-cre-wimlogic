from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.services.workflow_execution_service import workflow_execution_service
from app.schemas import (
    WorkflowExecutionCreate, WorkflowExecutionUpdate, WorkflowExecutionResponse, WorkflowExecutionListResponse,
    WorkflowEventResponse, WorkflowEventListResponse, WorkflowEventCreate
)
from pydantic import BaseModel

router = APIRouter()

class DeleteResponse(BaseModel):
    success: bool = True

@router.post("/", response_model=WorkflowExecutionResponse, status_code=201)
def create_workflow_execution(obj_in: WorkflowExecutionCreate, db: Session = Depends(get_db)):
    try:
        return workflow_execution_service.create_execution(db, execution_in=obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{id}", response_model=WorkflowExecutionResponse)
def get_workflow_execution(id: int, db: Session = Depends(get_db)):
    db_obj = workflow_execution_service.get_execution(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Workflow execution not found")
    return db_obj

@router.get("/by-number/{execution_number}", response_model=WorkflowExecutionResponse)
def get_workflow_execution_by_number(execution_number: str, db: Session = Depends(get_db)):
    db_obj = workflow_execution_service.get_execution_by_number(db, execution_number)
    if not db_obj:
        raise HTTPException(status_code=404, detail=f"Workflow execution '{execution_number}' not found")
    return db_obj

@router.get("/", response_model=WorkflowExecutionListResponse)
def list_workflow_executions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    project_id: Optional[int] = Query(None),
    property_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    items, total = workflow_execution_service.get_executions(
        db, skip=skip, limit=limit, project_id=project_id, property_id=property_id, status=status, search=search
    )
    return {"count": total, "items": items}

@router.put("/{id}", response_model=WorkflowExecutionResponse)
def update_workflow_execution(id: int, obj_in: WorkflowExecutionUpdate, db: Session = Depends(get_db)):
    db_obj = workflow_execution_service.get_execution(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Workflow execution not found")
    try:
        return workflow_execution_service.update_execution(db, execution_id=id, execution_in=obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", response_model=DeleteResponse)
def delete_workflow_execution(id: int, db: Session = Depends(get_db)):
    db_obj = workflow_execution_service.get_execution(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Workflow execution not found")
    workflow_execution_service.delete_execution(db, execution_id=id)
    return {"success": True}

# Timeline events sub-resource
@router.get("/{id}/events", response_model=WorkflowEventListResponse)
def get_workflow_execution_events(
    id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    db_obj = workflow_execution_service.get_execution(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Workflow execution not found")
    items, total = workflow_execution_service.get_events(db, execution_id=id, skip=skip, limit=limit)
    return {"count": total, "items": items}

@router.post("/{id}/events", response_model=WorkflowEventResponse, status_code=201)
def add_workflow_execution_event(
    id: int,
    obj_in: WorkflowEventCreate,
    db: Session = Depends(get_db)
):
    db_obj = workflow_execution_service.get_execution(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Workflow execution not found")
    return workflow_execution_service.add_event(
        db,
        execution_id=id,
        event_type=obj_in.event_type,
        status=obj_in.status,
        message=obj_in.message
    )
