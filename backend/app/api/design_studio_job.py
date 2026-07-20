"""
api/design_studio_job.py

AI HOME WIMLOGIC -- Design Studio -- V1.1D Design Job
Enterprise API Router (Stage A / B / C / D - Checkpoint 6 + 7 + 8)

Mounted at /api/v1/design-studio/jobs per the approved Decision 3
namespace.

Architecture Compliance
-------------------------
Routers contain HTTP only. All business logic and validation is
delegated to app.services.design_job_service (Stages A-C) and
app.services.design_job_execution_service (Stage D - Checkpoint 8:
execute/retry/executions). This file performs no direct CRUD/model
access.

Scope boundary (locked): this router implements CREATE, CONFIGURE
(Checkpoint 6), SUBMIT (Checkpoint 7 - freezes business intent, does NOT
touch WACP), and EXECUTE/RETRY/execution history (Checkpoint 8 - creates
runtime Workflow Execution attempts and submits the already-frozen
payload through the existing WACP seam). /submit is deliberately
preserved unchanged and is NOT overloaded to also execute - "submit" =
freeze business intent, "execute"/"retry" = start a runtime attempt.
Result ingestion, Design Image Versions, Image Lineage, and Approved
Design Baselines remain out of scope for later checkpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import (
    DesignJobCreate,
    DesignJobResponse,
    DesignJobListResponse,
    DesignJobConfigureImagesRequest,
    DesignJobConfigureOptionsRequest,
    DesignJobImageRead,
    DesignJobSubmitResponse,
    DesignJobRetryResponse,
    DesignJobExecutionRead,
    DesignJobExecutionListResponse,
)
from app.services.design_job_service import design_job_service, DesignJobNotFoundError, DesignJobValidationError
from app.services.design_job_execution_service import (
    design_job_execution_service,
    DesignJobExecutionNotFoundError,
    DesignJobExecutionValidationError,
    DesignJobExecutionConflictError,
)
from app.services.workflow_execution_service import workflow_execution_service
from app.services import wacp_adapter

router = APIRouter()


@router.post("/", response_model=DesignJobResponse, status_code=201)
def create_design_job(obj_in: DesignJobCreate, db: Session = Depends(get_db)):
    try:
        return design_job_service.create_design_job(db, obj_in)
    except DesignJobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DesignJobValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{job_id}", response_model=DesignJobResponse)
def get_design_job(job_id: int, db: Session = Depends(get_db)):
    db_obj = design_job_service.get_design_job(db, job_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Design Job not found")
    return db_obj


@router.get("/", response_model=DesignJobListResponse)
def list_design_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    property_id: Optional[int] = Query(None),
    project_id: Optional[str] = Query(None),
    tool_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    items, total = design_job_service.list_design_jobs(
        db, skip=skip, limit=limit, property_id=property_id, project_id=project_id, tool_id=tool_id, status=status
    )
    return {"count": total, "items": items}


@router.put("/{job_id}/images", response_model=List[DesignJobImageRead])
def configure_design_job_images(job_id: int, obj_in: DesignJobConfigureImagesRequest, db: Session = Depends(get_db)):
    try:
        result = design_job_service.set_images(db, job_id=job_id, images=obj_in.images)
    except DesignJobValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Design Job not found")
    return result


@router.get("/{job_id}/images", response_model=List[DesignJobImageRead])
def get_design_job_images(job_id: int, db: Session = Depends(get_db)):
    result = design_job_service.get_images(db, job_id=job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Design Job not found")
    items, _ = result
    return items


@router.put("/{job_id}/options", response_model=DesignJobResponse)
def configure_design_job_options(job_id: int, obj_in: DesignJobConfigureOptionsRequest, db: Session = Depends(get_db)):
    try:
        result = design_job_service.set_tool_options(db, job_id=job_id, tool_options=obj_in.tool_options)
    except DesignJobValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Design Job not found")
    return result


@router.post("/{job_id}/submit", response_model=DesignJobResponse)
def submit_design_job(job_id: int, db: Session = Depends(get_db)):
    """
    Checkpoint 7 scope: runs the full SUBMIT-time validation and freeze
    sequence (Tool Image Requirement min/max, required Tool Option
    completeness with default resolution, Tool Knowledge Rule
    application, Effective AI Context assembly, submitted_payload_json
    freeze) and transitions status 'draft' -> 'submitted'. Deliberately
    does NOT create a Workflow Execution, does NOT create a
    cre_design_job_executions row, and does NOT call WACP. Use
    POST /{job_id}/execute (Checkpoint 8) to actually start a runtime
    attempt against this frozen payload. The response model remains
    DesignJobResponse - this endpoint's contract does not change now
    that /execute exists alongside it.
    """
    try:
        result = design_job_service.submit_design_job(db, job_id=job_id)
    except DesignJobValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Design Job not found")
    return result


def _build_attempt_response(db: Session, job_id: int, attempt) -> dict:
    """
    Composes the DesignJobSubmitResponse/DesignJobRetryResponse shape
    from a DesignJobExecution row plus its associated Workflow Execution
    (for status and devtools_execution_id) - both schemas were approved
    in Checkpoint 2 with exactly these joined fields.
    """
    wf_exec = workflow_execution_service.get_execution(db, attempt.workflow_execution_id)
    return {
        "design_job_id": job_id,
        "attempt_number": attempt.attempt_number,
        "workflow_execution_id": attempt.workflow_execution_id,
        "devtools_execution_id": wf_exec.devtools_execution_id if wf_exec else None,
        "status": wf_exec.status if wf_exec else "Pending",
    }


@router.post("/{job_id}/execute", response_model=DesignJobSubmitResponse)
def execute_design_job(job_id: int, db: Session = Depends(get_db)):
    """
    Checkpoint 8. Creates the FIRST Workflow Execution attempt for an
    already-submitted, frozen Design Job and submits the exact frozen
    submitted_payload_json through the existing WACP seam. Never rebuilds
    that payload. See design_job_execution_service.execute_submitted_job()
    for the full two-phase attempt architecture.
    """
    try:
        attempt = design_job_execution_service.execute_submitted_job(db, job_id=job_id)
    except DesignJobExecutionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DesignJobExecutionValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DesignJobExecutionConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except wacp_adapter.DevToolsClientError as e:
        # The local Workflow Execution and Design Job Execution attempt
        # rows are already committed and preserved (Phase 1 completed
        # before this Phase 2 network call) - only the outbound WACP
        # dispatch itself failed. 502 reflects an upstream/external
        # service failure, distinct from a caller/business-rule error.
        raise HTTPException(status_code=502, detail=f"Design Job {job_id} attempt was created but WACP dispatch failed: {str(e)}")
    return _build_attempt_response(db, job_id, attempt)


@router.post("/{job_id}/retry", response_model=DesignJobRetryResponse)
def retry_design_job(job_id: int, db: Session = Depends(get_db)):
    """
    Checkpoint 8. Creates a NEW Workflow Execution attempt for the SAME
    Design Job, reusing the exact same frozen submitted_payload_json.
    Retry-eligible only when the current attempt's Workflow Execution
    status is 'Failed' - see
    design_job_execution_service.retry_design_job() for the full
    source-verified eligibility rule and the two-phase attempt
    architecture.
    """
    try:
        attempt = design_job_execution_service.retry_design_job(db, job_id=job_id)
    except DesignJobExecutionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DesignJobExecutionValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DesignJobExecutionConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except wacp_adapter.DevToolsClientError as e:
        raise HTTPException(status_code=502, detail=f"Design Job {job_id} retry attempt was created but WACP dispatch failed: {str(e)}")
    return _build_attempt_response(db, job_id, attempt)


@router.get("/{job_id}/executions", response_model=DesignJobExecutionListResponse)
def get_design_job_executions(job_id: int, db: Session = Depends(get_db)):
    """
    Checkpoint 8. Returns the Design Job's attempt bookkeeping history
    (attempt_number ascending). Pure bookkeeping - runtime status detail
    lives on cre_workflow_executions, not duplicated here.
    """
    result = design_job_execution_service.get_executions(db, job_id=job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Design Job not found")
    items, total = result
    return {"count": total, "items": items}
