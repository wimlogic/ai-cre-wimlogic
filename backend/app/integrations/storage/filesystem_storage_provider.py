"""
integrations/storage/filesystem_storage_provider.py

AI-CRE WIMLOGIC V1 -- Enterprise Storage Integration
Phase 3A -- Enterprise Image Upload & Workflow Integration

Purpose
-------
Provides the filesystem-backed storage implementation used to persist
business image assets. Handles raw file persistence, thumbnail generation,
inter-category file moves, path resolution, and safe deletion. Used by
PropertyImageUploadService and PropertyImageImportService (see services/).

Directory Layout
-----------------
All business image assets are organized per-property under UPLOAD_ROOT:

    <UPLOAD_ROOT>/
        <PROPERTIES_SUBDIR>/
            <property_id>/
                original/    -- as-uploaded / as-imported source files
                thumbnail/   -- generated thumbnails
                ai/          -- AI-referenced or AI-returned images (future use)
                temp/        -- staging area for in-progress imports/uploads

Only paths relative to UPLOAD_ROOT are ever persisted to the database
(e.g. cre_property_images.cached_path). Absolute paths are resolved on
demand and never leave this module.

Cross-Platform Behavior
------------------------
This module uses pathlib.Path exclusively for all path construction and
resolution so that storage behaves identically on Windows development
machines and Linux VPS production hosts. Relative paths persisted to the
database always use POSIX-style forward slashes (via Path.as_posix()),
regardless of host OS, so stored paths never mix separators between
environments.

Configuration
-------------
All storage locations and limits are read from app.core.config.settings,
which in turn reads from .env:

    UPLOAD_ROOT                 (default: "uploads")
    PROPERTIES_SUBDIR           (default: "properties")
    MAX_UPLOAD_SIZE_MB          (default: 25)
    ALLOWED_IMAGE_EXTENSIONS    (default: "jpg,jpeg,png,webp")
    THUMBNAIL_MAX_DIMENSION     (default: 400)
    URL_IMPORT_TIMEOUT_SECONDS  (default: 15)

The four per-property category folder names (original, thumbnail, ai, temp)
are fixed structural constants, not environment-configurable, since they
define the on-disk contract other services rely on.

Nothing in this module hardcodes a filesystem path.

External Dependencies (NOT added to requirements.txt per explicit
instruction; dependency management is being handled separately)
-----------------------------------------------------------------------------
- Pillow (PIL): required for thumbnail generation.
      from PIL import Image, UnidentifiedImageError
  Ensure the `pillow` package is installed in the target environment before
  this module is imported.

Provider Scope (V1.0A)
------------------------
Only FilesystemStorageProvider is implemented. No abstract storage
interface is introduced at this stage -- a second concrete provider (e.g.
AWS S3, Azure Blob Storage) would justify extracting a shared contract at
that time, per explicit instruction not to design for a hypothetical
second implementation before one actually exists.
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from PIL import Image, UnidentifiedImageError

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class StorageError(Exception):
    """Base exception for all storage integration failures."""


class InvalidFileTypeError(StorageError):
    """Raised when a file extension is not present in the enterprise allow-list."""


class FileTooLargeError(StorageError):
    """Raised when a file exceeds the configured maximum upload size."""


class FileNotFoundInStorageError(StorageError):
    """Raised when an operation references a relative path that does not exist on disk."""


class ThumbnailGenerationError(StorageError):
    """Raised when Pillow is unable to generate a thumbnail for a given source image."""


class InvalidCategoryError(StorageError):
    """Raised when an operation references a category outside the fixed enterprise set."""


# ---------------------------------------------------------------------------
# Filesystem Implementation
# ---------------------------------------------------------------------------

class FilesystemStorageProvider:
    """
    Enterprise filesystem storage backend for property image assets.

    Root directory layout (relative to settings.UPLOAD_ROOT):

        <UPLOAD_ROOT>/
            <PROPERTIES_SUBDIR>/
                <property_id>/
                    original/
                    thumbnail/
                    ai/
                    temp/

    Only paths relative to UPLOAD_ROOT are ever persisted to the database.
    Absolute paths are resolved on demand and never leave this module.
    """

    # Fixed structural category names. Not environment-configurable.
    CATEGORY_ORIGINAL = "original"
    CATEGORY_THUMBNAIL = "thumbnail"
    CATEGORY_AI = "ai"
    CATEGORY_TEMP = "temp"
    CATEGORIES = (CATEGORY_ORIGINAL, CATEGORY_THUMBNAIL, CATEGORY_AI, CATEGORY_TEMP)

    # Maps normalized (lowercase, no dot) extensions to the Pillow format
    # string required by Image.save(). Extended here if
    # settings.ALLOWED_IMAGE_EXTENSIONS is broadened in the future.
    _PILLOW_FORMAT_MAP = {
        "jpg": "JPEG",
        "jpeg": "JPEG",
        "png": "PNG",
        "webp": "WEBP",
    }

    def __init__(self) -> None:
        self._root = Path(settings.UPLOAD_ROOT).resolve()
        self._properties_subdir = settings.PROPERTIES_SUBDIR
        self._allowed_extensions = {
            ext.strip().lower().lstrip(".")
            for ext in settings.ALLOWED_IMAGE_EXTENSIONS.split(",")
            if ext.strip()
        }
        self._max_upload_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        self._thumbnail_max_dimension = settings.THUMBNAIL_MAX_DIMENSION

        self._ensure_directory(self._root)
        self._ensure_directory(self._root / self._properties_subdir)

        logger.info(
            "FilesystemStorageProvider initialized. root=%s properties_subdir=%s "
            "max_upload_mb=%s allowed_ext=%s",
            self._root,
            self._properties_subdir,
            settings.MAX_UPLOAD_SIZE_MB,
            sorted(self._allowed_extensions),
        )

    # -- Directory helpers ---------------------------------------------------

    @staticmethod
    def _ensure_directory(path: Path) -> None:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error("Failed to create storage directory %s: %s", path, exc)
            raise StorageError(f"Unable to create storage directory '{path}': {exc}") from exc

    def _property_dir(self, property_id: int) -> Path:
        return self._root / self._properties_subdir / str(property_id)

    def _validate_category(self, category: str) -> str:
        if category not in self.CATEGORIES:
            raise InvalidCategoryError(
                f"Category '{category}' is not permitted. Allowed: {list(self.CATEGORIES)}"
            )
        return category

    def _category_dir(self, property_id: int, category: str) -> Path:
        self._validate_category(category)
        category_dir = self._property_dir(property_id) / category
        self._ensure_directory(category_dir)
        return category_dir

    def ensure_property_directories(self, property_id: int) -> None:
        """
        Create the full category directory set (original, thumbnail, ai,
        temp) for a given property, if it does not already exist. Safe to
        call repeatedly.
        """
        for category in self.CATEGORIES:
            self._category_dir(property_id, category)
        logger.info("Ensured property directory set for property_id=%s at %s", property_id, self._property_dir(property_id))

    # -- Validation ------------------------------------------------------------

    def validate_extension(self, filename: str) -> str:
        """
        Validate a filename's extension against the enterprise allow-list.
        Returns the normalized lowercase extension (no leading dot) on success.
        """
        ext = Path(filename).suffix.lower().lstrip(".")
        if not ext or ext not in self._allowed_extensions:
            logger.warning("Rejected file '%s': extension '%s' not permitted.", filename, ext)
            raise InvalidFileTypeError(
                f"File extension '.{ext}' is not permitted. Allowed: {sorted(self._allowed_extensions)}"
            )
        return ext

    def validate_size(self, size_bytes: int) -> None:
        """Validate a file's byte size against the configured maximum upload size."""
        if size_bytes <= 0:
            raise StorageError("File is empty and cannot be stored.")
        if size_bytes > self._max_upload_bytes:
            raise FileTooLargeError(
                f"File size {size_bytes} bytes exceeds maximum of {self._max_upload_bytes} bytes "
                f"({settings.MAX_UPLOAD_SIZE_MB} MB)."
            )

    # -- Path helpers ------------------------------------------------------

    def generate_unique_filename(self, original_filename: str, ext: Optional[str] = None) -> str:
        """Generate a collision-safe filename, preserving the validated extension."""
        resolved_ext = ext or self.validate_extension(original_filename)
        return f"{uuid.uuid4().hex}.{resolved_ext}"

    def resolve_absolute_path(self, *, relative_path: str) -> Path:
        """
        Resolve a database-stored relative path to an absolute filesystem path.
        Guards against path traversal outside UPLOAD_ROOT.
        """
        candidate = (self._root / relative_path).resolve()
        try:
            candidate.relative_to(self._root)
        except ValueError as exc:
            logger.error("Path traversal attempt blocked for relative_path=%s", relative_path)
            raise StorageError(f"Invalid storage path '{relative_path}'.") from exc
        return candidate

    def _to_relative(self, absolute_path: Path) -> str:
        """Convert an absolute path under UPLOAD_ROOT to a POSIX-style relative path."""
        return absolute_path.relative_to(self._root).as_posix()

    def _pillow_format_for(self, absolute_path: Path) -> str:
        ext = absolute_path.suffix.lower().lstrip(".")
        pillow_format = self._PILLOW_FORMAT_MAP.get(ext)
        if not pillow_format:
            raise ThumbnailGenerationError(
                f"No Pillow format mapping for extension '.{ext}'. "
                f"Update _PILLOW_FORMAT_MAP if this extension should be supported."
            )
        return pillow_format

    # -- Core file operations --------------------------------------------

    def save_file(
        self,
        *,
        property_id: int,
        category: str,
        data: bytes,
        filename: Optional[str] = None,
        original_filename: Optional[str] = None,
    ) -> str:
        """
        Persist raw bytes under
        <UPLOAD_ROOT>/<PROPERTIES_SUBDIR>/<property_id>/<category>/<filename>
        and return the stored relative path (POSIX-style, safe for both
        Windows and Linux hosts).

        If `filename` is not supplied, a collision-safe filename is generated
        from `original_filename`'s extension. Writes are performed to a
        temporary ".part" file and atomically renamed on success so a failed
        write never leaves a corrupt/partial file at the final path.
        """
        self.validate_size(len(data))

        if filename is None:
            if not original_filename:
                raise StorageError("Either 'filename' or 'original_filename' must be provided.")
            filename = self.generate_unique_filename(original_filename)
        else:
            self.validate_extension(filename)

        target_dir = self._category_dir(property_id, category)
        target_path = target_dir / filename
        temp_path = target_dir / f"{filename}.part"

        try:
            with open(temp_path, "wb") as f:
                f.write(data)
            os.replace(temp_path, target_path)
        except OSError as exc:
            logger.error("Failed to write file to %s: %s", target_path, exc)
            self._safe_unlink(temp_path)
            self._safe_unlink(target_path)
            raise StorageError(f"Failed to save file '{filename}': {exc}") from exc

        relative_path = self._to_relative(target_path)
        logger.info(
            "Stored file '%s' (%d bytes) for property_id=%s category=%s at relative path '%s'.",
            filename, len(data), property_id, category, relative_path,
        )
        return relative_path

    def generate_thumbnail(
        self,
        *,
        property_id: int,
        source_relative_path: str,
        filename: Optional[str] = None,
    ) -> str:
        """
        Generate a thumbnail for a stored image and persist it under
        <UPLOAD_ROOT>/<PROPERTIES_SUBDIR>/<property_id>/thumbnail/.
        Returns the thumbnail's relative path.

        The thumbnail is written to a temporary file with the correct final
        extension (Pillow requires a resolvable format/extension to save
        correctly) and atomically renamed into place on success.
        """
        source_absolute = self.resolve_absolute_path(relative_path=source_relative_path)
        if not source_absolute.is_file():
            raise FileNotFoundInStorageError(f"Source image not found: '{source_relative_path}'")

        thumb_filename = filename or f"{source_absolute.stem}_thumb{source_absolute.suffix}"
        pillow_format = self._pillow_format_for(Path(thumb_filename))

        thumb_dir = self._category_dir(property_id, self.CATEGORY_THUMBNAIL)
        thumb_path = thumb_dir / thumb_filename
        # Keep the real extension before the .part suffix so any tooling that
        # inspects the temp file mid-write still sees a sane extension.
        temp_path = thumb_dir / f"{thumb_path.stem}.part{thumb_path.suffix}"

        try:
            with Image.open(source_absolute) as img:
                img.thumbnail((self._thumbnail_max_dimension, self._thumbnail_max_dimension))
                if pillow_format == "JPEG" and img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(temp_path, format=pillow_format)
            os.replace(temp_path, thumb_path)
        except (UnidentifiedImageError, OSError) as exc:
            logger.error("Thumbnail generation failed for %s: %s", source_relative_path, exc)
            self._safe_unlink(temp_path)
            self._safe_unlink(thumb_path)
            raise ThumbnailGenerationError(
                f"Unable to generate thumbnail for '{source_relative_path}': {exc}"
            ) from exc

        relative_thumb_path = self._to_relative(thumb_path)
        logger.info("Generated thumbnail '%s' from source '%s'.", relative_thumb_path, source_relative_path)
        return relative_thumb_path

    def move_file(
        self,
        *,
        source_relative_path: str,
        property_id: int,
        target_category: str,
        filename: Optional[str] = None,
    ) -> str:
        """
        Move an existing stored file (typically staged in `temp/`) into
        another category directory for the same property, e.g. promoting a
        validated temp download into `original/`. Returns the new relative
        path.

        Uses shutil.move rather than os.replace so the operation remains
        correct even in deployments where category directories could span
        filesystem boundaries (e.g. mounted network storage).
        """
        source_absolute = self.resolve_absolute_path(relative_path=source_relative_path)
        if not source_absolute.is_file():
            raise FileNotFoundInStorageError(f"File to move not found: '{source_relative_path}'")

        target_dir = self._category_dir(property_id, target_category)
        target_filename = filename or source_absolute.name
        target_path = target_dir / target_filename

        try:
            shutil.move(str(source_absolute), str(target_path))
        except OSError as exc:
            logger.error("Failed to move '%s' to '%s': %s", source_relative_path, target_path, exc)
            raise StorageError(f"Failed to move file '{source_relative_path}': {exc}") from exc

        relative_path = self._to_relative(target_path)
        logger.info("Moved file '%s' -> '%s'.", source_relative_path, relative_path)
        return relative_path

    def delete(self, *, relative_path: str) -> bool:
        """Delete a stored file. Returns True if removed, False if it did not exist."""
        absolute_path = self.resolve_absolute_path(relative_path=relative_path)
        if not absolute_path.is_file():
            logger.warning("Delete requested for missing file: '%s'", relative_path)
            return False
        try:
            absolute_path.unlink()
            logger.info("Deleted stored file: '%s'", relative_path)
            return True
        except OSError as exc:
            logger.error("Failed to delete file '%s': %s", relative_path, exc)
            raise StorageError(f"Failed to delete file '{relative_path}': {exc}") from exc

    def exists(self, *, relative_path: str) -> bool:
        """Return True if the relative path currently exists on disk."""
        try:
            absolute_path = self.resolve_absolute_path(relative_path=relative_path)
        except StorageError:
            return False
        return absolute_path.is_file()

    # -- Internal helpers ---------------------------------------------------

    @staticmethod
    def _safe_unlink(path: Path) -> None:
        """Best-effort cleanup of a partial/temp file. Never raises."""
        try:
            if path.exists():
                path.unlink()
        except OSError as exc:
            logger.warning("Failed to clean up temp file '%s': %s", path, exc)


# ---------------------------------------------------------------------------
# Module-level singleton (consistent with the existing service pattern, e.g.
# property_image_service = PropertyImageService() in services/property_image_service.py)
# ---------------------------------------------------------------------------

filesystem_storage_provider = FilesystemStorageProvider()
