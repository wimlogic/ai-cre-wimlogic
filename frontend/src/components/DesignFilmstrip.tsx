import { Star, Check, Sparkles } from 'lucide-react';
import EmptyState from './EmptyState';
import { PropertyImage } from '../types/index';
import { resolveImageSrc } from '../utils/imageUrl';
import { getContextCompletion } from '../utils/imageContext';
import styles from './DesignFilmstrip.module.css';

export interface DesignFilmstripProps {
  images: PropertyImage[];
  previewImageId: number | null;
  selectedImageIds: Set<number>;
  onPreview: (id: number) => void;
  onToggleSelect: (id: number) => void;
  onSetPrimary: (id: number) => void;
  isSettingPrimary?: boolean;
  id?: string;
}

/**
 * components/DesignFilmstrip.tsx
 *
 * Home Studio Frontend Checkpoint 2. Horizontal scrolling filmstrip -
 * true native scroll, never page-by-page pagination. Preview and
 * selection are deliberately separate concepts (AI HOME UX Manifest
 * 9.3): a single click sets the preview image; the selection control
 * toggles inclusion in the multi-select set independently.
 */
export default function DesignFilmstrip({
  images,
  previewImageId,
  selectedImageIds,
  onPreview,
  onToggleSelect,
  onSetPrimary,
  isSettingPrimary = false,
  id,
}: DesignFilmstripProps) {
  if (images.length === 0) {
    return (
      <EmptyState
        icon={Sparkles}
        title="No Photos Yet"
        description="Upload photos above to build your Property's photo collection."
        id={id ? `${id}-empty` : 'design-filmstrip-empty'}
      />
    );
  }

  return (
    <div className={styles.track} id={id || 'design-filmstrip'} role="listbox" aria-label="Property photos">
      {images.map((img) => {
        const isPreview = img.id === previewImageId;
        const isSelected = selectedImageIds.has(img.id);
        const src = resolveImageSrc(img);
        const completion = getContextCompletion(img);
        const completionTitle =
          completion === 'complete' ? 'Context Complete' : completion === 'partial' ? 'Partial Context' : 'No Context';

        return (
          <div
            key={img.id}
            className={`${styles.thumbWrap} ${isPreview ? styles.thumbWrapPreview : ''}`}
          >
            <button
              type="button"
              className={styles.thumbButton}
              onClick={() => onPreview(img.id)}
              role="option"
              aria-selected={isPreview}
              aria-label={`Preview photo${img.image_role ? `, role ${img.image_role}` : ''}`}
              id={`design-filmstrip-thumb-${img.id}`}
            >
              {src ? <img src={src} alt="" className={styles.thumbImage} /> : <div className={styles.thumbImage} />}

              {img.is_primary === 1 && (
                <span className={styles.primaryMarker} title="Primary Photo">
                  <Star className="w-3 h-3" />
                </span>
              )}

              <span
                className={`${styles.contextDot} ${styles[`contextDot_${completion}`]}`}
                title={completionTitle}
                aria-label={completionTitle}
              />

              <div className={styles.thumbFooter}>
                {img.image_role && <span className={styles.roleLabel}>{img.image_role}</span>}
                {img.priority != null && <span className={styles.priorityLabel}>P{img.priority}</span>}
              </div>
            </button>

            <label className={styles.selectRow}>
              <input
                type="checkbox"
                className="enterprise-form-checkbox"
                checked={isSelected}
                onChange={() => onToggleSelect(img.id)}
                aria-label="Select photo for design"
              />
              <span>{isSelected ? <Check className="w-3 h-3" /> : 'Select'}</span>
            </label>

            {img.is_primary !== 1 && (
              <button
                type="button"
                className={styles.setPrimaryBtn}
                onClick={() => onSetPrimary(img.id)}
                disabled={isSettingPrimary}
              >
                Set Primary Photo
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
