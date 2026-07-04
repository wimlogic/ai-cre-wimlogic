# PROPERTY_IMAGES_API.md

## AI-CRE WIMLOGIC V1.0A — Property Images API Reference

**Module:** `backend/app/api/property_image.py`
**Base Path:** `/api/v1/property-images`
**Phase:** 3A — Enterprise Image Upload & Workflow Integration
**Status:** Locked

---

## Authentication

No authentication or authorization layer is implemented in Phase 3A. Per `04_API_RESPONSE_STANDARD.md` (Section 24, Authorization Architecture), business endpoints shall never implement authentication logic directly — authentication/authorization is a future, centralized concern (RBAC / permission-based / tenant isolation) and is out of scope for this module. All endpoints below are currently open at the application layer; access control is expected to be added later via shared middleware, not per-endpoint logic.

---

## Endpoint Summary

| # | Method | Path | Purpose | Status Codes | Frontend Module |
|---|--------|------|---------|---------------|------------------|
| 1 | POST | `/api/v1/property-images/` | Create a property image metadata row directly | 201, 422 | Property Images — administrative/system use |
| 2 | GET | `/api/v1/property-images/{id}` | Get image details | 200, 404 | Property Images — Image Details Panel |
| 3 | GET | `/api/v1/property-images/` | List images (filterable, supports `property_id`) | 200 | Property Images — Image Gallery |
| 4 | PUT | `/api/v1/property-images/{id}` | Update image metadata | 200, 404 | Property Images — Image Details Panel / Image Actions |
| 5 | DELETE | `/api/v1/property-images/{id}` | Delete image (soft or hard) | 200, 404 | Property Images — Image Actions |
| 6 | POST | `/api/v1/property-images/upload` | Single file upload | 201, 400, 422, 500 | Property Images — Upload Images (single) |
| 7 | POST | `/api/v1/property-images/upload/batch` | Multi-file / drag & drop upload | 207, 400, 500 | Property Images — Upload Images (drag & drop / multi-select) |
| 8 | POST | `/api/v1/property-images/import-url` | Import image from external URL | 201, 400, 422, 500 | Property Images — Import Images |

---

## 1. Create Property Image (metadata only)

**Method:** `POST`
**Path:** `/api/v1/property-images/`
**Purpose:** Creates a `cre_property_images` row directly from a fully-formed payload (no file upload). Intended for administrative/system use — e.g. registering an already-known `image_url` (Street View, satellite, parcel map) without going through the upload pipeline.

### Request Payload — `PropertyImageCreate`

```json
{
  "property_id": 1,
  "image_type": "street_view",
  "image_url": "https://maps.googleapis.com/...",
  "provider": "google_street_view",
  "heading": 180.0,
  "pitch": 0.0,
  "fov": 90.0,
  "cached_path": null,
  "project_id": "PRJ-001",
  "original_file_name": null,
  "file_size": null,
  "file_type": null,
  "image_role": "street_view",
  "notes": null,
  "status": "ready",
  "is_deleted": 0
}
```

### Response — `PropertyImageResponse` (HTTP 201)

```json
{
  "id": 42,
  "property_id": 1,
  "image_type": "street_view",
  "image_url": "https://maps.googleapis.com/...",
  "provider": "google_street_view",
  "heading": 180.0,
  "pitch": 0.0,
  "fov": 90.0,
  "cached_path": null,
  "last_checked_at": null,
  "project_id": "PRJ-001",
  "original_file_name": null,
  "file_size": null,
  "file_type": null,
  "image_role": "street_view",
  "notes": null,
  "status": "ready",
  "is_deleted": 0,
  "created_at": "2026-07-03T12:00:00"
}
```

**Status Codes:** `201 Created` · `422 Unprocessable Entity` (schema validation failure)

**Frontend Module:** Not directly wired to a gallery action; reserved for system/administrative flows (e.g. future MLS/Street View auto-population).

---

## 2. Get Property Image Details

**Method:** `GET`
**Path:** `/api/v1/property-images/{id}`

### Response — `PropertyImageResponse` (HTTP 200)

Same shape as Section 1's response.

**Status Codes:** `200 OK` · `404 Not Found` (`"Property image not found"`)

**Frontend Module:** Property Images → **Image Details Panel** (General Information → Preview → Metadata → AI Status → Workflow Usage → Business Notes, per `08_PROPERTY_IMAGES.md`).

### Example Request

```
GET /api/v1/property-images/42
```

---

## 3. List Property Images

**Method:** `GET`
**Path:** `/api/v1/property-images/`

