from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.crud.workflow_event import workflow_event as crud_workflow_event
from app.schemas import WorkflowEventCreate, WorkflowEventUpdate, WorkflowEventResponse, WorkflowEventListResponse
from pydantic import BaseModel

router = APIRouter()

class DeleteResponse(BaseModel):
    success: bool = True

@router.post("/", response_model=WorkflowEventResponse, status_code=201)
def create_workflow_event(obj_in: WorkflowEventCreate, db: Session = Depends(get_db)):
    return crud_workflow_event.create(db, obj_in=obj_in)

@router.get("/{id}", response_model=WorkflowEventResponse)
def get_workflow_event(id: int, db: Session = Depends(get_db)):
    db_obj = crud_workflow_event.get(db, event_id=id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Workflow event not found")
    return db_obj

@router.get("/", response_model=WorkflowEventListResponse)
def list_workflow_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    execution_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    items, total = crud_workflow_event.get_multi(
        db, skip=skip, limit=limit, execution_id=execution_id, status=status, search=search
    )
    return {"count": total, "items": items}

@router.put("/{id}", response_model=WorkflowEventResponse)
def update_workflow_event(id: int, obj_in: WorkflowEventUpdate, db: Session = Depends(get_db)):
    db_obj = crud_workflow_event.get(db, event_id=id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Workflow event not found")
    return crud_workflow_event.update(db, db_obj=db_obj, obj_in=obj_in)

@router.delete("/{id}", response_model=DeleteResponse)
def delete_workflow_event(id: int, db: Session = Depends(get_db)):
    db_obj = crud_workflow_event.get(db, event_id=id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Workflow event not found")
    crud_workflow_event.remove(db, event_id=id)
    return {"success": True}
