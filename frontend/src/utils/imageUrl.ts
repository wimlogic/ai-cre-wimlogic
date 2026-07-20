import { AppConfig } from '../config/app';
import { PropertyImage } from '../types/index';

/**
 * utils/imageUrl.ts
 *
 * Shared Property Image URL resolution (Home Studio Frontend Checkpoint
 * 2). Extracted verbatim from PropertyImages.tsx's own inline resolveSrc()
 * - same two rules, same fallback - so both PropertyImages.tsx and Home
 * Studio's new components share one source of truth instead of two
 * copies with a risk of drifting apart.
 */
export function resolveImageSrc(img: PropertyImage): string {
  // Imported images (Street View, satellite, external URLs) already have a
  // full absolute image_url - render directly.
  if (img.image_url) return img.image_url;

  // Uploaded images only have cached_path, a relative POSIX-style path with
  // no scheme or host - resolve it against the configured upload base URL.
  if (img.cached_path) {
    const base = AppConfig.uploadBaseUrl.replace(/\/$/, '');
    const path = img.cached_path.replace(/^\//, '');
    return `${base}/${path}`;
  }

  return '';
}

/**
 * Best-effort display file name, also extracted from PropertyImages.tsx's
 * existing displayFileName() so both surfaces label images consistently.
 */
export function resolveImageFileName(img: PropertyImage): string {
  if (img.original_file_name) return img.original_file_name;
  if (img.image_url) {
    try {
      const parts = img.image_url.split('/');
      return parts[parts.length - 1] || `image-${img.id}`;
    } catch {
      return `image-${img.id}`;
    }
  }
  return `image-${img.id}`;
}
