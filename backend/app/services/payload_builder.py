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
from app.crud.design_tool_knowledge_rule import design_tool_knowledge_rule as crud_design_tool_knowledge_rule
from app.crud.property_analysis_report import property_analysis_report as crud_property_analysis_report
from app.models.property_analysis_report import PropertyAnalysisReport
from app.services.knowledge_context_builder import (
    build_project_knowledge_fields,
    build_property_knowledge_fields,
    build_image_knowledge_fields,
    build_design_job_knowledge_fields,
)

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


def _build_property_ai_analysis(report: PropertyAnalysisReport) -> Dict[str, Any]:
    """
    AI HOME Knowledge Inheritance V1.0 - inheritance_04_backend_implementation.md
    §9. Converts one already-selected PropertyAnalysisReport ORM row (chosen
    by crud_property_analysis_report.get_latest_completed_for_project_property(),
    Step 2) into the canonical normalized contract shape for inclusion under
    Property scope in build_design_job_context() (wired in Step 4 - this
    function is not yet called by anything).

    Maps only the named, approved structured fields per the spec's exact
    field mapping table (§9.3). Deliberately excludes:
        report_json    - extended/unvalidated structured output, not
                          automatically trusted normalized context per
                          inheritance_03 §12.5
        raw_api_json    - not even a column on this model (it lives on
                          cre_properties, a different table entirely) -
                          this function has no way to leak it even by
                          accident, since it only ever reads named
                          attributes off `report`, never report.__dict__
                          or any other bulk-copy mechanism

    Read-only: only reads attributes off `report`, never assigns to it -
    the source ORM object is never mutated.

    Returns a JSON-safe dict via a single pass through the existing,
    reused normalize_json_value() (Decimal -> float, datetime -> ISO
    string, None preserved as None) - no second/competing normalizer is
    introduced.
    """
    raw: Dict[str, Any] = {
        "analysis_report_id": report.id,
        "workflow_execution_id": report.workflow_execution_id,
        "workflow_result_id": report.workflow_result_id,
        "analysis_version": report.analysis_version,
        "status": report.workflow_status,
        "completed_at": report.completed_at,
        "summary": {
            "recommendation": report.recommendation,
            "score": report.score,
            "confidence_score": report.confidence_score,
        },
        "findings": {
            "zoning_notes": report.zoning_notes,
            "risk_notes": report.risk_notes,
        },
        "estimate": {
            "low": report.estimate_low,
            "high": report.estimate_high,
        },
        "source_reference": {
            "report_id": report.id,
        },
    }
    return normalize_json_value(raw)


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


