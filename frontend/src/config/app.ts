const apiBaseUrl: string = import.meta.env.VITE_API_BASE_URL;

/**
 * Backend origin (e.g. http://127.0.0.1:8000), derived from the existing API
 * base URL by stripping its /api or /api/v1-style suffix. Shared by anything
 * that needs to reach the backend outside the /api/v1 prefix - static
 * uploads and the root-level /health check - so the stripping logic exists
 * in exactly one place.
 */
const apiOrigin: string = apiBaseUrl.replace(/\/api(\/v\d+)?\/?$/, '');

/**
 * Origin that serves statically-mounted uploaded files (e.g.
 * http://127.0.0.1:8000/uploads). Only used to resolve `cached_path` for
 * uploaded images that have no external `image_url`.
 */
const uploadBaseUrl: string = `${apiOrigin}/uploads`;

export const AppConfig = {
  apiBaseUrl,
  apiOrigin,
  uploadBaseUrl,
  appName: import.meta.env.VITE_APP_NAME,
  version: import.meta.env.VITE_APP_VERSION,
};