### Query Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 100 (max 500) | Page size |
| `property_id` | int (optional) | — | Filter to a single property |
| `project_id` | string (optional) | — | Filter to a project |
| `image_type` | string (optional) | — | `street_view` \| `satellite` \| `parcel_map` \| `uploaded` |
| `include_deleted` | bool | false | Include soft-deleted rows |
| `search` | string (optional) | — | Matches `provider`, `notes`, `original_file_name` |

### Response — `PropertyImageListResponse` (HTTP 200)

```json
{
  "count": 3,
  "items": [
    { "id": 42, "property_id": 1, "image_type": "uploaded", "cached_path": "properties/1/original/a1b2c3.jpg", "...": "..." },
    { "id": 43, "property_id": 1, "image_type": "uploaded", "cached_path": "properties/1/original/d4e5f6.png", "...": "..." }
  ]
}
```

**Status Codes:** `200 OK`

**Frontend Module:** Property Images → **Image Gallery** (Gallery View / Grid View, lazy loading, infinite scrolling per `08_PROPERTY_IMAGES.md`). Also powers the **Business Summary KPI cards** ("Total Images", "Missing Categories") via repeated filtered calls.

### Example Request

```
GET /api/v1/property-images/?property_id=1&include_deleted=false&limit=50
```

---

## 4. Update Property Image Metadata

**Method:** `PUT`
**Path:** `/api/v1/property-images/{id}`

### Request Payload — `PropertyImageUpdate` (all fields optional)

```json
{
  "image_role": "exterior_front",
  "notes": "Primary listing photo",
  "status": "ready"
}
```

### Response — `PropertyImageResponse` (HTTP 200)

Full updated row, same shape as Section 1.

**Status Codes:** `200 OK` · `404 Not Found`

**Frontend Module:** Property Images → **Image Details Panel** and **Image Actions** (e.g. "Set Primary Image" writes `image_role`; business note edits write `notes`).

---

## 5. Delete Property Image

**Method:** `DELETE`
**Path:** `/api/v1/property-images/{id}`

### Query Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `soft` | bool | true | `true` sets `is_deleted=1`; `false` permanently removes the database row (the underlying stored file is **not** deleted by this endpoint in either mode — file lifecycle is managed separately by the storage layer) |

### Response — `DeleteResponse` (HTTP 200)

```json
{ "success": true }
```

**Status Codes:** `200 OK` · `404 Not Found`

**Frontend Module:** Property Images → **Image Actions** ("Delete").

### Example Request

```
DELETE /api/v1/property-images/42?soft=true
```

---

## 6. Upload Single Image

**Method:** `POST`
**Path:** `/api/v1/property-images/upload`
**Content-Type:** `multipart/form-data`

### Request Payload (form fields)

| Field | Type | Required | Description |
|---|---|---|---|
| `property_id` | int | Yes | Target property |
| `file` | file | Yes | Image file (`.jpg`, `.jpeg`, `.png`, `.webp`) |
| `project_id` | string | No | Business project identifier |
| `image_role` | string | No | e.g. `exterior`, `interior` |
| `notes` | string | No | Free-text business notes |

### Example Request (curl)

```bash
curl -X POST "http://localhost:8000/api/v1/property-images/upload" \
  -F "property_id=1" \
  -F "image_role=exterior" \
  -F "file=@front_facade.jpg;type=image/jpeg"
```

### Response — `PropertyImageResponse` (HTTP 201)

```json
{
  "id": 44,
  "property_id": 1,
  "image_type": "uploaded",
  "image_url": null,
  "provider": "manual_upload",
  "cached_path": "properties/1/original/9f3a2b1c8e4d4a2f9b1e2c3d4e5f6a7b.jpg",
  "project_id": null,
  "original_file_name": "front_facade.jpg",
  "file_size": 482113,
  "file_type": "image/jpeg",
  "image_role": "exterior",
  "notes": null,
  "status": "uploaded",
  "is_deleted": 0,
  "created_at": "2026-07-03T12:05:00"
}
```

**Status Codes:**
- `201 Created` — success
- `400 Bad Request` — target property does not exist
- `422 Unprocessable Entity` — invalid file extension, file too large, or thumbnail/storage failure
- `500 Internal Server Error` — unexpected failure

**Rollback Behavior:** If the database write fails after the file was written to disk, the stored file (and any generated thumbnail) is deleted before the error is returned — no orphaned files remain.

**Frontend Module:** Property Images → **Enterprise Toolbar → Upload Images** (single file / file browser path).

---

## 7. Upload Multiple Images (Batch / Drag & Drop)

**Method:** `POST`
**Path:** `/api/v1/property-images/upload/batch`
**Content-Type:** `multipart/form-data`