def build_design_job_context(
    db: Session,
    *,
    job,  # app.models.design_job.DesignJob - not type-hinted directly to avoid a
          # payload_builder <-> design_job model import cycle; callers pass the
          # already-loaded, already-lock_for_update()'d row.
    job_images: List[Any],  # List[app.models.design_job_image.DesignJobImage]
) -> Dict[str, Any]:
    """
    Design Studio Effective AI Context assembly (V1.1D). This is the
    Design Job equivalent of build_enterprise_payload() above, but for a
    genuinely different business contract: Effective AI Context =
    Project Knowledge + Property Knowledge + SELECTED Property Image
    Knowledge, entirely gated by this Tool's Knowledge Rules
    (cre_design_tool_knowledge_rules) rather than the unconditional
    "every property image" shape build_enterprise_payload() uses for its
    own, unrelated AI-orchestration contract.

    build_enterprise_payload() itself is NOT modified, NOT called, and
    NOT reused by this function - the two payload shapes are
    deliberately independent contracts for independent business flows,
    and conflating them would be exactly the kind of "duplicate business
    logic across two shapes" this codebase's conventions forbid in the
    other direction (one function serving two contracts is as wrong as
    two functions serving one).

    Only selected images (job_images) ever contribute Image Knowledge -
    each DesignJobImage's already-captured image_knowledge_snapshot_json
    (frozen at Configure time, Checkpoint 6) is reused as-is; this
    function never re-queries PropertyImage directly, so the assembled
    context reflects exactly what was selected, not whatever the image
    looks like right now.

    A scope with NO Knowledge Rule defined for this Tool is NOT included
    by default - Knowledge Rules are the opt-in switch controlling both
    requiredness (is_required) and inclusion (include_in_context) per
    the locked simplified architecture. If a Tool has no rules at all,
    this returns {}.

    Raises PayloadBuilderError (this module's existing exception class)
    if a Knowledge Rule marks a scope is_required=1 but the required data
    is unavailable (project/property not found, or no images selected
    for a required image scope) - callers (design_job_service.py) catch
    this and translate it into DesignJobValidationError / HTTP 400,
    exactly as build_enterprise_payload()'s own docstring already
    documents for its own PayloadBuilderError cases.

    Does NOT normalize its own return value - the caller
    (design_job_service.py) is responsible for the single
    normalize_json_value() pass over the combined submitted_payload_json,
    consistent with how it already normalizes tool_options and the rest
    of the frozen payload in one pass rather than several partial ones.
    """
    # Phase 1.2A: a scope may now have one blanket rule (field_code IS
    # NULL, governing exactly LEGACY_SCOPE_FIELDS for that scope) AND any
    # number of field-level rules (field_code IS NOT NULL, each governing
    # one FIELD_RULE_REGISTRY entry) - separated here rather than the
    # pre-1.2A single dict-per-scope, since more than one row per scope is
    # now valid. limit raised from 10 to 200 to accommodate this
    # (16 possible field-level rules today, comfortably under 200).
    rules, _ = crud_design_tool_knowledge_rule.get_multi(db, tool_id=job.tool_id, limit=200)
    blanket_rules_by_scope = {r.knowledge_scope: r for r in rules if r.field_code is None}
    field_rules_by_scope: Dict[str, List[Any]] = {}
    for r in rules:
        if r.field_code is not None:
            field_rules_by_scope.setdefault(r.knowledge_scope, []).append(r)

    context: Dict[str, Any] = {}

    project_rule = blanket_rules_by_scope.get("project")
    if project_rule:
        project_obj = crud_project.get_by_project_id(db, job.project_id)
        if project_rule.is_required == 1 and not project_obj:
            raise PayloadBuilderError(
                f"Tool Knowledge Rule requires project context, but project '{job.project_id}' was not found"
            )
        if project_rule.include_in_context == 1 and project_obj:
            context["project"] = {
                "project_id": project_obj.project_id,
                "project_name": project_obj.project_name,
                "description": project_obj.description,
                "knowledge_instructions": project_rule.instructions,
            }
            # Phase 1.2A - additive. Layers only the explicitly-granted
            # new fields (knowledge_context_builder.FIELD_RULE_REGISTRY)
            # on top of the untouched legacy block above; produces {}
            # when this Tool has no project-scope field-level rules,
            # exactly preserving pre-1.2A output.
            context["project"].update(
                build_project_knowledge_fields(project_obj, field_rules_by_scope.get("project", []))
            )

    property_rule = blanket_rules_by_scope.get("property")
    if property_rule:
        property_obj = crud_property.get(db, job.property_id)
        if property_rule.is_required == 1 and not property_obj:
            raise PayloadBuilderError(
                f"Tool Knowledge Rule requires property context, but property {job.property_id} was not found"
            )
        if property_rule.include_in_context == 1 and property_obj:
            context["property"] = {
                "address": property_obj.address,
                "city": property_obj.city,
                "state": property_obj.state,
                "zip": property_obj.zip,
                "apn": property_obj.apn,
                "zoning_code": property_obj.zoning_code,
                "existing_use": property_obj.existing_use,
                "notes": property_obj.notes,
                "knowledge_instructions": property_rule.instructions,
            }

            # AI HOME Knowledge Inheritance V1.0 (Step 4) - additive only.
            # Resolves the single deterministic, latest-eligible Property
            # Analysis Report (Step 2's crud helper - explicit
            # (project_id, property_id) pair, workflow_status="Completed",
            # completed_at DESC / id DESC) and, if one exists, injects its
            # normalized form (Step 3's _build_property_ai_analysis()) as
            # effective_context.property.ai_analysis. If no eligible
            # report exists, the key is simply omitted - never raised as
            # an error and never a placeholder/null value - since current
            # V1 Tool Knowledge Rules have no field-level requirement for
            # Property AI Analysis specifically (inheritance_04 §8.5).
            analysis_report = crud_property_analysis_report.get_latest_completed_for_project_property(
                db, project_id=job.project_id, property_id=job.property_id
            )
            if analysis_report:
                context["property"]["ai_analysis"] = _build_property_ai_analysis(analysis_report)

            # Phase 1.2A - additive, same pattern as project above.
            context["property"].update(
                build_property_knowledge_fields(property_obj, field_rules_by_scope.get("property", []))
            )

    image_rule = blanket_rules_by_scope.get("image")
    if image_rule:
        if image_rule.is_required == 1 and not job_images:
            raise PayloadBuilderError(
                "Tool Knowledge Rule requires selected Image Knowledge, but no images are selected"
            )
        if image_rule.include_in_context == 1 and job_images:
            # Phase 1.2A - Submit-time-fresh image context (approved
            # architecture revision §4.2). Previously this block read
            # img.image_knowledge_snapshot_json directly - the Configure-
            # time freeze. That snapshot is NOT removed and continues to
            # serve its two existing purposes unchanged (Tool Image
            # Requirement validation against the role captured at
            # Configure time; a historical record of what was selected
            # and its state at selection time) - but the CONTENT that
            # flows into effective_context.images[] is now re-read from
            # the live PropertyImage row at Submit time, exactly
            # mirroring how Project/Property context already worked
            # before this phase. This satisfies "Submit must rebuild the
            # complete effective context from authoritative current
            # records" as a hard rule applied uniformly across every
            # scope, not just two of the three.
            image_field_rules = field_rules_by_scope.get("image", [])
            images_context = []
            for img in job_images:
                live_image = crud_property_image.get(db, img.property_image_id)
                if live_image is not None:
                    knowledge = {
                        "image_role": live_image.image_role,
                        "notes": live_image.notes,
                        "ai_prompt": live_image.ai_prompt,
                        "tags": live_image.tags,
                        "constraints": live_image.constraints,
                        "priority": live_image.priority,
                        "is_primary": live_image.is_primary,
                        "status": live_image.status,
                    }
                    knowledge.update(build_image_knowledge_fields(live_image, image_field_rules))
                else:
                    # The live PropertyImage row no longer exists (deleted
                    # between Configure and Submit). build_design_job_context()
                    # runs before build_design_job_inputs() in
                    # submit_design_job() - the latter will raise
                    # PayloadBuilderError for this same missing image for
                    # MEDIA purposes momentarily after this function
                    # returns, and the whole Submit is atomic (nothing
                    # commits either way) - so this fallback never
                    # produces an incorrect *committed* result, it only
                    # determines which error surfaces first. Falling back
                    # to the frozen Configure-time snapshot here (rather
                    # than silently omitting the image) is the more
                    # honest choice for this transient window.
                    knowledge = img.image_knowledge_snapshot_json
                images_context.append({
                    "property_image_id": img.property_image_id,
                    "input_role": img.input_role,
                    "knowledge": knowledge,
                    "knowledge_instructions": image_rule.instructions,
                })
            context["images"] = images_context

    # Phase 1.2A - new design_job scope. Unlike the three scopes above,
    # design_job has no legacy fields at all (LEGACY_SCOPE_FIELDS
    # ["design_job"] is intentionally empty) and no "not found" failure
    # case (the DesignJob object is the very thing being built, so there
    # is nothing analogous to a missing Project/Property to guard
    # against) - a blanket design_job rule is therefore not a meaningful
    # concept on its own. The design_job section appears if and only if
    # at least one valid field-level design_job rule is granted and
    # produces a non-empty result; otherwise the key is omitted entirely,
    # never a placeholder.
    design_job_fields = build_design_job_knowledge_fields(job, field_rules_by_scope.get("design_job", []))
    if design_job_fields:
        context["design_job"] = design_job_fields

    return context


