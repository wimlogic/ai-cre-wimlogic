"""
api/property_image.py

AI-CRE WIMLOGIC V1.0A -- Enterprise API Router
Phase 3A -- Enterprise Image Upload & Workflow Integration

Purpose
-------
HTTP router for the Property Images business resource.

This file EXTENDS the existing, already-approved property_image router.
The original endpoints (create/get/list/update/delete metadata rows) are
preserved verbatim and unchanged below. This revision ADDS the remaining
required capabilities on top of them:

    - Single file upload            (multipart/form-data)
    - Multi file / batch upload     (multipart/form-data)
    - URL import
    - Delete Image                  (already existed -- unchanged)
    - List Images by Property       (already existed -- unchanged,
                                      property_id is an existing filter
                                      on GET /)
    - Update Image Metadata         (already existed -- unchanged)
    - Get Image Details             (already existed -- unchanged)

Architecture Compliance
-------------------------
Routers contain HTTP only. This file performs NO business logic:
    - No filesystem access.
    - No thumbnail generation.
    - No validation beyond what FastAPI/Pydantic performs on the wire.
    - No SQL, no CRUD calls, no direct model access.

All business logic is delegated to the existing, approved service layer:
    - app.services.property_image_service      (existing CRUD wrapper,
      unchanged, used for metadata-only create/get/list/update/delete)
    - app.services.property_image_upload_service (Phase 3A, approved)
    - app.services.property_image_import_service  (Phase 3A, approved)

No new CRUD module is introduced. No existing endpoint, schema, or
service is renamed or duplicated.

Multipart Handling Note
--------------------------
PropertyImageUploadService and PropertyImageImportService are
intentionally framework-agnostic (they accept a plain
`UploadFileInput` dataclass, not `fastapi.UploadFile`). Translating an
incoming multipart request into that dataclass is exactly the kind of
"HTTP only" adaptation that belongs in the router, so it is performed
here -- reading bytes from the uploaded file and constructing
`UploadFileInput` involves no business rules of its own.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.storage.filesystem_storage_provider import StorageError
from app.schemas import (
    PropertyImageCreate,
    PropertyImageListResponse,
    PropertyImageResponse,
    PropertyImageUpdate,
)
from app.services.property_image_import_service import (
    ImageImportError,
    property_image_import_service,
)
from app.services.property_image_service import property_image_service
from app.services.property_image_upload_service import (
    UploadFileInput,
    property_image_upload_service,
)

router = APIRouter()


class DeleteResponse(BaseModel):
    success: bool = True


# ---------------------------------------------------------------------------
# Existing endpoints (unchanged, preserved verbatim from the approved router)
# ---------------------------------------------------------------------------

@router.post("/", response_model=PropertyImageResponse, status_code=201)
def create_property_image(obj_in: PropertyImageCreate, db: Session = Depends(get_db)):
    return property_image_service.create_image(db, image_in=obj_in)

@router.get("/{id}", response_model=PropertyImageResponse)
def get_property_image(id: int, db: Session = Depends(get_db)):
    db_obj = property_image_service.get_image(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Property image not found")
    return db_obj

@router.get("/", response_model=PropertyImageListResponse)
def list_property_images(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    property_id: Optional[int] = Query(None),
    project_id: Optional[str] = Query(None),
    image_type: Optional[str] = Query(None),
    include_deleted: bool = Query(False),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    items, total = property_image_service.get_images(
        db,
        skip=skip,
        limit=limit,
        property_id=property_id,
        project_id=project_id,
        image_type=image_type,
        include_deleted=include_deleted,
        search=search
    )
    return {"count": total, "items": items}

@router.put("/{id}", response_model=PropertyImageResponse)
def update_property_image(id: int, obj_in: PropertyImageUpdate, db: Session = Depends(get_db)):
    db_obj = property_image_service.get_image(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Property image not found")
    return property_image_service.update_image(db, id=id, image_in=obj_in)

@router.delete("/{id}", response_model=DeleteResponse)
def delete_property_image(id: int, soft: bool = Query(True), db: Session = Depends(get_db)):
    db_obj = property_image_service.get_image(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Property image not found")
    property_image_service.delete_image(db, id=id, soft=soft)
    return {"success": True}


# ---------------------------------------------------------------------------
# NEW: Upload & Import endpoints (Phase 3A)
# ---------------------------------------------------------------------------

class BatchUploadResultItem(BaseModel):
    """Outcome for a single file within a multi-file upload response."""

    filename: str
    success: bool
    property_image: Optional[PropertyImageResponse] = None
    error: Optional[str] = None


class BatchUploadResponse(BaseModel):
    """
    HTTP response wrapper for a multi-file / drag & drop upload request.
    Mirrors app.services.property_image_upload_service.BatchUploadSummary.
    Defined here (not in schemas/) because it is a response contract for
    this custom, non-CRUD endpoint rather than a persisted business
    entity -- consistent with the existing pattern in
    api/ai_orchestration.py (e.g. WorkflowStatusResponse).
    """

    property_id: int
    total: int
    succeeded: int
    failed: int
    results: List[BatchUploadResultItem]


class ImageUrlImportRequest(BaseModel):
    """Request body for importing a single property image from a URL."""

    property_id: int
    image_url: str
    project_id: Optional[str] = None
    image_role: Optional[str] = None
    notes: Optional[str] = None


@router.post("/upload", response_model=PropertyImageResponse, status_code=201)
async def upload_property_image(
    property_id: int = Form(...),
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    image_role: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload a single image file for a property (standard file picker or
    single drag & drop). Delegates entirely to
    PropertyImageUploadService.upload_single().
    """
    content = await file.read()
    file_input = UploadFileInput(
        filename=file.filename or "upload",
        content=content,
        content_type=file.content_type,
        image_role=image_role,
        notes=notes,
    )
    try:
        return property_image_upload_service.upload_single(
            db, property_id=property_id, file_input=file_input, project_id=project_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except StorageError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error uploading image: {str(e)}")


@router.post("/upload/batch", response_model=BatchUploadResponse, status_code=207)
async def upload_property_images_batch(
    property_id: int = Form(...),
    files: List[UploadFile] = File(...),
    project_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload multiple image files for a property in one request (multi-select
    or drag & drop of several files). Delegates entirely to
    PropertyImageUploadService.upload_multiple(), which supports partial
    success: individual files may fail validation while others succeed.

    Returns HTTP 207 (Multi-Status) since the response body itself
    reports a per-file success/failure breakdown rather than a single
    pass/fail outcome.
    """
    file_inputs: List[UploadFileInput] = []
    for uploaded_file in files:
        content = await uploaded_file.read()
        file_inputs.append(
            UploadFileInput(
                filename=uploaded_file.filename or "upload",
                content=content,
                content_type=uploaded_file.content_type,
            )
        )

    try:
        summary = property_image_upload_service.upload_multiple(
            db, property_id=property_id, file_inputs=file_inputs, project_id=project_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error uploading images: {str(e)}")

    return BatchUploadResponse(
        property_id=summary.property_id,
        total=summary.total,
        succeeded=summary.succeeded,
        failed=summary.failed,
        results=[
            BatchUploadResultItem(
                filename=r.filename,
                success=r.success,
                property_image=r.property_image,
                error=r.error,
            )
            for r in summary.results
        ],
    )


@router.post("/import-url", response_model=PropertyImageResponse, status_code=201)
def import_property_image_from_url(
    request: ImageUrlImportRequest,
    db: Session = Depends(get_db),
):
    """
    Import a single image by downloading it from an external HTTP/HTTPS
    URL. Delegates entirely to PropertyImageImportService.import_from_url(),
    which internally reuses PropertyImageUploadService for validation,
    storage, thumbnailing, persistence, and rollback.
    """
    try:
        return property_image_import_service.import_from_url(
            db,
            property_id=request.property_id,
            image_url=request.image_url,
            project_id=request.project_id,
            image_role=request.image_role,
            notes=request.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (ImageImportError, StorageError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error importing image: {str(e)}")
