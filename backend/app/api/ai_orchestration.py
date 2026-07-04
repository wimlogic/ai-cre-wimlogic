from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.db.session import get_db
from app.services.ai_orchestration_service import ai_orchestration_service
from app.schemas import WorkflowExecutionResponse
from pydantic import BaseModel

router = APIRouter()

class WorkflowSubmitRequest(BaseModel):
    project_id: int
    property_id: int
    workflow_code: str
    scenario_id: Optional[int] = None
    priority: Optional[str] = "Normal"
    metadata_json: Optional[Dict[str, Any]] = None

class WorkflowStatusResponse(BaseModel):
    execution_id: int
    status: str

class WorkflowCallbackRequest(BaseModel):
    devtools_execution_id: str
    status: str
    payload: Dict[str, Any]

@router.post("/submit", response_model=WorkflowExecutionResponse, status_code=202)
def submit_workflow(
    request: WorkflowSubmitRequest,
    db: Session = Depends(get_db)
):
    """
    Triggers an enterprise AI property analysis workflow through the WIMLOGIC orchestrator.
    Initializes tracking logs and transitions state to pending.
    """
    try:
        return ai_orchestration_service.submit_workflow(
            db,
            project_id=request.project_id,
            property_id=request.property_id,
            workflow_code=request.workflow_code,
            scenario_id=request.scenario_id,
            priority=request.priority,
            metadata_json=request.metadata_json
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error submitting workflow: {str(e)}")

@router.get("/status/{execution_id}", response_model=WorkflowStatusResponse)
def check_workflow_status(
    execution_id: int,
    db: Session = Depends(get_db)
):
    """
    Queries current active execution status from WIMLOGIC and synchronizes local records.
    """
    try:
        status_str = ai_orchestration_service.check_workflow_status(db, execution_id=execution_id)
        return {"execution_id": execution_id, "status": status_str}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error polling workflow: {str(e)}")

@router.post("/callback", response_model=WorkflowExecutionResponse)
def receive_workflow_callback(
    request: WorkflowCallbackRequest,
    db: Session = Depends(get_db)
):
    """
    Asynchronous webhook endpoint registered with the external WIMLOGIC AI Orchestrator.
    Processes output payloads, updates timelines, and hydrates reports/assets.
    """
    try:
        return ai_orchestration_service.receive_workflow_callback(
            db,
            devtools_execution_id=request.devtools_execution_id,
            status=request.status,
            payload=request.payload
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error processing callback: {str(e)}")