def build_design_job_inputs(db: Session, *, property_id: int, job_images: List[Any]) -> Dict[str, Any]:
    """
    Design Studio SELECTED IMAGE MEDIA INPUT assembly (V1.1D). This is a
    deliberately separate contract from build_design_job_context()'s
    Effective AI Context: Media Input answers "what image should the
    workflow actually process", while Effective AI Context answers "what
    business/AI context should the model know about that image" - the two
    are never conflated, and Tool Knowledge Rules (which gate Effective AI
    Context inclusion) have NO influence here. A selected DesignJobImage
    is unconditionally a processing input, regardless of whether any
    Knowledge Rule exists for the "image" scope.

    Media location, existence, deleted-state, AND OWNERSHIP are all
    resolved from the CURRENT persisted PropertyImage row via the
    existing, reused _resolve_image_url() plus a fresh ownership check -
    all "is this media still valid to send" questions are current-state
    concerns, unlike Image Knowledge (which remains frozen from each
    DesignJobImage.image_knowledge_snapshot_json and is never reassembled
    from the live PropertyImage row here). property_id is the Design
    Job's own property_id (the authoritative business ownership
    boundary) - NOT read from any snapshot value, since Configure-time
    validation alone is insufficient given PropertyImage.property_id is
    mutable after Configure.

    Returns {"images": [...]}, ordered by DesignJobImage.display_order,
    each entry: property_image_id, input_role (from DesignJobImage - NEVER
    overwritten by PropertyImage.image_role), image_type, url, mime_type
    (from PropertyImage.file_type), original_file_name.

    Raises PayloadBuilderError if any selected PropertyImage no longer
    exists, no longer belongs to property_id, is soft-deleted, or has no
    resolvable URL (both image_url and cached_path are empty) - a Design
    Job must never freeze a payload referencing media that has moved to
    another Property, been deleted, or cannot actually be fetched.
    """
    ordered = sorted(job_images, key=lambda img: img.display_order)
    entries: List[Dict[str, Any]] = []

    for job_image in ordered:
        prop_image = crud_property_image.get(db, job_image.property_image_id)
        if not prop_image:
            raise PayloadBuilderError(
                f"Selected Property Image {job_image.property_image_id} no longer exists"
            )
        if prop_image.property_id != property_id:
            raise PayloadBuilderError(
                f"Selected Property Image {job_image.property_image_id} now belongs to "
                f"Property {prop_image.property_id}, not this Design Job's Property ({property_id})"
            )
        if prop_image.is_deleted == 1:
            raise PayloadBuilderError(
                f"Selected Property Image {job_image.property_image_id} has been deleted "
                f"and cannot be sent as a processing input"
            )
        url = _resolve_image_url(prop_image.image_url, prop_image.cached_path)
        if not url:
            raise PayloadBuilderError(
                f"Selected Property Image {job_image.property_image_id} has no resolvable URL "
                f"(both image_url and cached_path are empty)"
            )
        entries.append({
            "property_image_id": prop_image.id,
            "input_role": job_image.input_role,
            "image_type": prop_image.image_type,
            "url": url,
            "mime_type": prop_image.file_type,
            "original_file_name": prop_image.original_file_name,
        })

    return {"images": entries}
