"""
api/design_studio_image_version.py

AIHOME Phase 1 (Phase D) -- Design Image Version read API.

Mounted at /api/v1/design-studio/image-versions per the approved Design
Studio namespace (matching design_studio_job.py/design_studio_tool.py).

Architecture Compliance
-------------------------
Routers contain HTTP only. All business logic is delegated to
app.services.design_result_service and app.crud.design_image_version -
this file performs no direct model access beyond what FastAPI/Pydantic
already provides through response_model serialization.

Scope: read-only for this phase. Versions are created exclusively by
workflow result ingestion (design_result_service.create_design_image_version),
not by any endpoint here - matches the "no public Create schema exists"
note already documented on DesignImageVersionRead and the CRUD layer.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import DesignImageVersionResponse, DesignImageVersionListResponse
from app.crud.design_image_version import design_image_version as crud_design_image_version
from app.services.design_result_service import list_versions_for_property_image

router = APIRouter()


@router.get("/{version_id}", response_model=DesignImageVersionResponse)
def get_design_image_version(version_id: int, db: Session = Depends(get_db)):
    db_obj = crud_design_image_version.get(db, version_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Design Image Version not found")
    return db_obj


@router.get("/", response_model=DesignImageVersionListResponse)
def list_design_image_versions(
    property_image_id: Optional[int] = Query(
        None,
        description="Return every version whose lineage traces back to this Property Image "
                    "(via cre_design_image_lineage) - the primary Phase D 'Versions' tab query.",
    ),
    design_job_id: Optional[int] = Query(None),
    property_id: Optional[int] = Query(None),
    workflow_execution_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    if property_image_id is not None:
        # Lineage-based lookup - a single Property Image's own version
        # history, not one of the existing single-column CRUD filters.
        items = list_versions_for_property_image(db, property_image_id=property_image_id)
        return {"count": len(items), "items": items[skip: skip + limit]}

    items, total = crud_design_image_version.get_multi(
        db,
        skip=skip,
        limit=limit,
        design_job_id=design_job_id,
        property_id=property_id,
        workflow_execution_id=workflow_execution_id,
        status=status,
    )
    return {"count": total, "items": items}
