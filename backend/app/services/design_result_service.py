"""
app/services/design_result_service.py

AIHOME Phase 1 - Design Studio result ingestion and baseline approval.

Activates two already-existing, previously-dormant tables
(cre_design_image_versions, cre_approved_design_baselines) and their
already-fully-specified CRUD transaction patterns (see the docstrings on
crud/design_image_version.py, crud/approved_design_baseline.py,
crud/design_image_lineage.py - written during an earlier architecture
review, never implemented until now). This module is the orchestration
layer those docstrings already call for; it does not invent new
transaction shapes.

Per the approved Phase 1 principles:
- cre_design_image_lineage is the sole lineage mechanism (no new FK
  column) - confirmed correct by that model's own docstring: "ONE
  Property Image -> MANY generated versions" is exactly what this module
  needs and exactly what that table already models.
- No schema changes in this file.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

import requests
from PIL import Image
from io import BytesIO
from urllib.parse import urljoin

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.design_image_version import design_image_version as crud_design_image_version
from app.crud.design_image_lineage import design_image_lineage as crud_design_image_lineage
from app.crud.approved_design_baseline import approved_design_baseline as crud_approved_design_baseline
from app.crud.design_job_execution import design_job_execution as crud_design_job_execution
from app.models.design_job import DesignJob
from app.models.design_tool import DesignTool
from app.models.project import Project
from app.models.design_job_image import DesignJobImage
from app.models.design_job_execution import DesignJobExecution
from app.models.property import Property
from app.models.property_image import PropertyImage
from app.models.workflow_execution import WorkflowExecution
from app.models.design_image_version import DesignImageVersion
from app.models.design_image_lineage import DesignImageLineage
from app.models.approved_design_baseline import ApprovedDesignBaseline
from app.integrations.storage.filesystem_storage_provider import FilesystemStorageProvider

logger = logging.getLogger(__name__)

_storage_provider = FilesystemStorageProvider()

#: Reasonable ceiling for a single artifact download - an IMAGE_DESIGN
#: result should never legitimately produce anything close to this;
#: exists purely to bound how long one bad/slow artifact can block
#: ingestion of every OTHER image in the same result.
_ARTIFACT_DOWNLOAD_TIMEOUT_SECONDS = 30

#: RC1: "basic retry (3 attempts maximum)" - 3 TOTAL attempts (1 initial
#: + 2 retries), not 1 initial + 3 retries. HTTP 5xx is retried with
#: bounded exponential backoff (2s, 4s) up to this limit; HTTP 404 is
#: never retried (the artifact is gone, not transiently unavailable).
_ARTIFACT_DOWNLOAD_MAX_RETRIES = 2
_ARTIFACT_DOWNLOAD_RETRY_BASE_SECONDS = 2


class ImageDesignIngestionError(Exception):
    """Raised for a single image that could not be downloaded or
    imported. Caught per-image by ingest_image_design_results() so one
    bad artifact never blocks any of the others in the same result."""


class DesignResultError(Exception):
    """Raised for a domain-level failure creating a version or approving a baseline."""


class BaselineApprovalConflictError(DesignResultError):
    """
    Defensive fallback only - should be unreachable given the Property-row
    lock in approve_design_version(), but a raw IntegrityError must never
    reach an API caller (per the approved architecture review for this
    transaction).
    """


def _resolve_design_scope(db: Session, *, design_job_id: int) -> str:
    """
    Derives design_scope from the Design Job's own primary selected image's
    room-type (PropertyImage.image_role, e.g. "kitchen"/"front_exterior") -
    reusing the already-established image_role vocabulary rather than
    introducing a new field, per "prefer activating/extending over
    creating new". Falls back to "general" if no primary image is
    selected or that image has no image_role set, rather than raising -
    a missing scope classification should never block baseline creation.

    Not the same as DesignJobImage.input_role ("primary"/"supporting"/
    "reference" - a job-scoped selection role): this reads THROUGH the
    primary DesignJobImage to the underlying PropertyImage's own
    property-level room-type classification.
    """
    primary_job_image = db.execute(
        select(DesignJobImage).where(
            DesignJobImage.design_job_id == design_job_id,
            DesignJobImage.input_role == "primary",
        )
    ).scalars().first()
    if primary_job_image is None:
        return "general"

    property_image = db.get(PropertyImage, primary_job_image.property_image_id)
    if property_image is None or not property_image.image_role:
        return "general"
    return property_image.image_role


def create_design_image_version(
    db: Session,
    *,
    design_job: DesignJob,
    workflow_execution: WorkflowExecution,
    file_name: str,
    storage_path: str,
    thumbnail_path: Optional[str] = None,
    mime_type: Optional[str] = None,
    file_size: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    source_property_image_ids: Sequence[int] = (),
    source_image_version_ids: Sequence[int] = (),
) -> DesignImageVersion:
    """
    Creates one DesignImageVersion row from a completed Design Studio
    execution's output, plus one DesignImageLineage row per declared
    source - as a single atomic transaction (the "Image Version + Lineage
    Ingestion transaction" already named in crud/design_image_version.py's
    own docstring). A version must never persist with partial or missing
    lineage: every CRUD call here uses commit=False, with exactly one
    commit at the end.

    version_number is the next integer after the highest existing version
    for this design_job (crud.get_max_version_number() + 1) - monotonic
    per job, matching the existing UNIQUE(design_job_id, version_number)
    constraint.

    Callers pass property_image_ids for images that directly informed
    this generation, and image_version_ids for any prior version this one
    refines (a "v2 -> v3" refinement chain) - at least one of the two
    sequences should normally be non-empty, but this function does not
    enforce that itself (a version with genuinely no recorded lineage is
    a data-quality question for the caller, not something to block here).
    """
    next_version_number = crud_design_image_version.get_max_version_number(db, design_job_id=design_job.id) + 1

    version = crud_design_image_version.create(
        db,
        obj_in={
            "version_uid": f"DIV-{uuid.uuid4().hex[:16].upper()}",
            "design_job_id": design_job.id,
            "property_id": design_job.property_id,
            "workflow_execution_id": workflow_execution.execution_id,
            "version_number": next_version_number,
            "file_name": file_name,
            "storage_path": storage_path,
            "thumbnail_path": thumbnail_path,
            "mime_type": mime_type,
            "file_size": file_size,
            "width": width,
            "height": height,
            "status": "generated",
            "generated_at": workflow_execution.completed_at or datetime.now(),
        },
        commit=False,
    )

    for source_property_image_id in source_property_image_ids:
        crud_design_image_lineage.create(
            db,
            obj_in={
                "image_version_id": version.id,
                "source_type": "property_image",
                "source_property_image_id": source_property_image_id,
                "lineage_role": "primary",
            },
            commit=False,
        )
    for source_image_version_id in source_image_version_ids:
        crud_design_image_lineage.create(
            db,
            obj_in={
                "image_version_id": version.id,
                "source_type": "image_version",
                "source_image_version_id": source_image_version_id,
                "lineage_role": "parent",
            },
            commit=False,
        )

    db.commit()
    db.refresh(version)
    logger.info(
        "Created DesignImageVersion id=%s version_uid=%s design_job_id=%s version_number=%s "
        "with %d property-image source(s) and %d prior-version source(s).",
        version.id, version.version_uid, design_job.id, next_version_number,
        len(source_property_image_ids), len(source_image_version_ids),
    )
    return version


def approve_design_version(
    db: Session, *, image_version_id: int, approved_by: Optional[int] = None
) -> ApprovedDesignBaseline:
    """
    Promotes a DesignImageVersion to the active ApprovedDesignBaseline for
    its (property_id, design_type, design_scope) scope - the exact
    transaction already specified in crud/approved_design_baseline.py's
    own docstring, and already corrected once during an earlier
    architecture review for the first-approval race condition described
    below. Implementing that reviewed design, not designing fresh.

    Transaction, in order:
      1. Lock the parent PROPERTY row (SELECT ... FOR UPDATE) - NOT the
         active baseline row, which may not exist yet for a scope's
         first-ever approval (a lock on a nonexistent row is a no-op,
         which was the actual bug the earlier review caught and fixed).
      2. Only now query the current active baseline via
         crud.get_active() - safe, since the Property lock already
         serializes every concurrent approval for this property.
      3. If the target version is already the active baseline for its
         scope, return it unchanged (idempotent re-approval, no-op).
      4. If a different baseline is currently active for this scope,
         flip it to 'superseded' (commit=False) - active_scope_key
         collapses to NULL automatically the instant status changes,
         freeing the unique constraint.
      5. Insert the new active baseline (commit=False), copying
         tool_options_json/effective_context_json/submitted_payload_json
         from the source Design Job - a deliberate, one-time snapshot
         copy, since a Baseline's entire purpose is to be an immutable
         historical record independent of whatever the source Design
         Job's own row does afterward.
      6. Commit once. A duplicate-key IntegrityError (should be
         unreachable given the lock in step 1, but defended against
         anyway per the reviewed design) is translated into
         BaselineApprovalConflictError - never a raw DB exception to a
         caller.

    Every caller touching cre_approved_design_baselines for a given
    Property MUST acquire that Property's row lock first, in this same
    order, or the exact race this design fixes could be reintroduced by
    a different code path later.
    """
    version = crud_design_image_version.get(db, image_version_id)
    if version is None:
        raise DesignResultError(f"DesignImageVersion {image_version_id} does not exist.")

    design_job = db.get(DesignJob, version.design_job_id)
    if design_job is None:
        raise DesignResultError(f"DesignJob {version.design_job_id} for version {image_version_id} does not exist.")

    design_scope = _resolve_design_scope(db, design_job_id=design_job.id)

    # Step 1 - lock the stable, always-present Property row before
    # touching the baseline table at all.
    db.execute(select(Property).where(Property.id == version.property_id).with_for_update())

    # Step 2 - safe now; the Property lock serializes every writer.
    current_active = crud_approved_design_baseline.get_active(
        db, property_id=version.property_id, design_type=design_job.design_type, design_scope=design_scope,
    )

    # Step 3 - idempotent re-approval.
    if current_active is not None and current_active.image_version_id == image_version_id:
        return current_active

    # Step 4 - supersede the prior active baseline, if any.
    if current_active is not None:
        crud_approved_design_baseline.update(
            db, db_obj=current_active, obj_in={"status": "superseded"}, commit=False,
        )

    # Step 5 - insert the new active baseline, snapshotting the source
    # Design Job's frozen payload fields.
    new_baseline = crud_approved_design_baseline.create(
        db,
        obj_in={
            "baseline_uid": f"BASE-{uuid.uuid4().hex[:16].upper()}",
            "project_id": design_job.project_id,
            "property_id": version.property_id,
            "design_job_id": design_job.id,
            "image_version_id": image_version_id,
            "tool_id": design_job.tool_id,
            "tool_code": design_job.tool_code,
            "design_type": design_job.design_type,
            "design_scope": design_scope,
            "tool_options_json": design_job.tool_options_json,
            "effective_context_json": design_job.effective_context_json,
            "submitted_payload_json": design_job.submitted_payload_json,
            "approved_by": approved_by,
            "approved_at": datetime.now(),
        },
        commit=False,
    )

    # Step 6 - commit once. Defensive fallback only.
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.error(
            "Baseline approval hit a duplicate-key conflict for property_id=%s design_type=%s "
            "design_scope=%s despite the Property-row lock - should be unreachable; treating as "
            "a concurrent-approval conflict rather than raising a raw DB error. %s",
            version.property_id, design_job.design_type, design_scope, exc,
        )
        raise BaselineApprovalConflictError(
            "Another approval for this scope completed concurrently; retry."
        ) from exc

    # Also mark the version itself as approved, for direct querying
    # without joining through the baseline table.
    crud_design_image_version.update(db, db_obj=version, obj_in={"status": "approved"}, commit=True)

    db.refresh(new_baseline)
    logger.info(
        "Approved DesignImageVersion id=%s as the active baseline for property_id=%s "
        "design_type=%s design_scope=%s (baseline_id=%s).",
        image_version_id, version.property_id, design_job.design_type, design_scope, new_baseline.id,
    )
    return new_baseline


def list_versions_for_property_image(db: Session, *, property_image_id: int) -> List[DesignImageVersion]:
    """
    Returns every DesignImageVersion whose lineage traces back to a given
    Property Image - the read query the Phase D "Versions" UI needs.
    Reuses cre_design_image_lineage as the sole lineage authority (no new
    FK column, per the approved Phase 1 principle): finds every
    DesignImageLineage row with source_type="property_image" and
    source_property_image_id matching, then fetches those specific
    version rows, newest first.
    """
    lineage_rows = db.execute(
        select(DesignImageLineage).where(
            DesignImageLineage.source_type == "property_image",
            DesignImageLineage.source_property_image_id == property_image_id,
        )
    ).scalars().all()

    version_ids = {row.image_version_id for row in lineage_rows}
    if not version_ids:
        return []

    versions = db.execute(
        select(DesignImageVersion)
        .where(DesignImageVersion.id.in_(version_ids))
        .order_by(DesignImageVersion.created_at.desc())
    ).scalars().all()
    return list(versions)


# ---------------------------------------------------------------------------
# AIHOME Image Result Integration - IMAGE_DESIGN workflow support.
#
# Architecture (unchanged ownership model, per the task's own diagram):
#
#     DEV-TOOLS -> Temporary Artifact -> Artifact API -> AIHOME
#         -> Download -> Permanent Version -> Image History -> Display
#
# DEV-TOOLS owns workflow execution and temporary generated artifacts;
# AIHOME owns permanent property images, version history, design
# history, and approved designs. This module only ever performs a plain
# HTTP GET against the already-published, already-verified artifact
# endpoint DEV-TOOLS exposes (design_images[].url) - `storage_path`
# (DEV-TOOLS' own internal path) is never read or used. No DEV-TOOLS,
# WACP, or Runtime file is touched by any of this.
#
# Called EAGERLY at result-sync time (result_sync._sync_completed_job),
# not lazily when a user opens the Results page - the recommendation
# behind this design: AIHOME must hold its own permanent copy before any
# DEV-TOOLS temporary artifact could be cleaned up, so the Results page
# only ever displays AIHOME-managed images, never a live DEV-TOOLS URL.
#
# SCOPING NOTE (explicitly not silently expanded): this requires an
# existing DesignJob associated with the WorkflowExecution
# (cre_design_job_executions), which is always true for the established
# Design Studio submission flow. An IMAGE_DESIGN result arriving via the
# Business Intent checkboxes on a Property Analysis submission (which
# never creates a DesignJob) is NOT yet handled here - doing so would
# require auto-provisioning a DesignJob AND a DesignTool row, and I do
# not have a verified copy of the DesignTool model to write that
# correctly. ingest_image_design_results() logs a warning and skips
# ingestion (never raises, never blocks the rest of result sync) for
# this case rather than guessing at DesignTool's required fields.
# ---------------------------------------------------------------------------

#: RC1 - the implicit DesignTool/DesignJob used when an image arrives
#: with no pre-existing Design Studio job (e.g. IMAGE_DESIGN requested
#: via the Business Intent checkboxes, or any future non-Design-Studio
#: caller). No new tables are created - this reuses cre_design_tools and
#: cre_design_jobs exactly as they already exist, satisfying
#: cre_design_image_versions.design_job_id's existing NOT NULL
#: constraint without any schema change.
_IMPLICIT_DESIGN_TOOL_CODE = "GENERIC_ARTIFACT_IMPORT"


def _get_or_create_implicit_design_tool(db: Session) -> DesignTool:
    """Finds or creates the single, shared implicit DesignTool row used
    for every non-Design-Studio image import. Idempotent - safe to call
    on every import; only ever creates this row once."""
    existing = db.execute(
        select(DesignTool).where(DesignTool.tool_code == _IMPLICIT_DESIGN_TOOL_CODE)
    ).scalars().first()
    if existing:
        return existing
    tool = DesignTool(
        tool_code=_IMPLICIT_DESIGN_TOOL_CODE,
        tool_name="Generic Artifact Import (RC1)",
        design_type="generic_artifact_import",
        workflow_code="GENERIC_ARTIFACT_IMPORT",
        status="active",
    )
    db.add(tool)
    db.commit()
    db.refresh(tool)
    logger.info("Auto-provisioned the shared implicit DesignTool id=%s (%s).", tool.id, _IMPLICIT_DESIGN_TOOL_CODE)
    return tool


def ensure_import_design_job(db: Session, *, execution: WorkflowExecution) -> DesignJob:
    """
    Returns the DesignJob already associated with this execution if one
    exists (the established Design Studio submission flow); otherwise
    auto-provisions a minimal implicit DesignJob (and, if needed, the
    shared implicit DesignTool) so image import NEVER depends on Design
    Studio having been used at all - per RC1's explicit requirement.

    No new tables: this only ever inserts ordinary rows into the
    existing cre_design_jobs / cre_design_tools / cre_design_job_executions
    tables, using them exactly as already defined.
    """
    existing = _find_design_job_for_execution(db, execution=execution)
    if existing is not None:
        return existing

    tool = _get_or_create_implicit_design_tool(db)
    project_row = db.get(Project, execution.project_id)
    project_code = project_row.project_id if project_row is not None else str(execution.project_id)

    job = DesignJob(
        job_number=f"IMPLICIT-{execution.execution_id}",
        project_id=project_code,
        property_id=execution.property_id,
        tool_id=tool.id,
        tool_code=_IMPLICIT_DESIGN_TOOL_CODE,
        design_type="generic_artifact_import",
        workflow_code=execution.workflow_code,
        status="Completed",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    db.add(DesignJobExecution(
        design_job_id=job.id, workflow_execution_id=execution.execution_id,
        attempt_number=1, is_current=True,
    ))
    db.commit()

    logger.info(
        "No Design Studio job existed for execution_id=%s - auto-provisioned implicit "
        "DesignJob id=%s (job_number=%s) so image import can proceed independent of "
        "Design Studio, per RC1's explicit requirement.",
        execution.execution_id, job.id, job.job_number,
    )
    return job


def _find_design_job_for_execution(db: Session, *, execution: WorkflowExecution) -> Optional[DesignJob]:
    """Looks up the DesignJob already associated with this
    WorkflowExecution via cre_design_job_executions (the Design Studio
    submission flow always creates this link before dispatch). Returns
    None if no such link exists - see the scoping note above."""
    job_execution = crud_design_job_execution.get_by_workflow_execution_id(
        db, workflow_execution_id=execution.execution_id
    )
    if job_execution is None:
        return None
    return db.get(DesignJob, job_execution.design_job_id)


def _resolve_artifact_url(raw_url: str) -> str:
    """
    Resolves a design_images[].url entry to a fully-qualified download
    URL. Per the task's own example: a relative URL
    ("/api/v1/artifacts/...") is joined against the configured WACP
    server origin (settings.WACP_BASE_URL - AIHOME's existing WACP
    connection setting; conceptually the same thing the task calls
    DEV_TOOLS_API_BASE_URL). An already-absolute URL is returned as-is.
    storage_path is never read anywhere in this module - only this
    `url` field is ever used to construct a download request.
    """
    if raw_url.startswith("http://") or raw_url.startswith("https://"):
        return raw_url
    if not settings.WACP_BASE_URL:
        raise ImageDesignIngestionError(
            "Cannot resolve a relative artifact URL: settings.WACP_BASE_URL is not configured."
        )
    return urljoin(settings.WACP_BASE_URL.rstrip("/") + "/", raw_url.lstrip("/"))


def _download_artifact(url: str, expected_mime_type: str) -> "_DownloadedArtifact":
    """
    Downloads the generated image's raw bytes, per
    AIHOME_IMAGE_DESIGN_OUTPUT_SPEC.md's "Artifact Download" and "Error
    Handling" sections:

      - HTTP 404: the artifact is unavailable/expired - fails immediately,
        no retry (regenerating is DEV-TOOLS' and the operator's decision,
        not something to paper over by retrying a permanently-missing
        artifact).
      - HTTP 5xx: retried with bounded exponential backoff
        (_ARTIFACT_DOWNLOAD_MAX_RETRIES attempts, doubling delay each time)
        before giving up - a transient DEV-TOOLS issue should not
        permanently drop an otherwise-valid image.
      - Any other non-200: fails immediately, no retry.
      - Content-Type must EXACTLY match `design_images[].mime_type` (not
        merely "contains png") - a mismatch is rejected outright, per the
        spec's explicit MIME-mismatch handling.

    Raises ImageDesignIngestionError (never a raw requests exception) on
    any failure, so the caller's per-image try/except catches a single,
    predictable error type.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(_ARTIFACT_DOWNLOAD_MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=_ARTIFACT_DOWNLOAD_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < _ARTIFACT_DOWNLOAD_MAX_RETRIES:
                time.sleep(_ARTIFACT_DOWNLOAD_RETRY_BASE_SECONDS * (2 ** attempt))
                continue
            raise ImageDesignIngestionError(f"Network error downloading artifact from '{url}': {exc}") from exc

        if response.status_code == 404:
            raise ImageDesignIngestionError(
                f"Artifact endpoint returned HTTP 404 for '{url}' - the artifact is unavailable "
                "or expired; regeneration is required rather than retrying."
            )
        if 500 <= response.status_code < 600:
            if attempt < _ARTIFACT_DOWNLOAD_MAX_RETRIES:
                logger.warning(
                    "Artifact endpoint returned HTTP %s for '%s' (attempt %d/%d) - retrying "
                    "after bounded exponential backoff.",
                    response.status_code, url, attempt + 1, _ARTIFACT_DOWNLOAD_MAX_RETRIES + 1,
                )
                time.sleep(_ARTIFACT_DOWNLOAD_RETRY_BASE_SECONDS * (2 ** attempt))
                continue
            raise ImageDesignIngestionError(
                f"Artifact endpoint returned HTTP {response.status_code} for '{url}' after "
                f"{_ARTIFACT_DOWNLOAD_MAX_RETRIES + 1} attempts."
            )
        if response.status_code != 200:
            raise ImageDesignIngestionError(
                f"Artifact endpoint returned HTTP {response.status_code} for '{url}' (expected 200)."
            )

        response_mime_type = response.headers.get("Content-Type", "").split(";")[0].strip()
        if response_mime_type != expected_mime_type:
            raise ImageDesignIngestionError(
                f"Artifact MIME mismatch for '{url}': expected {expected_mime_type!r}, "
                f"received {response_mime_type!r}."
            )

        return _DownloadedArtifact(
            data=response.content,
            content_disposition=response.headers.get("Content-Disposition"),
            mime_type=response_mime_type,
        )

    # Unreachable in practice (every branch above either returns or
    # raises), but keeps type-checkers satisfied and fails loudly rather
    # than silently returning None if control flow is ever changed.
    raise ImageDesignIngestionError(f"Exhausted retries downloading artifact from '{url}'.") from last_exc


class _DownloadedArtifact:
    """Plain holder for a downloaded artifact's bytes plus the response
    headers needed for filename resolution (Content-Disposition) - never
    exposed outside this module."""

    def __init__(self, *, data: bytes, content_disposition: Optional[str], mime_type: str):
        self.data = data
        self.content_disposition = content_disposition
        self.mime_type = mime_type


_MIME_TO_EXTENSION = {"image/png": ".png", "image/jpeg": ".jpg"}


def _filename_from_content_disposition(content_disposition: Optional[str]) -> Optional[str]:
    """Extracts `filename="..."` from a Content-Disposition header value,
    per the spec's filename-resolution priority (this is priority #1,
    tried before the MIME-derived extension or the image_id fallback)."""
    if not content_disposition:
        return None
    match = re.search(r'filename\s*=\s*"?([^";]+)"?', content_disposition)
    return match.group(1).strip() if match else None


def _resolve_filename(
    *, image_id: Optional[str], mime_type: str, content_disposition: Optional[str],
    metadata_filename: Optional[str] = None,
) -> str:
    """
    Determines the imported filename, in priority order:

      1. An explicit filename in the image's own metadata (RC1's
         `download.filename`, e.g. "kitchen_modern.png") - the most
         authoritative source when DEV-TOOLS provides one directly.
      2. Filename from the Content-Disposition response header.
      3. Extension derived from design_images[].mime_type, combined with image_id.
      4. Fallback filename using image_id alone (mime type not recognized).
    """
    if metadata_filename:
        return metadata_filename

    from_header = _filename_from_content_disposition(content_disposition)
    if from_header:
        return from_header

    stem = image_id or uuid.uuid4().hex
    extension = _MIME_TO_EXTENSION.get(mime_type)
    if extension:
        return f"{stem}{extension}"

    return stem


def _verify_checksum(data: bytes, expected_checksum: Optional[str]) -> None:
    """
    Independently verifies the downloaded bytes against the checksum
    DEV-TOOLS reported, when one was provided. Per
    AIHOME_IMAGE_DESIGN_OUTPUT_SPEC.md's "Checksum Validation" and Error
    Handling sections, a mismatch is REJECTED, not merely logged -
    `checksum` is documented as the SHA-256 hex digest of the generated
    file specifically (not an ambiguous/unspecified algorithm), so a
    mismatch means the downloaded bytes do not match what DEV-TOOLS
    reported, and the artifact must not be imported.
    """
    if not expected_checksum:
        return
    actual = hashlib.sha256(data).hexdigest()
    if actual.lower() != expected_checksum.lower():
        raise ImageDesignIngestionError(
            f"Checksum mismatch: DEV-TOOLS reported {expected_checksum!r}, downloaded bytes hash "
            f"to {actual!r}. Rejecting this artifact - the downloaded bytes do not match what "
            "DEV-TOOLS reported, per the documented SHA-256 checksum contract."
        )


def ingest_one_generated_image(
    db: Session,
    *,
    execution: WorkflowExecution,
    design_job: DesignJob,
    image_entry: Dict[str, Any],
    quality_approved: Optional[bool] = None,
) -> DesignImageVersion:
    """
    Downloads one design_images[] entry and imports it into AIHOME's
    permanent storage + design history:

        DEV-TOOLS artifact URL
              v
        Download (exact MIME match, bounded retry on 5xx, no retry on 404)
              v
        Checksum verification (SHA-256; mismatch REJECTS the artifact)
              v
        properties/{property_id}/ai/  (FilesystemStorageProvider.CATEGORY_AI -
                                        the property-wide "ai" category,
                                        confirmed against the actual on-disk
                                        layout, not the per-image-version
                                        "images/{id}/versions/" path used
                                        elsewhere in this file)
              v
        Thumbnail generated alongside it
              v
        DesignImageVersion + lineage row (create_design_image_version(),
        unchanged - reused exactly as designed for every other version)

    `quality_approved` (optional) is DEV-TOOLS' own quality_review.approved
    outcome for this result, passed through from the caller so it can be
    stored alongside the version - per AIHOME_IMAGE_DESIGN_OUTPUT_SPEC.md,
    "Workflow completion and quality approval are separate states" and
    product policy (not this function) decides whether an unapproved
    image may be imported/previewed/published; this function always
    imports and always records the flag, so AIHOME's UI can apply
    whatever policy it chooses at display time.

    Raises ImageDesignIngestionError on any failure (download, checksum,
    storage, or Pillow decode) - the caller (ingest_image_design_results)
    catches this per-image so one bad artifact never blocks any other
    image in the same result.
    """
    # Metadata shape flexibility: real production DEV-TOOLS payloads
    # traced during this engagement carry url/checksum/mime_type FLAT on
    # the image entry directly (image_id, url, checksum, mime_type all
    # siblings). RC1's own example proposes a nested `download{}`
    # envelope instead (artifact_id, download: {url, checksum,
    # mime_type, filename}) - the two are tried in that order (nested
    # first, flat fallback) so this works unmodified against either
    # shape, rather than assuming the newer, not-yet-confirmed-in-
    # production shape and silently breaking the real payloads already
    # verified against this pipeline.
    # image_id (the generated image's own identity within DEV-TOOLS) is
    # distinct from artifact_id (the storage-blob identity the download
    # URL is keyed on - confirmed as two DIFFERENT values in a real
    # payload). source_image_id's own field name says "image", so
    # image_id takes priority when both are present; artifact_id is only
    # used as a fallback identifier when image_id is absent entirely.
    image_id = image_entry.get("image_id") or image_entry.get("artifact_id")
    download_meta = image_entry.get("download")
    if isinstance(download_meta, dict):
        raw_url = download_meta.get("url")
        checksum = download_meta.get("checksum")
        mime_type = download_meta.get("mime_type") or "image/png"
        metadata_filename = download_meta.get("filename")
    else:
        raw_url = image_entry.get("url")
        checksum = image_entry.get("checksum")
        mime_type = image_entry.get("mime_type") or "image/png"
        metadata_filename = None

    if not raw_url:
        raise ImageDesignIngestionError(f"design_images entry (image_id={image_id!r}) has no 'url' field.")

    download_url = _resolve_artifact_url(raw_url)
    artifact = _download_artifact(download_url, expected_mime_type=mime_type)
    _verify_checksum(artifact.data, checksum)
    data = artifact.data

    # Verify the downloaded bytes actually decode as a real image and
    # extract authoritative width/height directly from the bytes -
    # never blindly trusted from the (possibly stale or incorrect)
    # width/height fields DEV-TOOLS reported alongside the URL.
    try:
        with Image.open(BytesIO(data)) as pil_image:
            pil_image.verify()
        with Image.open(BytesIO(data)) as pil_image:
            actual_width, actual_height = pil_image.size
    except Exception as exc:
        raise ImageDesignIngestionError(
            f"Downloaded artifact for image_id={image_id!r} is not a valid image: {exc}"
        ) from exc

    file_name = _resolve_filename(
        image_id=image_id, mime_type=mime_type, content_disposition=artifact.content_disposition,
        metadata_filename=metadata_filename,
    )

    try:
        storage_path = _storage_provider.save_file(
            property_id=design_job.property_id,
            category=FilesystemStorageProvider.CATEGORY_AI,
            data=data,
            filename=file_name,
        )
        thumbnail_path = _storage_provider.generate_thumbnail(
            property_id=design_job.property_id,
            source_relative_path=storage_path,
        )
    except Exception as exc:
        raise ImageDesignIngestionError(
            f"Failed to save downloaded artifact for image_id={image_id!r} to AIHOME storage: {exc}"
        ) from exc

    # Lineage: every currently-associated input image for this Design
    # Job, matching the same convention create_design_image_version()
    # already uses elsewhere for Design Studio's own generation flow.
    source_property_image_ids = [
        row.property_image_id
        for row in db.execute(
            select(DesignJobImage).where(DesignJobImage.design_job_id == design_job.id)
        ).scalars().all()
    ]

    version = create_design_image_version(
        db,
        design_job=design_job,
        workflow_execution=execution,
        file_name=file_name,
        storage_path=storage_path,
        thumbnail_path=thumbnail_path,
        mime_type=mime_type,
        file_size=len(data),
        width=actual_width,
        height=actual_height,
        source_property_image_ids=source_property_image_ids,
    )

    # Provenance (requires the six columns from
    # add_design_image_version_provenance_columns.sql / the model patch -
    # set here via a direct, minimal update rather than threading six
    # new parameters through create_design_image_version()'s existing
    # signature, since none of its OTHER callers have any provenance to
    # supply and its signature is otherwise unchanged).
    version.source_image_id = str(image_id) if image_id is not None else None
    version.source_provider = image_entry.get("provider")
    version.source_model = image_entry.get("model")
    version.source_checksum = checksum
    version.source_artifact_url = download_url
    version.quality_approved = quality_approved
    db.commit()
    db.refresh(version)

    logger.info(
        "Imported generated design image image_id=%s (provider=%s, model=%s, quality_approved=%s) as "
        "DesignImageVersion id=%s version_uid=%s for property_id=%s.",
        image_id, image_entry.get("provider"), image_entry.get("model"), quality_approved,
        version.id, version.version_uid, design_job.property_id,
    )
    return version


def ingest_image_design_results(
    db: Session, *, execution: WorkflowExecution, result_data: Dict[str, Any],
) -> List[DesignImageVersion]:
    """
    Scans a DEV-TOOLS terminal result for any IMAGE_DESIGN-shaped output
    (a payload containing a non-empty `design_images` array) and imports
    every entry into AIHOME's permanent storage. Called from
    result_sync._sync_completed_job() - eagerly, at sync time, not
    lazily when the Results page is opened, per the explicit design
    recommendation this was built against.

    Supports multiple generated images per result (iterates the full
    `design_images` array, never assumes exactly one) and multiple
    IMAGE_DESIGN-shaped outputs within the same multi-Business-Intent
    result (iterates every flattened output, not just the first match).

    RC1: does NOT depend on Design Studio or Business Intent. If no
    DesignJob is associated with this execution (the Business Intent
    checkboxes never create one), an implicit DesignJob is
    auto-provisioned - see ensure_import_design_job(). No new
    tables; this only inserts ordinary rows into cre_design_jobs /
    cre_design_tools / cre_design_job_executions, exactly as they
    already exist.

    One failed image (network error, non-200/non-PNG response, checksum
    verification, storage failure) is logged and skipped - it never
    prevents any other image in the same result, or the rest of result
    sync, from completing. Returns the list of successfully created
    DesignImageVersion rows (possibly empty if no IMAGE_DESIGN output was
    present at all, or every image failed).
    """
    from app.services.dev_tools_output_flattening import flatten_dev_tools_outputs

    design_job = _find_design_job_for_execution(db, execution=execution)

    created: List[DesignImageVersion] = []
    #: Guards against importing the same generated image twice when a
    #: result carries it in BOTH shapes (a Final Design Package's
    #: design_images[] AND a standalone artifact output) - keyed by
    #: image_id/artifact_id.
    seen_image_keys: set = set()

    all_outputs = flatten_dev_tools_outputs(result_data)

    # WF_IMAGE_DESIGN_ONLY returns quality_review as its OWN separate
    # output rather than nested inside a Final Design Package, so it's
    # resolved up-front here and applied to any artifact-shaped image
    # found below. Shape A (Final Design Package) still reads its own
    # nested quality_review as before - this pre-scan only supplies the
    # value for Shape B.
    result_quality_approved = None
    for output in all_outputs:
        content = output.get("content")
        if not isinstance(content, str):
            continue
        try:
            payload = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(payload, dict) and "approved" in payload and "overall_score" in payload:
            result_quality_approved = payload.get("approved")
            if result_quality_approved is False:
                logger.warning(
                    "IMAGE_DESIGN result for execution_id=%s has quality_review.approved=false "
                    "(issues=%s) - importing anyway per current policy; quality_approved is stored "
                    "on the version so the UI can surface this.",
                    execution.execution_id, payload.get("issues"),
                )
            break

    for output in all_outputs:
        # NOTE: 'artifact' outputs are explicitly allowed through here.
        # The previous `!= "json"` filter skipped them entirely, which
        # is precisely why WF_IMAGE_DESIGN_ONLY's generated image - its
        # ONLY carrier - was never seen at all.
        if output.get("output_type") not in ("json", "artifact"):
            continue
        content = output.get("content")
        if not isinstance(content, str):
            continue
        try:
            payload = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue

        # ---- Shape B: a standalone artifact output ----
        # WF_IMAGE_DESIGN_ONLY (WIM Module V2) returns NO Final Design
        # Package at all - confirmed against a real completed result.
        # Its outputs are: a design-context output, a prompt-builder
        # output, a raw generation-agent output, a quality-review
        # output, and ONE output with output_type="artifact" whose
        # `content` IS the image object itself (image_id, artifact_id,
        # url, download{}, checksum) - not wrapped in a design_images
        # array, and with none of the five package signature fields
        # anywhere. Shape A below therefore never matched, and the
        # image was silently skipped - the confirmed root cause of
        # generated images never appearing in AIHOME for this workflow.
        if output.get("output_type") == "artifact":
            is_image = (
                payload.get("artifact_type") == "IMAGE"
                or str(payload.get("mime_type", "")).startswith("image/")
            )
            if is_image and payload.get("url"):
                if design_job is None:
                    design_job = ensure_import_design_job(db, execution=execution)
                artifact_key = payload.get("image_id") or payload.get("artifact_id")
                if artifact_key and artifact_key in seen_image_keys:
                    continue
                if artifact_key:
                    seen_image_keys.add(artifact_key)
                try:
                    version = ingest_one_generated_image(
                        db, execution=execution, design_job=design_job, image_entry=payload,
                        quality_approved=result_quality_approved,
                    )
                    created.append(version)
                except ImageDesignIngestionError as exc:
                    logger.error(
                        "Skipping one generated artifact image (image_id=%s) for execution_id=%s: %s",
                        payload.get("image_id"), execution.execution_id, exc,
                    )
            continue

        # ---- Shape A: Final Design Package ----
        # Final Design Package selection, per
        # AIHOME_IMAGE_DESIGN_OUTPUT_SPEC.md's "Selecting the Final
        # Design Package": require ALL FIVE signature fields together,
        # not merely `design_images` alone. Several OTHER outputs in the
        # same result (the standalone design-context output, the raw
        # generation-agent output, the quality-review output, the
        # design-recommendation output) may each carry a subset of this
        # data on their own - only the true final package carries all
        # five at once, and relying on `design_images` alone risks
        # matching an earlier draft/interim output in a differently-
        # shaped future result.
        design_images = payload.get("design_images")
        if not isinstance(design_images, list) or not design_images:
            continue
        if not all(key in payload for key in ("design_context", "quality_review", "design_recommendation", "execution_metadata")):
            continue

        quality_review = payload.get("quality_review")
        quality_approved = quality_review.get("approved") if isinstance(quality_review, dict) else None
        if quality_approved is False:
            logger.warning(
                "IMAGE_DESIGN result for execution_id=%s has quality_review.approved=false "
                "(issues=%s) - importing anyway per current policy (product policy determines "
                "whether an unapproved image may be displayed/published; quality_approved is "
                "stored on the version so the UI can surface this).",
                execution.execution_id, quality_review.get("issues") if isinstance(quality_review, dict) else None,
            )

        if design_job is None:
            design_job = ensure_import_design_job(db, execution=execution)

        for image_entry in design_images:
            if not isinstance(image_entry, dict):
                continue
            entry_key = image_entry.get("image_id") or image_entry.get("artifact_id")
            if entry_key and entry_key in seen_image_keys:
                continue
            if entry_key:
                seen_image_keys.add(entry_key)
            try:
                version = ingest_one_generated_image(
                    db, execution=execution, design_job=design_job, image_entry=image_entry,
                    quality_approved=quality_approved,
                )
                created.append(version)
            except ImageDesignIngestionError as exc:
                logger.error(
                    "Skipping one generated image (image_id=%s) for execution_id=%s: %s",
                    image_entry.get("image_id"), execution.execution_id, exc,
                )
                continue

    return created


__all__ = [
    "DesignResultError",
    "BaselineApprovalConflictError",
    "ImageDesignIngestionError",
    "create_design_image_version",
    "approve_design_version",
    "list_versions_for_property_image",
    "ingest_image_design_results",
    "ingest_one_generated_image",
    "ensure_import_design_job",
]
