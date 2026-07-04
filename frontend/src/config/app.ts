const apiBaseUrl: string = import.meta.env.VITE_API_BASE_URL;

/**
 * Origin that serves statically-mounted uploaded files (e.g.
 * http://127.0.0.1:8000/uploads), derived from the existing API base URL by
 * stripping its /api or /api/v1-style suffix. This avoids hardcoding a second
 * localhost default alongside VITE_API_BASE_URL - if the API base URL changes
 * per environment (dev / VPS / prod), the upload base URL follows it
 * automatically. Only used to resolve `cached_path` for uploaded images that
 * have no external `image_url`.
 */
const uploadBaseUrl: string = apiBaseUrl.replace(/\/api(\/v\d+)?\/?$/, '') + '/uploads';

export const AppConfig = {
  apiBaseUrl,
  uploadBaseUrl,
  appName: import.meta.env.VITE_APP_NAME,
  version: import.meta.env.VITE_APP_VERSION,
};
