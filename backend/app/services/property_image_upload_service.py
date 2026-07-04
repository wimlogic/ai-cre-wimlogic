"""
services/property_image_upload_service.py

AI-CRE WIMLOGIC V1 -- Enterprise Business Service
Phase 3A -- Enterprise Image Upload & Workflow Integration

Purpose
-------
Business service responsible for uploading Property Images (single file,
multi-file, and drag & drop batches) into enterprise filesystem storage,
generating thumbnails, and persisting metadata rows through the existing
`crud.property_image` layer.

Architecture Compliance
-------------------------
- No SQL appears in this file. All persistence goes through
  app.crud.property_image (existing, unmodified) and app.crud.property
  (existing, unmodified) for the property-existence guard.
- All file I/O goes through
  app.integrations.storage.filesystem_storage_provider (Phase 3A).
- This service is intentionally decoupled from FastAPI. It accepts a
  framework-agnostic `UploadFileInput` dataclass rather than
  `fastapi.UploadFile`, so that translating an incoming multipart request
  into bytes remains an HTTP-layer concern for the router to own (per
  "Routers contain HTTP only"), and so this service can be unit tested
  without a running FastAPI app.
- Only the `cached_path` (relative path to the original file) is persisted
  to `cre_property_images`. The schema has no dedicated thumbnail-path
  column, and per AI Studio rules this service does not invent one.
  `derive_thumbnail_relative_path()` below computes the thumbnail's
  relative path deterministically from `cached_path` using the same
  naming convention FilesystemStorageProvider.generate_thumbnail() applies,
  so callers (API layer) can resolve a thumbnail URL without a new column.

Rollback Behavior
-------------------
Each individual file upload is wrapped in its own try/except. If the
database write fails after file(s) were already written to disk, the
written original (and thumbnail, if generated) are deleted before the
exception propagates. In a multi-file batch, one file's failure and
rollback never aborts the remaining files -- partial success is expected
and reported back via BatchUploadSummary.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from sqlalchemy.orm import Session

from app.crud.property import property as crud_property
from app.crud.property_image import property_image as crud_property_image
from app.integrations.storage.filesystem_storage_provider import (
    FilesystemStorageProvider,
    StorageError,
    ThumbnailGenerationError,
    filesystem_storage_provider,
)
from app.models.property_image import PropertyImage
from app.schemas.property_image import PropertyImageCreate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Framework-agnostic data contracts
# ---------------------------------------------------------------------------

@dataclass
class UploadFileInput:
    """
    A single file to be uploaded, decoupled from any specific web framework.
    The API router is responsible for populating this from an incoming
    multipart/form-data request (e.g. from a FastAPI UploadFile).
    """

    filename: str
    content: bytes
    content_type: Optional[str] = None
    image_role: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class UploadResult:
    """Outcome for a single file within a multi-file upload batch."""

    filename: str
    success: bool
    property_image: Optional[PropertyImage] = None
    error: Optional[str] = None


@dataclass
class BatchUploadSummary:
    """
    Aggregate result of a multi-file / drag & drop upload request.
    Supports partial success: some files may succeed while others fail.
    """

    property_id: int
    total: int
    succeeded: int
    failed: int
    results: List[UploadResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class PropertyImageUploadService:
    """
    Business service for uploading property images to enterprise
    filesystem storage and persisting their metadata.
    """

    def __init__(self) -> None:
        self._storage = filesystem_storage_provider

    # -- Public API -----------------------------------------------------

    def upload_single(
        self,
        db: Session,
        *,
        property_id: int,
        file_input: UploadFileInput,
        project_id: Optional[str] = None,
    ) -> PropertyImage:
        """
        Upload one image for a property.

        Raises ValueError if the property does not exist, and raises
        subclasses of StorageError (InvalidFileTypeError, FileTooLargeError,
        etc.) for storage validation failures. On any failure occurring
        after file(s) were written to disk, those file(s) are rolled back
        (deleted) before the exception propagates.
        """
        self._validate_property_exists(db, property_id)
        return self._store_and_persist(
            db, property_id=property_id, file_input=file_input, project_id=project_id
        )

    def upload_multiple(
        self,
        db: Session,
        *,
        property_id: int,
        file_inputs: Sequence[UploadFileInput],
        project_id: Optional[str] = None,
    ) -> BatchUploadSummary:
        """
        Upload multiple images for a property in a single business
        operation (multi-select or drag & drop). Each file succeeds or
        fails independently: a failure on one file rolls back only that
        file's own storage writes and does not abort the remaining files
        in the batch. Partial success is expected and reported.
        """
        self._validate_property_exists(db, property_id)

        results: List[UploadResult] = []
        for file_input in file_inputs:
            try:
                image_obj = self._store_and_persist(
                    db, property_id=property_id, file_input=file_input, project_id=project_id
                )
                results.append(
                    UploadResult(filename=file_input.filename, success=True, property_image=image_obj)
                )
            except (StorageError, ValueError) as exc:
                logger.warning(
                    "Upload failed for file '%s' (property_id=%s): %s",
                    file_input.filename, property_id, exc,
                )
                results.append(
                    UploadResult(filename=file_input.filename, success=False, error=str(exc))
                )

        succeeded = sum(1 for r in results if r.success)
        failed = len(results) - succeeded

        logger.info(
            "Batch upload complete for property_id=%s: %d/%d succeeded, %d failed.",
            property_id, succeeded, len(results), failed,
        )

        return BatchUploadSummary(
            property_id=property_id,
            total=len(results),
            succeeded=succeeded,
            failed=failed,
            results=results,
        )

    # -- Thumbnail path derivation (no DB column invented) -----------------

    @staticmethod
    def derive_thumbnail_relative_path(cached_path: Optional[str]) -> Optional[str]:
        """
        Compute the thumbnail's relative storage path from a PropertyImage's
        `cached_path`, without requiring a dedicated thumbnail-path column.

        Mirrors the exact naming convention used by
        FilesystemStorageProvider.generate_thumbnail(): the 'original'
        path segment becomes 'thumbnail', and '_thumb' is inserted before
        the file extension.

        Returns None if `cached_path` is empty or does not follow the
        expected 'properties/{id}/original/<filename>' layout (for example,
        images imported from an external URL with no local thumbnail).
        """
        if not cached_path:
            return None

        parts = cached_path.split("/")
        try:
            original_index = parts.index(FilesystemStorageProvider.CATEGORY_ORIGINAL)
        except ValueError:
            return None

        filename = parts[-1]
        if "." not in filename:
            return None

        stem, ext = filename.rsplit(".", 1)
        thumb_parts = list(parts)
        thumb_parts[original_index] = FilesystemStorageProvider.CATEGORY_THUMBNAIL
        thumb_parts[-1] = f"{stem}_thumb.{ext}"
        return "/".join(thumb_parts)

    # -- Internal -----------------------------------------------------------

    def _validate_property_exists(self, db: Session, property_id: int) -> None:
        property_obj = crud_property.get(db, property_id)
        if not property_obj:
            raise ValueError(f"Property with ID '{property_id}' does not exist")

    def _store_and_persist(
        self,
        db: Session,
        *,
        property_id: int,
        file_input: UploadFileInput,
        project_id: Optional[str],
    ) -> PropertyImage:
        """
        Save the file (and its thumbnail) to storage, then create the
        PropertyImage metadata row. If the database write fails after the
        file was already written to disk, the stored file(s) are deleted
        (rollback) before re-raising.
        """
        self._storage.ensure_property_directories(property_id)

        original_relative_path: Optional[str] = None
        thumbnail_relative_path: Optional[str] = None

        try:
            original_relative_path = self._storage.save_file(
                property_id=property_id,
                category=self._storage.CATEGORY_ORIGINAL,
                data=file_input.content,
                original_filename=file_input.filename,
            )

            try:
                thumbnail_relative_path = self._storage.generate_thumbnail(
                    property_id=property_id,
                    source_relative_path=original_relative_path,
                )
            except ThumbnailGenerationError as exc:
                # Thumbnailing is best-effort: the original image is still
                # valid and usable even if a preview could not be rendered
                # (e.g. corrupt EXIF, unsupported color profile). Log and
                # continue rather than failing the whole upload.
                logger.warning(
                    "Thumbnail generation failed for property_id=%s file='%s': %s. "
                    "Continuing without a thumbnail.",
                    property_id, file_input.filename, exc,
                )
                thumbnail_relative_path = None

            image_in = PropertyImageCreate(
                property_id=property_id,
                image_type="uploaded",
                image_url=None,
                provider="manual_upload",
                cached_path=original_relative_path,
                project_id=project_id,
                original_file_name=file_input.filename,
                file_size=len(file_input.content),
                file_type=file_input.content_type or self._infer_content_type(file_input.filename),
                image_role=file_input.image_role,
                notes=file_input.notes,
                status="uploaded",
                is_deleted=0,
            )
            image_obj = crud_property_image.create(db, obj_in=image_in)

        except Exception:
            self._rollback_files(original_relative_path, thumbnail_relative_path)
            raise

        logger.info(
            "Uploaded image '%s' for property_id=%s -> cached_path='%s' (thumbnail=%s).",
            file_input.filename, property_id, original_relative_path, thumbnail_relative_path,
        )
        return image_obj

    def _rollback_files(self, *relative_paths: Optional[str]) -> None:
        """Best-effort deletion of already-written files after a failed upload."""
        for relative_path in relative_paths:
            if not relative_path:
                continue
            try:
                self._storage.delete(relative_path=relative_path)
                logger.info("Rolled back stored file '%s' after upload failure.", relative_path)
            except StorageError as exc:
                logger.error("Rollback failed to delete '%s': %s", relative_path, exc)

    @staticmethod
    def _infer_content_type(filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
        }.get(ext, "application/octet-stream")


property_image_upload_service = PropertyImageUploadService()
