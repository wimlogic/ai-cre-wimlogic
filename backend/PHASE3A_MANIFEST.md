# PHASE3A_MANIFEST.md

## AI-CRE WIMLOGIC V1.0A — Phase 3A Deployment Manifest

**Phase:** 3A — Enterprise Image Upload & Workflow Integration
**Date:** 2026-07-03
**Status:** Ready for deployment review

This document is the authoritative deployment checklist for Phase 3A. It enumerates every file added or changed, every configuration and dependency change, and every API surface change, so this phase can be deployed by replacing files directly without ambiguity.

---

## NEW FILES

```
backend/app/integrations/__init__.py
backend/app/integrations/storage/__init__.py
backend/app/integrations/storage/filesystem_storage_provider.py
backend/app/services/property_image_upload_service.py
backend/app/services/property_image_import_service.py
backend/app/services/property_readiness_service.py
```

```
ProjectDocs/API/PROPERTY_IMAGES_API.md
TEST_REPORT.md
CHANGELOG.md
PHASE3A_MANIFEST.md   (this file)
```

---

## MODIFIED FILES

| File | Nature of Change |
|---|---|
| `backend/app/api/property_image.py` | Extended. Original 5 CRUD endpoints (`POST /`, `GET /{id}`, `GET /`, `PUT /{id}`, `DELETE /{id}`) preserved byte-identical. 3 new endpoints added: `POST /upload`, `POST /upload/batch`, `POST /import-url`. |
| `backend/app/core/config.py` | Extended (additive only). 6 new `Settings` fields added for storage configuration. No existing field renamed, removed, retyped, or had its default changed. See CONFIGURATION CHANGES below. |

**No other file in the backend tree was modified.**

---

## UNCHANGED FILES

All remaining backend files are unchanged from the originally uploaded `AI_CRE_Backend_V1A.zip`, including but not limited to:

```
backend/app/main.py
backend/app/db/database.py
backend/app/db/session.py
backend/app/db/base.py
backend/app/api/__init__.py
backend/app/api/ai_orchestration.py
backend/app/api/api_usage_log.py
backend/app/api/concept_design.py
backend/app/api/estimate.py
backend/app/api/generated_asset.py
backend/app/api/project.py
backend/app/api/project_property.py
backend/app/api/property.py
backend/app/api/property_analysis_report.py
backend/app/api/renovation_scenario.py
backend/app/api/result_section.py
backend/app/api/scan.py
backend/app/api/scan_job.py
backend/app/api/scan_property.py
backend/app/api/workflow_event.py
backend/app/api/workflow_execution.py
backend/app/api/workflow_result.py
backend/app/api/zoning_note.py

backend/app/crud/*.py                      (all 18 modules, including property_image.py)
backend/app/models/*.py                    (all 18 modules)
backend/app/schemas/*.py                   (all 18 modules)

backend/app/services/ai_orchestration_service.py
backend/app/services/generated_asset_service.py
backend/app/services/project_service.py
backend/app/services/property_image_service.py
backend/app/services/property_service.py
backend/app/services/workflow_execution_service.py
backend/app/services/workflow_result_service.py
```

Verified via byte-for-byte diff against the originally uploaded ZIP for `core/config.py` (prior to the additive change documented below) and via verbatim substring match for the preserved portion of `api/property_image.py`.

---

## REMOVED FILES

**None.** No file was deleted or renamed in Phase 3A.

---

## CONFIGURATION CHANGES

**File:** `backend/app/core/config.py`
**Type:** Additive only — appended inside the existing `Settings` class, immediately before the existing `DATABASE_URL` property.

```python
UPLOAD_ROOT: str = "uploads"
PROPERTIES_SUBDIR: str = "properties"
MAX_UPLOAD_SIZE_MB: int = 25
ALLOWED_IMAGE_EXTENSIONS: str = "jpg,jpeg,png,webp"
THUMBNAIL_MAX_DIMENSION: int = 400
URL_IMPORT_TIMEOUT_SECONDS: int = 15
```

| Setting | Default | Purpose |
|---|---|---|
| `UPLOAD_ROOT` | `"uploads"` | Root directory for all filesystem-stored image assets, relative to the application working directory. |
| `PROPERTIES_SUBDIR` | `"properties"` | Sub-directory under `UPLOAD_ROOT` containing one folder per property. |
| `MAX_UPLOAD_SIZE_MB` | `25` | Maximum accepted file size per upload/import, in megabytes. |
| `ALLOWED_IMAGE_EXTENSIONS` | `"jpg,jpeg,png,webp"` | Comma-separated allow-list of accepted file extensions. |
| `THUMBNAIL_MAX_DIMENSION` | `400` | Longest edge, in pixels, for generated thumbnails. |
| `URL_IMPORT_TIMEOUT_SECONDS` | `15` | Timeout for outbound URL image import downloads. |

