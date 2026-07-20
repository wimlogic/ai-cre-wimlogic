import { useEffect, useState } from 'react';
import { Info, Layers, CheckCircle2, Circle } from 'lucide-react';
import EnterpriseCard from './EnterpriseCard';
import EnterpriseSelect from './EnterpriseSelect';
import EmptyState from './EmptyState';
import FormField from './FormField';
import TagEditor from './TagEditor';
import useToast from '../hooks/useToast';
import { propertyImageService } from '../services/propertyImageService';
import { PropertyImage } from '../types/index';
import { resolveImageFileName } from '../utils/imageUrl';
import { formatDate } from '../utils/formatters';
import { IMAGE_ROLE_OPTIONS, PRIORITY_OPTIONS, getContextCompletion } from '../utils/imageContext';
import styles from './ImageInspector.module.css';

export interface ImageInspectorProps {
  image: PropertyImage | null;
  /** Called after a successful Save, so the parent (Home Studio) can refresh its own image list/state. */
  onSaved?: (updated: PropertyImage) => void;
  id?: string;
}

/**
 * components/ImageInspector.tsx
 *
 * Home Studio's right-side Contextual Inspector - Image Context
 * Management revision (Phase 1, frontend only).
 *
 * Four sections, per the approved task:
 *   1. Image Information (read-only)
 *   2. Image Context (editable - Image Role, Notes, Priority, Tags,
 *      Save Image Context)
 *   3. AI Readiness (business-friendly, frontend-only heuristic)
 *   4. Design History (empty-state placeholder for this phase)
 *
 * Image Context belongs to the Property Image, not the Design Job -
 * "Save Image Context" persists ONLY these four fields through the
 * EXISTING propertyImageService.update() endpoint. It never submits a
 * Design Job and never calls DEV-TOOLS. All four fields (image_role,
 * notes, priority, tags) are already real, updatable columns on
 * cre_property_images - confirmed via the same backend audit performed
 * for the Property Images Image Role/Status correction pass, so no
 * backend TODO is needed for the core save action itself (see the one
 * documented TODO below, for "Latest Design Job").
 *
 * Selecting "Primary" here uses the same primary-consistency handling
 * already built for Property Images (real setPrimary() endpoint, never
 * a plain text write) - reusing that logic rather than reintroducing
 * the exact stale-text bug that was already found and fixed elsewhere.
 */
