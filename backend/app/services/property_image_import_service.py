"""
services/property_image_import_service.py

AI-CRE WIMLOGIC V1 -- Enterprise Business Service
Phase 3A -- Enterprise Image Upload & Workflow Integration

Purpose
-------
Business service responsible for importing Property Images from sources
other than a direct browser upload:
    - Local filesystem import  (a file path already accessible to the
      server, e.g. a batch/administrative import from a mounted drive or
      network share -- distinct from the multipart browser upload handled
      by PropertyImageUploadService)
    - URL import                (downloading an image from an external
      HTTP/HTTPS URL)

Future extension points (NOT implemented in V1.0A; explicit stubs only,
per instruction not to build speculative infrastructure for sources that
do not exist yet):
    - Google Street View
    - MLS
    - Google Drive

Architecture Compliance
-------------------------
- No SQL appears in this file. All persistence goes through
  app.crud.property_image (existing, unmodified).
- All file I/O for storage goes through
  app.integrations.storage.filesystem_storage_provider (Phase 3A).
- This service REUSES app.services.property_image_upload_service for the
  entire validate -> save -> thumbnail -> persist -> rollback pipeline
  rather than duplicating any of that logic. Import-specific behavior
  (reading local bytes, downloading remote bytes, and tagging the
  resulting row with import provenance) is layered on top via a single
  follow-up metadata update through the existing property_image CRUD.
- Property-existence validation is NOT duplicated here: it already occurs
  inside PropertyImageUploadService.upload_single()/upload_multiple().
- File extension and file size validation are NOT duplicated here: they
  already occur inside FilesystemStorageProvider.save_file(), invoked via
  the reused upload service. This service performs only import-source-
  specific checks (URL scheme, download size ceiling while streaming,
  local path existence/readability) that upload_single cannot perform on
  its own, since it never sees a URL or a local filesystem path.

Metadata Tagging
------------------
`cre_property_images.provider` is set to a source-identifying value
("local_import" / "url_import") and, for URL imports,
`cre_property_images.image_url` is set to the original external URL for
reference/audit purposes. `cached_path` continues to store only the
relative on-disk path to the locally persisted copy, exactly as produced
by PropertyImageUploadService -- no filesystem path is ever stored in
`image_url`, and no external URL is ever stored in `cached_path`.

Rollback Behavior
-------------------
The heavy-lifting rollback (storage write + DB row) is already handled
inside PropertyImageUploadService. This service adds one additional
rollback case: if the follow-up provenance-tagging update fails after
upload_single() already succeeded, the newly created row and its stored
file(s) are removed before the exception propagates, so an import never
leaves an orphaned, mis-tagged row behind.

External Dependencies (NOT added to requirements.txt per explicit
instruction; dependency management is being handled separately)
-----------------------------------------------------------------------------
- httpx: required for URL image import.
      import httpx
  Ensure the `httpx` package is installed in the target environment
  before this module is imported.
"""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import List, Optional, Sequence
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.property_image import property_image as crud_property_image
from app.integrations.storage.filesystem_storage_provider import (
    StorageError,
    filesystem_storage_provider,
)
from app.models.property_image import PropertyImage
from app.schemas.property_image import PropertyImageUpdate
from app.services.property_image_upload_service import (
    BatchUploadSummary,
    UploadFileInput,
    UploadResult,
    property_image_upload_service,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ImageImportError(Exception):
    """Base exception for all image import failures."""


class LocalFileImportError(ImageImportError):
    """Raised when a local filesystem source cannot be read for import."""


class URLDownloadError(ImageImportError):
    """Raised when a remote URL image cannot be downloaded."""


class UnsupportedImportSourceError(ImageImportError):
    """Raised when an import source is not yet implemented in this phase."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class PropertyImageImportService:
    """
    Business service for importing property images from local filesystem
    paths and external URLs into enterprise storage, reusing
    PropertyImageUploadService for all validation, persistence, and
    rollback behavior.
    """

    # Source-identifying values written to cre_property_images.provider.
    SOURCE_LOCAL = "local_import"
    SOURCE_URL = "url_import"

    def __init__(self) -> None:
        self._storage = filesystem_storage_provider
        self._upload_service = property_image_upload_service
        self._download_timeout_seconds = settings.URL_IMPORT_TIMEOUT_SECONDS
        self._max_download_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # -- Local filesystem import ---------------------------------------

    def import_from_local_path(
        self,
        db: Session,
        *,
        property_id: int,
        source_path: str,
        project_id: Optional[str] = None,
        image_role: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> PropertyImage:
        """
        Import a single image from a local filesystem path already
        accessible to the server (e.g. an administrative batch import from
        a mounted drive or network share).

        Reuses PropertyImageUploadService.upload_single() for validation,
        storage, thumbnailing, persistence, and rollback. After a
        successful upload, tags the resulting row's `provider` as
        'local_import'. If that tagging step fails, the newly created row
        and its stored file(s) are rolled back.
        """
        file_input = self._read_local_file(source_path, image_role=image_role, notes=notes)

        image_obj = self._upload_service.upload_single(
            db, property_id=property_id, file_input=file_input, project_id=project_id
        )

        return self._tag_import_provenance(db, image_obj=image_obj, provider=self.SOURCE_LOCAL)

    def import_from_local_paths(
        self,
        db: Session,
        *,
        property_id: int,
        source_paths: Sequence[str],
        project_id: Optional[str] = None,
    ) -> BatchUploadSummary:
        """
        Import multiple images from local filesystem paths for a single
        property. Each path succeeds or fails independently; partial
        success is expected and reported, consistent with
        PropertyImageUploadService.upload_multiple().
        """
        results: List[UploadResult] = []
        for source_path in source_paths:
            filename = Path(source_path).name
            try:
                image_obj = self.import_from_local_path(
                    db, property_id=property_id, source_path=source_path, project_id=project_id
                )
                results.append(UploadResult(filename=filename, success=True, property_image=image_obj))
            except (ImageImportError, StorageError, ValueError) as exc:
                logger.warning(
                    "Local import failed for '%s' (property_id=%s): %s",
                    source_path, property_id, exc,
                )
                results.append(UploadResult(filename=filename, success=False, error=str(exc)))

        succeeded = sum(1 for r in results if r.success)
        failed = len(results) - succeeded

        logger.info(
            "Local import batch complete for property_id=%s: %d/%d succeeded, %d failed.",
            property_id, succeeded, len(results), failed,
        )

        return BatchUploadSummary(
            property_id=property_id, total=len(results), succeeded=succeeded, failed=failed, results=results
        )

    # -- URL import -----------------------------------------------------

    def import_from_url(
        self,
        db: Session,
        *,
        property_id: int,
        image_url: str,
        project_id: Optional[str] = None,
        image_role: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> PropertyImage:
        """
        Import a single image by downloading it from an external
        HTTP/HTTPS URL.

        Reuses PropertyImageUploadService.upload_single() for validation,
        storage, thumbnailing, persistence, and rollback. After a
        successful upload, tags the resulting row's `provider` as
        'url_import' and stores the original source URL in `image_url`
        for reference. If that tagging step fails, the newly created row
        and its stored file(s) are rolled back.
        """
        file_input = self._download_url(image_url, image_role=image_role, notes=notes)

        image_obj = self._upload_service.upload_single(
            db, property_id=property_id, file_input=file_input, project_id=project_id
        )

        return self._tag_import_provenance(
            db, image_obj=image_obj, provider=self.SOURCE_URL, source_url=image_url
        )

    def import_from_urls(
        self,
        db: Session,
        *,
        property_id: int,
        image_urls: Sequence[str],
        project_id: Optional[str] = None,
    ) -> BatchUploadSummary:
        """
        Import multiple images by downloading them from external URLs for
        a single property. Each URL succeeds or fails independently;
        partial success is expected and reported, consistent with
        PropertyImageUploadService.upload_multiple().
        """
        results: List[UploadResult] = []
        for image_url in image_urls:
            filename = Path(urlparse(image_url).path).name or image_url
            try:
                image_obj = self.import_from_url(
                    db, property_id=property_id, image_url=image_url, project_id=project_id
                )
                results.append(UploadResult(filename=filename, success=True, property_image=image_obj))
            except (ImageImportError, StorageError, ValueError) as exc:
                logger.warning(
                    "URL import failed for '%s' (property_id=%s): %s",
                    image_url, property_id, exc,
                )
                results.append(UploadResult(filename=filename, success=False, error=str(exc)))

        succeeded = sum(1 for r in results if r.success)
        failed = len(results) - succeeded

        logger.info(
            "URL import batch complete for property_id=%s: %d/%d succeeded, %d failed.",
            property_id, succeeded, len(results), failed,
        )

        return BatchUploadSummary(
            property_id=property_id, total=len(results), succeeded=succeeded, failed=failed, results=results
        )

    # -- Future extension points (V1.0A stubs only) -----------------------

    def import_from_google_street_view(self, db: Session, *, property_id: int, **kwargs) -> PropertyImage:
        """
        Future extension point. Google Street View import is not
        implemented in V1.0A. Intentionally raises so callers fail loudly
        rather than silently no-op.
        """
        raise UnsupportedImportSourceError(
            "Google Street View import is not implemented in AI-CRE WIMLOGIC V1.0A."
        )

    def import_from_mls(self, db: Session, *, property_id: int, **kwargs) -> PropertyImage:
        """
        Future extension point. MLS import is not implemented in V1.0A.
        Intentionally raises so callers fail loudly rather than silently
        no-op.
        """
        raise UnsupportedImportSourceError(
            "MLS import is not implemented in AI-CRE WIMLOGIC V1.0A."
        )

    def import_from_google_drive(self, db: Session, *, property_id: int, **kwargs) -> PropertyImage:
        """
        Future extension point. Google Drive import is not implemented in
        V1.0A. Intentionally raises so callers fail loudly rather than
        silently no-op.
        """
        raise UnsupportedImportSourceError(
            "Google Drive import is not implemented in AI-CRE WIMLOGIC V1.0A."
        )

    # -- Internal: source readers -----------------------------------------

    @staticmethod
    def _read_local_file(
        source_path: str, *, image_role: Optional[str], notes: Optional[str]
    ) -> UploadFileInput:
        """
        Read a local file into memory as an UploadFileInput. Performs only
        source-access checks (existence, is-a-file, readability) --
        extension and size validation are intentionally left to
        FilesystemStorageProvider via the reused upload service, so that
        validation logic is not duplicated.
        """
        path = Path(source_path)

        if not path.exists():
            raise LocalFileImportError(f"Local file not found: '{source_path}'")
        if not path.is_file():
            raise LocalFileImportError(f"Local path is not a file: '{source_path}'")

        try:
            content = path.read_bytes()
        except OSError as exc:
            logger.error("Failed to read local file '%s': %s", source_path, exc)
            raise LocalFileImportError(f"Unable to read local file '{source_path}': {exc}") from exc

        logger.info("Read local file '%s' (%d bytes) for import.", source_path, len(content))

        return UploadFileInput(
            filename=path.name,
            content=content,
            content_type=mimetypes.guess_type(path.name)[0],
            image_role=image_role,
            notes=notes,
        )

    def _download_url(
        self, image_url: str, *, image_role: Optional[str], notes: Optional[str]
    ) -> UploadFileInput:
        """
        Download an image from an external HTTP/HTTPS URL into memory as
        an UploadFileInput. Enforces URL scheme restriction and a streamed
        size ceiling (to avoid unbounded memory use on an oversized or
        malicious response) -- both are import-source-specific safety
        checks that upload_single() cannot perform, since it never sees a
        URL. Extension and final-size validation remain the responsibility
        of FilesystemStorageProvider via the reused upload service.
        """
        parsed = urlparse(image_url)
        if parsed.scheme not in ("http", "https"):
            raise URLDownloadError(
                f"Unsupported URL scheme '{parsed.scheme}' for image import. Only http/https are allowed."
            )

        try:
            with httpx.stream(
                "GET", image_url, timeout=self._download_timeout_seconds, follow_redirects=True
            ) as response:
                response.raise_for_status()

                content_type = response.headers.get("content-type", "").split(";")[0].strip()

                chunks = []
                total_bytes = 0
                for chunk in response.iter_bytes():
                    total_bytes += len(chunk)
                    if total_bytes > self._max_download_bytes:
                        raise URLDownloadError(
                            f"Remote image at '{image_url}' exceeds maximum allowed download size "
                            f"({settings.MAX_UPLOAD_SIZE_MB} MB)."
                        )
                    chunks.append(chunk)
                content = b"".join(chunks)

        except httpx.HTTPStatusError as exc:
            logger.error("URL import received HTTP error for '%s': %s", image_url, exc)
            raise URLDownloadError(
                f"Remote server returned an error status for '{image_url}': {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("URL import request failed for '%s': %s", image_url, exc)
            raise URLDownloadError(f"Failed to download image from '{image_url}': {exc}") from exc

        filename = self._derive_filename_from_url(image_url, content_type)

        logger.info(
            "Downloaded '%s' (%d bytes, content-type=%s) for import.",
            image_url, len(content), content_type or "unknown",
        )

        return UploadFileInput(
            filename=filename,
            content=content,
            content_type=content_type or None,
            image_role=image_role,
            notes=notes,
        )

    @staticmethod
    def _derive_filename_from_url(image_url: str, content_type: str) -> str:
        """
        Derive a filename for a downloaded image. Prefers the URL's path
        segment if it has a plausible extension; otherwise falls back to a
        generic name with an extension guessed from the response
        Content-Type.
        """
        path_name = Path(urlparse(image_url).path).name
        if path_name and "." in path_name:
            return path_name

        guessed_ext = mimetypes.guess_extension(content_type) if content_type else None
        return f"imported_image{guessed_ext or '.jpg'}"

    # -- Internal: provenance tagging with rollback -------------------------

    def _tag_import_provenance(
        self,
        db: Session,
        *,
        image_obj: PropertyImage,
        provider: str,
        source_url: Optional[str] = None,
    ) -> PropertyImage:
        """
        Apply import-source metadata (`provider`, and for URL imports the
        original `image_url`) to a PropertyImage row that was just created
        by PropertyImageUploadService. If this update fails, the row and
        its already-stored file(s) are rolled back so no orphaned,
        mis-tagged row is left behind.
        """
        update_in = PropertyImageUpdate(provider=provider, image_url=source_url)

        try:
            updated_obj = crud_property_image.update(db, db_obj=image_obj, obj_in=update_in)
        except Exception:
            logger.error(
                "Failed to tag import provenance for property_image id=%s; rolling back.",
                image_obj.id,
            )
            self._rollback_imported_image(db, image_obj=image_obj)
            raise

        return updated_obj

    def _rollback_imported_image(self, db: Session, *, image_obj: PropertyImage) -> None:
        """
        Remove a PropertyImage row and its stored file(s) after a failure
        occurring strictly after PropertyImageUploadService already
        persisted them.
        """
        cached_path = image_obj.cached_path
        try:
            crud_property_image.remove(db, id=image_obj.id)
        except Exception as exc:
            logger.error("Rollback failed to remove property_image id=%s: %s", image_obj.id, exc)

        if cached_path:
            try:
                self._storage.delete(relative_path=cached_path)
            except StorageError as exc:
                logger.error("Rollback failed to delete stored file '%s': %s", cached_path, exc)

            thumb_path = self._upload_service.derive_thumbnail_relative_path(cached_path)
            if thumb_path:
                try:
                    self._storage.delete(relative_path=thumb_path)
                except StorageError as exc:
                    logger.error("Rollback failed to delete thumbnail '%s': %s", thumb_path, exc)


property_image_import_service = PropertyImageImportService()