### Request Payload (form fields)

| Field | Type | Required | Description |
|---|---|---|---|
| `property_id` | int | Yes | Target property |
| `files` | file[] | Yes | Multiple image files |
| `project_id` | string | No | Business project identifier |

### Example Request (curl)

```bash
curl -X POST "http://localhost:8000/api/v1/property-images/upload/batch" \
  -F "property_id=1" \
  -F "files=@front.jpg;type=image/jpeg" \
  -F "files=@side.jpg;type=image/jpeg" \
  -F "files=@rear.png;type=image/png"
```

### Response — `BatchUploadResponse` (HTTP 207 Multi-Status)

```json
{
  "property_id": 1,
  "total": 3,
  "succeeded": 2,
  "failed": 1,
  "results": [
    { "filename": "front.jpg", "success": true, "property_image": { "id": 45, "...": "..." }, "error": null },
    { "filename": "side.jpg", "success": true, "property_image": { "id": 46, "...": "..." }, "error": null },
    { "filename": "rear.png", "success": false, "property_image": null, "error": "File extension '.exe' is not permitted. Allowed: ['jpeg', 'jpg', 'png', 'webp']" }
  ]
}
```

**Status Codes:**
- `207 Multi-Status` — request processed; individual files may have succeeded or failed (see `results[]`)
- `400 Bad Request` — target property does not exist (fails the entire batch before any file is processed)
- `500 Internal Server Error` — unexpected failure

**Partial Success:** Each file is validated, stored, and persisted independently. One file's failure does not roll back or block the others.

**Frontend Module:** Property Images → **Enterprise Toolbar → Upload Images** (drag & drop / multi-select path), with a progress/results indicator per `08_PROPERTY_IMAGES.md` ("Upload Images" → Support: Drag & Drop, File Browser, Multiple File Upload, Progress Bar).

---

## 8. Import Image from URL

**Method:** `POST`
**Path:** `/api/v1/property-images/import-url`
**Content-Type:** `application/json`

### Request Payload — `ImageUrlImportRequest`

```json
{
  "property_id": 1,
  "image_url": "https://example.com/listing-photos/exterior.jpg",
  "project_id": "PRJ-001",
  "image_role": "exterior",
  "notes": "Imported from listing site"
}
```

### Response — `PropertyImageResponse` (HTTP 201)

```json
{
  "id": 47,
  "property_id": 1,
  "image_type": "uploaded",
  "image_url": "https://example.com/listing-photos/exterior.jpg",
  "provider": "url_import",
  "cached_path": "properties/1/original/7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f.jpg",
  "project_id": "PRJ-001",
  "original_file_name": "exterior.jpg",
  "file_size": 391204,
  "file_type": "image/jpeg",
  "image_role": "exterior",
  "notes": "Imported from listing site",
  "status": "uploaded",
  "is_deleted": 0,
  "created_at": "2026-07-03T12:10:00"
}
```

**Status Codes:**
- `201 Created` — success
- `400 Bad Request` — target property does not exist
- `422 Unprocessable Entity` — unsupported URL scheme, download failure, remote size limit exceeded, or invalid file type/size after download
- `500 Internal Server Error` — unexpected failure

**Rollback Behavior:** If provenance tagging (`provider`, `image_url`) fails after the file was already stored and persisted, the row and its stored file(s) are removed before the error is returned.

**Frontend Module:** Property Images → **Enterprise Toolbar → Import**, and the **Empty State** secondary action "Import Images" (per `08_PROPERTY_IMAGES.md`).

**Note:** `PropertyImageImportService` also supports local filesystem import (`import_from_local_path` / `import_from_local_paths`) for administrative batch imports. No HTTP endpoint is exposed for this in Phase 3A since it was not part of the requested router scope; it remains available for a future internal/admin tool.

---

## Schema Reference

All response bodies conform to `PropertyImageRead` / `PropertyImageResponse` (see `app/schemas/property_image.py`), which exposes every column on `cre_property_images` (see `app/models/property_image.py`). No new database columns were introduced in Phase 3A — `cached_path` continues to be the single source of truth for the on-disk relative path.

**Thumbnail paths are not stored as a column.** They are deterministically derivable from `cached_path` by replacing the `original/` path segment with `thumbnail/` and inserting `_thumb` before the file extension (see `PropertyImageUploadService.derive_thumbnail_relative_path()`). No API endpoint currently serves this derived value directly; it is available for the frontend/service layer to compute or for a future dedicated endpoint.

---

*End of Document — PROPERTY_IMAGES_API.md*
