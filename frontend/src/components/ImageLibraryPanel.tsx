import { useState } from 'react';
import { ChevronDown, ChevronRight, Image as ImageIcon, Sparkles, AlertTriangle } from 'lucide-react';
import { PropertyImage, DesignImageVersion } from '../types/index';
import { resolveImageSrc } from '../utils/imageUrl';
import { resolveDesignImageSrc } from '../utils/imageUrl';
import { formatDate } from '../utils/formatters';
import styles from './ImageLibraryPanel.module.css';

export interface ImageLibraryPanelProps {
  originalImages: PropertyImage[];
  aiVersions: DesignImageVersion[];
  selectedOriginalIds: Set<number>;
  selectedVersionIds: Set<number>;
  onToggleOriginal: (id: number) => void;
  onToggleVersion: (id: number) => void;
  /** Hover preview - lets the center panel show a live preview of
   * whatever's under the cursor without changing the actual selection. */
  onHoverOriginal?: (id: number | null) => void;
  onHoverVersion?: (id: number | null) => void;
  id?: string;
}

/**
 * components/ImageLibraryPanel.tsx
 *
 * AIHOME Design Studio V2 - Image Workspace Evolution. Left panel of the
 * Design Job Workspace: two expandable groups (Original Photos, AI
 * Generated Images), each a checkbox grid. The user may select any
 * combination - originals only, AI images only, or mixed - nothing is
 * automatically selected or excluded.
 *
 * Structured for future filtering (a filter bar could sit directly above
 * either grid without restructuring this component) and future card
 * actions (favorite/approve/archive) without redesign - this pass only
 * implements selection, per the approved scope.
 */
export default function ImageLibraryPanel({
  originalImages,
  aiVersions,
  selectedOriginalIds,
  selectedVersionIds,
  onToggleOriginal,
  onToggleVersion,
  onHoverOriginal,
  onHoverVersion,
  id,
}: ImageLibraryPanelProps) {
  const [originalsExpanded, setOriginalsExpanded] = useState(true);
  const [aiExpanded, setAiExpanded] = useState(true);

  return (
    <div className={styles.panel} id={id || 'image-library-panel'}>
      <div className={styles.group}>
        <button
          type="button"
          className={styles.groupHeader}
          onClick={() => setOriginalsExpanded((v) => !v)}
          aria-expanded={originalsExpanded}
        >
          {originalsExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          <ImageIcon className="w-3.5 h-3.5" />
          <span className={styles.groupTitle}>Original Photos</span>
          <span className={styles.groupCount}>{originalImages.length}</span>
        </button>
        {originalsExpanded && (
          <div className={styles.grid}>
            {originalImages.length === 0 ? (
              <p className={styles.emptyText}>No original photos yet.</p>
            ) : (
              originalImages.map((img) => {
                const isSelected = selectedOriginalIds.has(img.id);
                const src = resolveImageSrc(img);
                return (
                  <label
                    key={img.id}
                    className={`${styles.card} ${isSelected ? styles.cardSelected : ''}`}
                    onMouseEnter={() => onHoverOriginal?.(img.id)}
                    onMouseLeave={() => onHoverOriginal?.(null)}
                  >
                    <input
                      type="checkbox"
                      className={styles.checkbox}
                      checked={isSelected}
                      onChange={() => onToggleOriginal(img.id)}
                      aria-label={`Select original photo${img.image_role ? `, ${img.image_role}` : ''}`}
                    />
                    {src ? <img src={src} alt="" className={styles.thumb} /> : <div className={styles.thumb} />}
                    {img.image_role && <span className={styles.cardBadge}>{img.image_role}</span>}
                  </label>
                );
              })
            )}
          </div>
        )}
      </div>

      <div className={styles.group}>
        <button
          type="button"
          className={styles.groupHeader}
          onClick={() => setAiExpanded((v) => !v)}
          aria-expanded={aiExpanded}
        >
          {aiExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          <Sparkles className="w-3.5 h-3.5" />
          <span className={styles.groupTitle}>AI Generated Images</span>
          <span className={styles.groupCount}>{aiVersions.length}</span>
        </button>
        {aiExpanded && (
          <div className={styles.grid}>
            {aiVersions.length === 0 ? (
              <p className={styles.emptyText}>No AI generated images yet.</p>
            ) : (
              aiVersions.map((version) => {
                const isSelected = selectedVersionIds.has(version.id);
                const src = resolveDesignImageSrc(version, true);
                return (
                  <label
                    key={version.id}
                    className={`${styles.card} ${isSelected ? styles.cardSelected : ''}`}
                    onMouseEnter={() => onHoverVersion?.(version.id)}
                    onMouseLeave={() => onHoverVersion?.(null)}
                  >
                    <input
                      type="checkbox"
                      className={styles.checkbox}
                      checked={isSelected}
                      onChange={() => onToggleVersion(version.id)}
                      aria-label={`Select AI generated version ${version.version_number}`}
                    />
                    {src ? <img src={src} alt="" className={styles.thumb} /> : <div className={styles.thumb} />}
                    {version.quality_approved === false && (
                      <span className={styles.warningBadge} title="Quality review: not approved">
                        <AlertTriangle className="w-3 h-3" />
                      </span>
                    )}
                    <div className={styles.cardMeta}>
                      <span className={styles.versionBadge}>V{version.version_number}</span>
                      <span className={styles.dateBadge}>{formatDate(version.generated_at)}</span>
                    </div>
                  </label>
                );
              })
            )}
          </div>
        )}
      </div>
    </div>
  );
}
