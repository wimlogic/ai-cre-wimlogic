import { PropertyImage } from '../types/index';

/**
 * utils/imageContext.ts
 *
 * Shared Image Role vocabulary and Image Context completion rule, reused
 * by both PropertyImages.tsx (Image Role dropdown, added in the prior
 * Image Role/Status correction pass) and Home Studio's new Image
 * Context panel - a single source of truth rather than two competing
 * lists. AUDIT NOTE (unchanged from the prior correction): this is a
 * FRONTEND-ONLY constraint - cre_property_images.image_role has no
 * database CHECK constraint, Pydantic Literal, or service validation.
 * "Do not introduce a new backend enumeration" is honored by reusing
 * this exact list rather than the differently-worded example list given
 * in the Image Context Management task, which is illustrative rather
 * than a second authoritative vocabulary.
 */
export const IMAGE_ROLE_OPTIONS: { value: string; label: string }[] = [
  { value: 'primary', label: 'Primary' },
  { value: 'exterior', label: 'Exterior' },
  { value: 'interior', label: 'Interior' },
  { value: 'kitchen', label: 'Kitchen' },
  { value: 'bathroom', label: 'Bathroom' },
  { value: 'bedroom', label: 'Bedroom' },
  { value: 'living_room', label: 'Living Room' },
  { value: 'dining_room', label: 'Dining Room' },
  { value: 'garage', label: 'Garage' },
  { value: 'yard', label: 'Yard' },
  { value: 'floor_plan', label: 'Floor Plan' },
  { value: 'site_plan', label: 'Site Plan' },
  { value: 'detail', label: 'Detail' },
  { value: 'reference', label: 'Reference' },
  { value: 'other', label: 'Other' },
];

/**
 * Priority is a plain nullable int column with no backend enum - the
 * High/Medium/Low dropdown requested for Home Studio's Image Context
 * panel is a FRONTEND CONVENTION mapped onto that same column, not a new
 * backend field or schema change. Values chosen to match the numeric
 * convention already used in real seeded/tested data (priority=10 as
 * the highest tier).
 */
export const PRIORITY_OPTIONS: { value: number; label: string }[] = [
  { value: 10, label: 'High' },
  { value: 5, label: 'Medium' },
  { value: 1, label: 'Low' },
];

export function priorityLabel(value: number | null | undefined): string {
  if (value == null) return 'Not Set';
  const match = PRIORITY_OPTIONS.find((p) => p.value === value);
  if (match) return match.label;
  // A priority value outside the three known tiers (e.g. legacy data) -
  // show the raw number rather than silently mislabeling it.
  return String(value);
}

export type ContextCompletion = 'complete' | 'partial' | 'none';

/**
 * Image Context completion rule (Home Studio Image Context Management,
 * Phase 1). Frontend-only heuristic - documented explicitly, not a
 * fabricated backend readiness field. Drives both the thumbnail status
 * dot and the AI Readiness panel's "Context Completed" line.
 *
 * complete: role AND priority AND (notes or at least one tag)
 * partial:  at least one of role / priority / notes / tags is set
 * none:     nothing set
 */
export function getContextCompletion(image: PropertyImage): ContextCompletion {
  const hasRole = Boolean(image.image_role);
  const hasPriority = image.priority != null;
  const hasNotes = Boolean(image.notes && image.notes.trim().length > 0);
  const hasTags = Boolean(image.tags && image.tags.length > 0);

  if (hasRole && hasPriority && (hasNotes || hasTags)) return 'complete';
  if (hasRole || hasPriority || hasNotes || hasTags) return 'partial';
  return 'none';
}
