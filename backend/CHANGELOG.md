# CHANGELOG.md

## AI-CRE WIMLOGIC V1.0A

---

## [Phase 3A] — Enterprise Image Upload & Workflow Integration — 2026-07-03

### Added

**Storage Infrastructure**
- `FilesystemStorageProvider` — enterprise filesystem storage backend for property images.
  - Per-property directory structure: `uploads/properties/{property_id}/{original|thumbnail|ai|temp}/`.
  - Atomic writes (temp-file + rename) to prevent partial/corrupt files on failure.
  - Automatic thumbnail generation via Pillow, capped at a configurable max dimension.
  - `move_file()` for promoting staged files (e.g. `temp/` → `original/`).
  - Path-traversal protection on all relative-path resolution.
  - Cross-platform: identical behavior on Windows Local and Linux VPS via `pathlib.Path`; stored relative paths always use POSIX separators.

**Business Services**
- `PropertyImageUploadService` — single and multi-file (batch/drag & drop) image upload, with:
  - Extension and file-size validation.
  - Automatic thumbnail generation (non-fatal on failure).
  - Full rollback of stored file(s) if the database write fails.
  - Partial-success semantics for batch uploads (one file's failure never blocks the others).
  - `derive_thumbnail_relative_path()` — deterministic thumbnail path computation with no new database column required.
- `PropertyImageImportService` — image import from external sources, reusing `PropertyImageUploadService` for all validation/storage/persistence/rollback:
  - Local filesystem import (single and batch).
  - URL import (single and batch), with URL scheme restriction and a streamed download size ceiling.
  - Import provenance tagging (`provider`, `image_url`) with its own rollback path if tagging fails after upload.
  - Explicit, non-silent stub methods for future sources: Google Street View, MLS, Google Drive (`UnsupportedImportSourceError`).
- `PropertyReadinessService` — pure computation service (no AI calls, no workflow execution) assessing:
  - Data Completeness (required Property business fields).
  - Image Completeness (Street View / Exterior / Interior category coverage).
  - Workflow Readiness (fields + image categories complete).
  - AI Readiness (Workflow Readiness + no blocked-status images).
  - Missing Information and Suggested Next Actions, generated from the above.

**API**
- Extended `api/property_image.py` with three new endpoints, layered on top of the five pre-existing (unchanged) CRUD endpoints:
  - `POST /api/v1/property-images/upload` — single file upload.
  - `POST /api/v1/property-images/upload/batch` — multi-file upload (HTTP 207, partial success supported).
  - `POST /api/v1/property-images/import-url` — URL-based image import.

**Configuration**
- Added six new additive fields to `core/config.py` (`UPLOAD_ROOT`, `PROPERTIES_SUBDIR`, `MAX_UPLOAD_SIZE_MB`, `ALLOWED_IMAGE_EXTENSIONS`, `THUMBNAIL_MAX_DIMENSION`, `URL_IMPORT_TIMEOUT_SECONDS`). No existing setting was renamed, removed, or had its default changed.

**Documentation**
- `ProjectDocs/API/PROPERTY_IMAGES_API.md` — full endpoint reference.
- `TEST_REPORT.md` — Phase 3A test results.
- `PHASE3A_MANIFEST.md` — deployment checklist.

### Changed
- Nothing existing was modified beyond the additive `core/config.py` fields listed above.

### Deprecated
- Nothing.

### Removed
- Nothing.

### Fixed
- Not applicable — this phase adds new capability rather than fixing existing behavior.

### Security
- Path-traversal guard added to all storage path resolution (`FilesystemStorageProvider.resolve_absolute_path`).
- URL import restricted to `http`/`https` schemes only; streamed downloads are capped mid-transfer to prevent unbounded memory use from an oversized or malicious remote response.

### Known Limitations / Deferred to a Future Phase
- No authentication/authorization on any Property Images endpoint (tracked as a future centralized concern per `04_API_RESPONSE_STANDARD.md`).
- No HTTP endpoint yet exposes `PropertyImageImportService.import_from_local_path()` (service-level capability exists; not wired to the router in this phase, as it was not part of the requested endpoint scope).
- `httpx` and `Pillow` are required runtime dependencies introduced in this phase but were **intentionally not added to `requirements.txt`**, per explicit instruction that dependency management is being handled separately. See `PHASE3A_MANIFEST.md` → Dependency Changes.
- No dedicated endpoint serves a resolved thumbnail URL/path directly; thumbnail paths are derivable client-side/service-side from `cached_path`.

---

*End of Document — CHANGELOG.md*