**Deployment action required:** Add corresponding entries to the environment's `.env` file if non-default values are desired. If `.env` does not define these keys, the defaults above apply automatically — no `.env` changes are strictly required to deploy.

**Deployment action required (filesystem):** Ensure the process has write access to create `UPLOAD_ROOT` (default `uploads/`) relative to the application's working directory, on both Windows Local and Linux VPS targets. The application creates this directory automatically on `FilesystemStorageProvider` initialization if it does not exist.

---

## DEPENDENCY CHANGES

**`requirements.txt` was intentionally NOT modified in Phase 3A**, per explicit instruction that dependency management is being handled separately.

The following two packages are **required at runtime** by Phase 3A code and must be installed in the target environment before deployment, even though they are not yet reflected in `requirements.txt`:

| Package | Required By | Suggested Minimum Version |
|---|---|---|
| `Pillow` | `integrations/storage/filesystem_storage_provider.py` (thumbnail generation) | `>=10.0.0` |
| `httpx` | `services/property_image_import_service.py` (URL import) | `>=0.27.0` |

**Deployment action required:** Install these two packages in the target environment (`pip install Pillow httpx` or equivalent), and add them to `requirements.txt` when dependency management for this phase is finalized. Deployment will fail at import time (`ModuleNotFoundError`) without them.

No other dependency was added, upgraded, or removed.

---

## DATABASE CHANGES

**None.** No table was created, altered, or dropped. No column was added, removed, or retyped. Phase 3A stores all data using the existing `cre_property_images` schema — specifically the pre-existing `cached_path`, `provider`, `image_url`, `image_type`, `image_role`, `original_file_name`, `file_size`, `file_type`, `status`, and `notes` columns.

No `ai_cre_schema.sql` change is required for this phase.

---

## API ENDPOINTS ADDED

| Method | Path | Router File |
|---|---|---|
| `POST` | `/api/v1/property-images/upload` | `backend/app/api/property_image.py` |
| `POST` | `/api/v1/property-images/upload/batch` | `backend/app/api/property_image.py` |
| `POST` | `/api/v1/property-images/import-url` | `backend/app/api/property_image.py` |

Full request/response contracts: see `ProjectDocs/API/PROPERTY_IMAGES_API.md`.

---

## API ENDPOINTS MODIFIED

**None.** The five pre-existing Property Images endpoints (`POST /`, `GET /{id}`, `GET /`, `PUT /{id}`, `DELETE /{id}`) are unchanged in request payload, response schema, and status codes.

---

## SERVICES CREATED

| Service | File | Singleton Export |
|---|---|---|
| `PropertyImageUploadService` | `backend/app/services/property_image_upload_service.py` | `property_image_upload_service` |
| `PropertyImageImportService` | `backend/app/services/property_image_import_service.py` | `property_image_import_service` |
| `PropertyReadinessService` | `backend/app/services/property_readiness_service.py` | `property_readiness_service` |

All three follow the existing module-level singleton pattern used throughout the codebase (e.g. `property_image_service = PropertyImageService()`).

---

## INTEGRATIONS CREATED

| Integration | File | Singleton Export |
|---|---|---|
| `FilesystemStorageProvider` | `backend/app/integrations/storage/filesystem_storage_provider.py` | `filesystem_storage_provider` |

No abstract storage interface was introduced in Phase 3A. `FilesystemStorageProvider` is a standalone concrete class; an abstract contract will only be introduced if and when a second concrete storage provider (e.g. AWS S3, Azure Blob Storage) is actually implemented.

---

## PRE-DEPLOYMENT VALIDATION SIGN-OFF

| Check | Status |
|---|---|
| Every Python file in the backend compiles (`py_compile`) — 95/95 | ✅ PASS |
| Every new/modified API endpoint verified via FastAPI `TestClient` — 18/18 | ✅ PASS |
| No duplicate business logic (verified via source inspection — see `TEST_REPORT.md` §5) | ✅ PASS |
| Original CRUD endpoints in `api/property_image.py` verified byte-identical | ✅ PASS |
| `core/config.py` change verified additive-only via diff against original upload | ✅ PASS |
| Rollback verified (upload + import failure paths) | ✅ PASS |
| Backward compatibility preserved (no renamed APIs, models, schemas, or CRUD modules) | ✅ PASS |

**This manifest reflects a backend that has passed full validation and is ready for the `Phase3A_Backend_Image_APIs.zip` package to be deployed.**

---

*End of Document — PHASE3A_MANIFEST.md*
