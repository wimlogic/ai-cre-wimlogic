import { apiClient } from './apiClient';
import { AppConfig } from '../config/app';
import { PropertyImage, ListResponse } from '../types/index';

/**
 * ASSUMPTION — UNVERIFIED BACKEND CONTRACT
 * ─────────────────────────────────────────
 * The frontend project provided for this modernization pass contains no
 * confirmed upload route. Per project instructions, backend code is out of
 * scope here and the upload/image-management APIs are assumed to already
 * exist and be production-ready.
 *
 * Expected contract (to be verified against the live backend before this
 * ships):
 *
 *   POST /property-images/upload
 *   Content-Type: multipart/form-data
 *   Fields:
 *     file          (binary, required)      - the image file
 *     property_id   (string/number, required)
 *     project_id    (string, required)
 *     image_type    (string, required)      - one of the existing
 *                                              cre_property_images.image_type
 *                                              enum values
 *     image_role    (string, optional)
 *     notes         (string, optional)
 *     status        (string, optional)
 *
 *   Response: 201 Created -> a single PropertyImage record (same shape
 *   returned by GET/POST /property-images/), with `image_url` and/or
 *   `cached_path` populated by the server after it stores the file via
 *   FilesystemStorageProvider.
 *
 * If this endpoint does not exist yet, `upload()` below is the single,
 * isolated call site to update - nothing else in the frontend depends on
 * upload internals.
 */
export interface PropertyImageUploadParams {
  file: File;
  property_id: number;
  project_id: string;
  image_type: string;
  image_role?: string;
  notes?: string;
  status?: string;
}

/**
 * Single source of truth for the assumed upload route. If the verified
 * backend contract turns out to use a different path, this is the only
 * line that needs to change - both `upload()` and `uploadWithProgress()`
 * read from it.
 */
const PROPERTY_IMAGE_UPLOAD_ENDPOINT = '/property-images/upload';

export const propertyImageService = {
  async list(params?: {
    skip?: number;
    limit?: number;
    property_id?: number;
    project_id?: string;
    image_type?: string;
    include_deleted?: boolean;
    search?: string;
  }): Promise<ListResponse<PropertyImage>> {
    const query = new URLSearchParams();
    if (params?.skip !== undefined) query.append('skip', String(params.skip));
    if (params?.limit !== undefined) query.append('limit', String(params.limit));
    if (params?.property_id !== undefined) query.append('property_id', String(params.property_id));
    if (params?.project_id) query.append('project_id', params.project_id);
    if (params?.image_type) query.append('image_type', params.image_type);
    if (params?.include_deleted !== undefined) query.append('include_deleted', String(params.include_deleted));
    if (params?.search) query.append('search', params.search);

    const queryString = query.toString();
    const endpoint = queryString ? `/property-images/?${queryString}` : '/property-images/';
    return apiClient.get<ListResponse<PropertyImage>>(endpoint);
  },

  async get(id: number): Promise<PropertyImage> {
    return apiClient.get<PropertyImage>(`/property-images/${id}`);
  },

  async create(data: Partial<PropertyImage>): Promise<PropertyImage> {
    return apiClient.post<PropertyImage>('/property-images/', data);
  },

  async update(id: number, data: Partial<PropertyImage>): Promise<PropertyImage> {
    return apiClient.put<PropertyImage>(`/property-images/${id}`, data);
  },

  async delete(id: number, soft = true): Promise<{ success: boolean }> {
    return apiClient.delete<{ success: boolean }>(`/property-images/${id}?soft=${soft}`);
  },

  /**
   * Upload a real image file. See the ASSUMPTION notice above this object -
   * this hits an endpoint that has not been confirmed against a live backend.
   */
  async upload(params: PropertyImageUploadParams): Promise<PropertyImage> {
    const formData = new FormData();
    formData.append('file', params.file);
    formData.append('property_id', String(params.property_id));
    formData.append('project_id', params.project_id);
    formData.append('image_type', params.image_type);
    if (params.image_role) formData.append('image_role', params.image_role);
    if (params.notes) formData.append('notes', params.notes);
    if (params.status) formData.append('status', params.status);

    return apiClient.upload<PropertyImage>(PROPERTY_IMAGE_UPLOAD_ENDPOINT, formData);
  },

  /**
   * Same as `upload()`, but reports progress via XHR (fetch cannot expose
   * upload progress events). Drives the progress bar in the DAM upload UI.
   * Returns both the result promise and an `abort()` handle so the caller
   * can cancel an in-flight upload.
   */
  uploadWithProgress(
    params: PropertyImageUploadParams,
    onProgress?: (percent: number) => void
  ): { promise: Promise<PropertyImage>; abort: () => void } {
    const formData = new FormData();
    formData.append('file', params.file);
    formData.append('property_id', String(params.property_id));
    formData.append('project_id', params.project_id);
    formData.append('image_type', params.image_type);
    if (params.image_role) formData.append('image_role', params.image_role);
    if (params.notes) formData.append('notes', params.notes);
    if (params.status) formData.append('status', params.status);

    const xhr = new XMLHttpRequest();
    const baseUrl = AppConfig.apiBaseUrl || 'http://127.0.0.1:8000/api/v1';

    const promise = new Promise<PropertyImage>((resolve, reject) => {
      xhr.open('POST', `${baseUrl}${PROPERTY_IMAGE_UPLOAD_ENDPOINT}`);

      xhr.upload.onprogress = (evt) => {
        if (evt.lengthComputable && onProgress) {
          onProgress(Math.round((evt.loaded / evt.total) * 100));
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch {
            reject(new Error('Failed to parse upload response'));
          }
        } else {
          let detail = xhr.responseText;
          try {
            detail = JSON.parse(xhr.responseText).detail || detail;
          } catch {
            /* keep raw text */
          }
          reject(new Error(detail || `Upload failed with status ${xhr.status}`));
        }
      };

      xhr.onerror = () => reject(new Error('Network error during upload'));
      xhr.onabort = () => reject(new Error('Upload cancelled'));

      xhr.send(formData);
    });

    return { promise, abort: () => xhr.abort() };
  },
};
