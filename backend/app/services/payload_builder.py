"""
AI-CRE WIMLOGIC V1 -- Phase 1A-BE WACP Client SDK Integration

payload_builder.py

Builds the WACP envelope's `data` block content for a single AI request,
assembled from existing AI-CRE data only (Project, Property, Property
Images, notes, business goal, requested deliverables, metadata).

Per 10_WACP_PROTOCOL.md §9, `data` is owned entirely by the Business
Application and is otherwise unconstrained by the protocol - this module
builds exactly that block, nothing more. Everything that used to live in
this module's legacy "header" (app_id, app_version, payload_version,
workflow_intent, priority) is now an envelope-level concern the WACP
Client SDK itself owns (application_id from configuration, workflow_code/
priority/correlation_id passed directly to WacpClient.submit()) - see
services/wacp_adapter.py and services/ai_orchestration_service.py.
This module no longer builds or knows about any envelope field.

This module performs no HTTP calls and no database writes - it only reads
via existing CRUD objects and assembles a plain dict. `wacp_adapter.py`
is responsible for actually sending this data to DEV-TOOLS as the `data`
block of a WACP envelope.

Intentionally reusable by future modules: callers supply whatever business
goal / deliverables / metadata they have, and this module does not assume
a single call site.
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.project import project as crud_project
from app.crud.property import property as crud_property
from app.crud.property_image import property_image as crud_property_image

logger = logging.getLogger(__name__)


class PayloadBuilderError(ValueError):
    """Raised when the payload cannot be built (e.g. missing project/property)."""


def normalize_json_value(value: Any) -> Any:
    """
    Recursively converts a Python value into something `json.dumps()` can
    serialize natively, with no custom encoder required at the call site.

    This is the ONE reusable normalization function for the Enterprise
    Payload contract - payload_builder.py is the single place responsible
    for turning Python business objects into JSON-safe values. Every future
    WIMLOGIC application (AI-CRE, AI-ECOM, AI-HR, ...) reusing this
    contract should reuse this function rather than writing its own.

    Supported conversions:
        Decimal             -> float
        datetime            -> ISO 8601 string
        date                -> ISO 8601 string
        UUID                -> string
        Enum                -> .value
        Path                -> string
        bytes / bytearray   -> UTF-8 string if decodable, else base64 string
        dict                -> recursively normalized dict
        list / tuple / set  -> recursively normalized list
        anything else JSON-native (str, int, float, bool, None) -> unchanged
        anything else (unrecognized object) -> str(value), so serialization
            never raises even for a business object type not explicitly
            listed above; a warning is logged so unexpected types are
            still visible rather than silently mis-serialized forever.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            import base64

            return base64.b64encode(bytes(value)).decode("ascii")

    if isinstance(value, dict):
        return {key: normalize_json_value(val) for key, val in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [normalize_json_value(item) for item in value]

    logger.warning(
        "normalize_json_value: unrecognized type %s, falling back to str(). "
        "Consider adding explicit support if this type is expected.",
        type(value).__name__,
    )
    return str(value)


def _resolve_image_url(image_url: Optional[str], cached_path: Optional[str]) -> Optional[str]:
    """
    Returns a fetchable absolute URL for a property image.

    Imported images already carry a full `image_url`. Uploaded images only
    have a relative `cached_path` (relative to UPLOAD_ROOT, e.g.
    "properties/927/original/xyz.jpg"), which must be resolved against this
    backend's public base URL and the "/uploads" static mount registered in
    main.py before an external service like DEV-TOOLS can fetch it.
    """
    if image_url:
        return image_url
    if cached_path:
        base = settings.APP_BASE_URL.rstrip("/")
        path = cached_path.lstrip("/")
        return f"{base}/uploads/{path}"
    return None


def build_enterprise_payload(
    db: Session,
    *,
    project_id: int,
    property_id: int,
    business_goal: str = "",
    additional_notes: Optional[str] = None,
    requested_deliverables: Optional[List[str]] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Assembles the `data` block of a WACP envelope for a single AI request,
    in the project/property/images/instructions/metadata shape AI-CRE has
    always used for its business data - only the enclosing `header` is
    gone, since every field it used to carry is now envelope-level and
    supplied directly to WacpClient.submit() by the caller
    (ai_orchestration_service.py), never embedded inside `data` itself.

    This function is intentionally generic: it serializes whatever project,
    property, and instruction data it is given into the contract shape, and
    carries no AI-CRE-specific assumptions. This is what makes the contract
    reusable by future WIMLOGIC applications beyond AI-CRE.

    The returned dict's `project` block still includes `project_id` (the
    business project code, e.g. "PRJ001") alongside the numeric `id` -
    callers needing the business code for the WACP envelope's
    `project_code` field (§7.2) can read it from there rather than this
    module returning anything beyond the single `data` dict it always has.

    Raises PayloadBuilderError if the referenced project or property does
    not exist - callers should catch this and translate it into an
    appropriate HTTP 400/404, consistent with the rest of the codebase.
    """
    project_obj = crud_project.get(db, project_id)
    if not project_obj:
        raise PayloadBuilderError(f"Project with ID '{project_id}' does not exist")

    property_obj = crud_property.get(db, property_id)
    if not property_obj:
        raise PayloadBuilderError(f"Property with ID '{property_id}' does not exist")

    images, _total = crud_property_image.get_multi(
        db, property_id=property_id, limit=200, include_deleted=False
    )

    image_entries: List[Dict[str, Any]] = [
        {
            "image_type": img.image_type,
            "url": _resolve_image_url(img.image_url, img.cached_path),
            "notes": img.notes or "",
        }
        for img in images
    ]

    payload: Dict[str, Any] = {
        "project": {
            "id": project_obj.id,
            "project_id": project_obj.project_id,
            "project_name": project_obj.project_name,
            "description": project_obj.description,
        },
        "property": {
            "id": property_obj.id,
            "property_uid": property_obj.property_uid,
            "address": property_obj.address,
            "city": property_obj.city,
            "state": property_obj.state,
            "zip": property_obj.zip,
            "apn": property_obj.apn,
            "latitude": property_obj.latitude,
            "longitude": property_obj.longitude,
            "lot_sqft": property_obj.lot_sqft,
            "building_sqft": property_obj.building_sqft,
            "year_built": property_obj.year_built,
            "zoning_code": property_obj.zoning_code,
            "existing_use": property_obj.existing_use,
            "land_value": property_obj.land_value,
            "improvement_value": property_obj.improvement_value,
            "total_assessed_value": property_obj.total_assessed_value,
        },
        "images": image_entries,
        "instructions": {
            "business_goal": business_goal or "",
            "additional_notes": additional_notes or property_obj.notes or "",
            "requested_deliverables": requested_deliverables or [],
        },
        "metadata": metadata_json or {},
    }

    logger.info(
        "Built WACP data block for project_id=%s property_id=%s image_count=%d",
        project_id,
        property_id,
        len(image_entries),
    )

    # Single normalization pass: guarantees the returned dict is directly
    # compatible with json.dumps(...) with no custom encoder required
    # anywhere downstream (wacp_adapter.py, result_sync.py, or any
    # future caller).
    return normalize_json_value(payload)
