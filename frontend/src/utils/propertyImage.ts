import { PropertyImage } from '../types/index';

/**
 * utils/propertyImage.ts
 *
 * AI HOME Image Display Standard - single shared helper for choosing
 * which image represents a Property, anywhere in the application.
 *
 * Priority, exactly as locked:
 *   1. is_primary = 1
 *   2. First uploaded image (earliest created_at)
 *   3. null - the caller renders its own placeholder/empty state; this
 *      helper never fabricates a placeholder image URL itself, so each
 *      page keeps whatever empty-state treatment already fits it (e.g.
 *      Home Studio's "Upload Photos to Begin" empty state, Dashboard's
 *      icon placeholder) rather than being forced into one shared visual.
 *
 * Excludes soft-deleted images (is_deleted = 1) - a deleted image should
 * never be presented as a Property's representative image. Callers that
 * already filter is_deleted before calling this (e.g. via
 * include_deleted: false on the list request) get identical behavior;
 * this filter is a defensive backstop, not a requirement to double-fetch.
 */
export function resolvePrimaryPropertyImage(images: PropertyImage[] | null | undefined): PropertyImage | null {
  if (!images || images.length === 0) return null;

  const active = images.filter((img) => img.is_deleted !== 1);
  if (active.length === 0) return null;

  const primary = active.find((img) => img.is_primary === 1);
  if (primary) return primary;

  // "First uploaded" = earliest created_at, not merely array order (the
  // caller's fetch/sort order is not guaranteed to be creation order).
  const sorted = [...active].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
  return sorted[0] ?? null;
}
