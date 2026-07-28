"""
api/design_studio_baseline.py

AIHOME Phase 1 (Phase D) -- Approved Design Baseline read + approve API.

Mounted at /api/v1/design-studio/baselines per the approved Design Studio
namespace.

Architecture Compliance
-------------------------
Routers contain HTTP only. Approval is delegated entirely to
app.services.design_result_service.approve_design_version() (Phase B,
already tested) - this router performs no transaction logic, no locking,
no supersede handling of its own.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import (
    ApprovedDesignBaselineResponse,
    ApprovedDesignBaselineListResponse,
    ApprovedDesignBaselineApproveRequest,
)
from app.crud.approved_design_baseline import approved_design_baseline as crud_approved_design_baseline
from app.services.design_result_service import (
    approve_design_version,
    DesignResultError,
    BaselineApprovalConflictError,
)

router = APIRouter()


@router.get("/{baseline_id}", response_model=ApprovedDesignBaselineResponse)
def get_approved_design_baseline(baseline_id: int, db: Session = Depends(get_db)):
    db_obj = crud_approved_design_baseline.get(db, baseline_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Approved Design Baseline not found")
    return db_obj


@router.get("/", response_model=ApprovedDesignBaselineListResponse)
def list_approved_design_baselines(
    property_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    design_type: Optional[str] = Query(None),
    design_scope: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Backs the Phase D "Currently Active Baseline" display: callers
    typically pass property_id + status="active" to find the one active
    baseline for a property (or filter further by design_type/
    design_scope if a property has baselines for more than one scope).
    """
    items, total = crud_approved_design_baseline.get_multi(
        db, skip=skip, limit=limit, property_id=property_id, status=status,
        design_type=design_type, design_scope=design_scope,
    )
    return {"count": total, "items": items}


@router.post("/approve", response_model=ApprovedDesignBaselineResponse, status_code=201)
def approve_design_image_version(obj_in: ApprovedDesignBaselineApproveRequest, db: Session = Depends(get_db)):
    """
    Promotes a Design Image Version to the active baseline for its scope.
    design_scope on the request is currently ignored (AIHOME Phase 1
    documented temporary behavior - see ApprovedDesignBaselineApproveRequest's
    own docstring): the service derives it server-side from the Design
    Job's primary selected image's image_role.
    """
    try:
        return approve_design_version(db, image_version_id=obj_in.image_version_id, approved_by=None)
    except DesignResultError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BaselineApprovalConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
