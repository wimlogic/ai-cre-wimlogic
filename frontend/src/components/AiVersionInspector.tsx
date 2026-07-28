import { Sparkles, AlertTriangle, CheckCircle2, Layers } from 'lucide-react';
import EnterpriseCard from './EnterpriseCard';
import EmptyState from './EmptyState';
import { DesignImageVersion } from '../types/index';
import { formatDate } from '../utils/formatters';
import styles from './ImageInspector.module.css';

export interface AiVersionInspectorProps {
  version: DesignImageVersion | null;
  onUseAsReference?: (versionId: number) => void;
  id?: string;
}

function formatFileSize(bytes: number | undefined): string {
  if (!bytes) return 'Unknown';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * components/AiVersionInspector.tsx
 *
 * AIHOME Design Studio V2. The "AI Generated" tab's counterpart to
 * ImageInspector - a REAL bug fix, not new scope: Home Studio's right
 * panel previously always rendered ImageInspector bound to whichever
 * original photo happened to be last previewed, regardless of which tab
 * was active, showing an editable Image Context (Role/Notes/Priority/
 * Tags) section that has no meaning for a generated image and edits an
 * entirely unrelated Property Image behind the scenes.
 *
 * Read-only by design: a DesignImageVersion has no image_role/notes/
 * priority/tags columns to save - those are Property Image business
 * context concepts, not Design Asset ones. "Use as Reference" is the
 * actual, correct action for "I want to do something more with this
 * image" - it opens the Design Job Workspace with this version already
 * selected, which is the only real mechanism for adding an image to a
 * Design Job anywhere in this app.
 *
 * Prompt/Rating/Favorite/Approved/Parent/Children/Tags (the fuller
 * "Image Details" vision) are intentionally NOT shown here - none of
 * those exist as real, populated fields on DesignImageVersion today;
 * showing them would mean fabricating data. Only real fields are
 * displayed; the rest remains future scope, per the same discipline
 * already applied to Design History and Latest Design Job elsewhere in
 * ImageInspector.tsx.
 */
export default function AiVersionInspector({ version, onUseAsReference, id }: AiVersionInspectorProps) {
  if (!version) {
    return (
      <div className={styles.wrapper} id={id || 'ai-version-inspector'}>
        <EmptyState
          icon={Sparkles}
          title="No AI Image Selected"
          description="Select a generated design from the filmstrip to see its details here."
        />
      </div>
    );
  }

  const isUnapproved = version.quality_approved === false;

  return (
    <div className={styles.wrapper} id={id || 'ai-version-inspector'}>
      <EnterpriseCard title="Image Information" className={styles.sectionCard}>
        <div className={styles.row}>
          <span className={styles.label}>Version</span>
          <span className={styles.value}>V{version.version_number}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.label}>Status</span>
          <span className={styles.value}>{version.status}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.label}>Generated</span>
          <span className={styles.value}>{formatDate(version.generated_at)}</span>
        </div>
        {version.source_provider && (
          <div className={styles.row}>
            <span className={styles.label}>Provider</span>
            <span className={styles.value}>{version.source_provider}</span>
          </div>
        )}
        {version.source_model && (
          <div className={styles.row}>
            <span className={styles.label}>Model</span>
            <span className={styles.value}>{version.source_model}</span>
          </div>
        )}
        {version.width && version.height && (
          <div className={styles.row}>
            <span className={styles.label}>Dimensions</span>
            <span className={styles.value}>{version.width} × {version.height}</span>
          </div>
        )}
        <div className={styles.row}>
          <span className={styles.label}>File Size</span>
          <span className={styles.value}>{formatFileSize(version.file_size)}</span>
        </div>
      </EnterpriseCard>

      <EnterpriseCard title="Quality Review" className={styles.sectionCard}>
        <div className={styles.readinessRow}>
          {isUnapproved ? (
            <AlertTriangle className="w-4 h-4" style={{ color: 'var(--color-warning-600, #d97706)' }} />
          ) : (
            <CheckCircle2 className="w-4 h-4" style={{ color: 'var(--color-success-600)' }} />
          )}
          <span>{isUnapproved ? 'Not approved by DEV-TOOLS quality review' : 'Approved'}</span>
        </div>
      </EnterpriseCard>

      <button
        type="button"
        className="enterprise-btn enterprise-btn-primary"
        onClick={() => onUseAsReference?.(version.id)}
        id="ai-version-inspector-use-as-reference-btn"
        style={{ width: '100%', justifyContent: 'center' }}
      >
        <Layers className="w-3.5 h-3.5" />
        Use as Reference
      </button>
    </div>
  );
}