export default function ImageInspector({ image, onSaved, id }: ImageInspectorProps) {
  const { success, error: toastError } = useToast();

  const [draftRole, setDraftRole] = useState('');
  const [draftNotes, setDraftNotes] = useState('');
  const [draftPriority, setDraftPriority] = useState<number | null>(null);
  const [draftTags, setDraftTags] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  // Reset the draft whenever the user switches to a different photo -
  // otherwise an in-progress edit on Photo A would leak into Photo B.
  useEffect(() => {
    setDraftRole(image?.image_role || '');
    setDraftNotes(image?.notes || '');
    setDraftPriority(image?.priority ?? null);
    setDraftTags(image?.tags || []);
  }, [image?.id]);

  if (!image) {
    return (
      <div className={styles.wrapper} id={id || 'image-inspector'}>
        <EmptyState
          icon={Info}
          title="No Photo Selected"
          description="Select a property image to inspect its AI Knowledge and prepare it for AI Design Studio workflows."
        />
      </div>
    );
  }

  const isDirty =
    draftRole !== (image.image_role || '') ||
    draftNotes !== (image.notes || '') ||
    draftPriority !== (image.priority ?? null) ||
    JSON.stringify(draftTags) !== JSON.stringify(image.tags || []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const wantsPrimary = draftRole === 'primary';
      const isCurrentlyPrimary = image.is_primary === 1;

      // Same primary-consistency handling as Property Images: selecting
      // "Primary" must use the real endpoint, never a plain text write.
      if (wantsPrimary && !isCurrentlyPrimary) {
        await propertyImageService.setPrimary(image.id);
      }

      const updated = await propertyImageService.update(image.id, {
        image_role: draftRole || undefined,
        notes: draftNotes,
        priority: draftPriority,
        tags: draftTags,
      });

      success('Image Context saved.');
      onSaved?.(updated);
    } catch (err: any) {
      console.error('[Home Studio] Failed to save Image Context:', err);
      toastError(err?.message || 'Failed to save Image Context.');
    } finally {
      setIsSaving(false);
    }
  };

  const completion = getContextCompletion(image);

  return (
    <div className={styles.wrapper} id={id || 'image-inspector'}>
      <EnterpriseCard title="Image Information" className={styles.sectionCard}>
        <div className={styles.row}>
          <span className={styles.label}>Filename</span>
          <span className={styles.value}>{resolveImageFileName(image)}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.label}>Upload Date</span>
          <span className={styles.value}>{formatDate(image.created_at)}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.label}>Format</span>
          <span className={styles.value}>{image.file_type || 'Unknown'}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.label}>Image Size</span>
          <span className={styles.value}>{formatFileSize(image.file_size)}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.label}>Resolution</span>
          {/* cre_property_images has no width/height column - honestly
              reported as unavailable rather than fabricated. */}
          <span className={styles.valueMissing}>Not available</span>
        </div>
      </EnterpriseCard>

      <EnterpriseCard title="Image Context" className={styles.sectionCard}>
        <FormField label="Image Role" id="context-image-role-field">
          <EnterpriseSelect
            id="context-image-role-select"
            value={draftRole}
            options={IMAGE_ROLE_OPTIONS}
            placeholder="Select a role"
            onChange={setDraftRole}
            disabled={isSaving}
          />
        </FormField>

        <FormField label="Image Notes" id="context-notes-field">
          <textarea
            className="enterprise-form-input"
            rows={3}
            value={draftNotes}
            onChange={(e) => setDraftNotes(e.target.value)}
            placeholder="Main front elevation. Replace siding. Keep front porch."
            disabled={isSaving}
          />
        </FormField>

        <FormField label="Priority" id="context-priority-field">
          <EnterpriseSelect
            id="context-priority-select"
            value={draftPriority != null ? String(draftPriority) : ''}
            options={PRIORITY_OPTIONS.map((p) => ({ value: String(p.value), label: p.label }))}
            placeholder="Select a priority"
            onChange={(v) => setDraftPriority(v ? Number(v) : null)}
            disabled={isSaving}
          />
        </FormField>

        <FormField label="Tags" id="context-tags-field">
          <TagEditor tags={draftTags} onChange={setDraftTags} disabled={isSaving} />
        </FormField>

        <button
          type="button"
          className={`enterprise-btn enterprise-btn-primary ${styles.saveButton}`}
          onClick={handleSave}
          disabled={isSaving || !isDirty}
          id="save-image-context-btn"
        >
          {isSaving ? 'Saving...' : 'Save Image Context'}
        </button>
      </EnterpriseCard>

      <EnterpriseCard title="AI Readiness" className={styles.sectionCard}>
        <div className={styles.readinessList}>
          <div className={styles.readinessRow}>
            <CheckCircle2 className="w-4 h-4" style={{ color: 'var(--color-success-600)' }} />
            <span>Image Uploaded</span>
          </div>
          <div className={styles.readinessRow}>
            {completion === 'complete' ? (
              <CheckCircle2 className="w-4 h-4" style={{ color: 'var(--color-success-600)' }} />
            ) : (
              <Circle className="w-4 h-4" style={{ color: 'var(--color-neutral-300)' }} />
            )}
            <span>Context Completed</span>
          </div>
          <div className={styles.readinessRow}>
            {completion === 'complete' ? (
              <CheckCircle2 className="w-4 h-4" style={{ color: 'var(--color-success-600)' }} />
            ) : (
              <Circle className="w-4 h-4" style={{ color: 'var(--color-neutral-300)' }} />
            )}
            <span>Eligible for Design Jobs</span>
          </div>
        </div>
        <div className={styles.row} style={{ marginTop: '0.75rem' }}>
          <span className={styles.label}>Latest Design Job</span>
          {/* TODO(backend): no query exists today to look up Design Jobs
              by property_image_id (only by property_id, which does not
              indicate whether THIS specific image was selected in that
              job). Honestly shown as None for this phase rather than
              approximated. */}
          <span className={styles.valueMissing}>None</span>
        </div>
      </EnterpriseCard>

      <EnterpriseCard title="Design History" className={styles.sectionCard}>
        <EmptyState icon={Layers} title="No Design Versions Yet" description="Generated design versions will appear here once a Design Job produces results." />
      </EnterpriseCard>
    </div>
  );
}

function formatFileSize(bytes: number | undefined): string {
  if (!bytes) return 'Unknown';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
