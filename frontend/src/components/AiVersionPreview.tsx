import { useRef } from 'react';
import { Sparkles, ChevronLeft, ChevronRight, Maximize2, AlertTriangle } from 'lucide-react';
import EmptyState from './EmptyState';
import { DesignImageVersion } from '../types/index';
import { resolveDesignImageSrc, resolveDesignImageFileName } from '../utils/imageUrl';
import { formatDate } from '../utils/formatters';
import styles from './AiVersionPreview.module.css';

export interface AiVersionPreviewProps {
  hasSelectedProperty: boolean;
  hasVersions: boolean;
  previewVersion: DesignImageVersion | null;
  onPrev?: () => void;
  onNext?: () => void;
  id?: string;
}

/**
 * components/AiVersionPreview.tsx
 *
 * Home Studio's "AI Generated" counterpart to OriginalImagePreview.
 * Owns only the generated-image visual preview, prev/next navigation
 * through the Property's AI versions, and a real fullscreen toggle -
 * the same scope OriginalImagePreview owns for original photos.
 *
 * Unlike OriginalImagePreview, no "Image Role" chip (that's a Property
 * Image concept) - instead shows provider/model/version, and a quality
 * review warning when DEV-TOOLS reported approved: false. This mirrors
 * the same fields already surfaced on the Results page's "Generated
 * Design Images" card, so the same version reads consistently wherever
 * it's shown in AIHOME.
 */
export default function AiVersionPreview({
  hasSelectedProperty,
  hasVersions,
  previewVersion,
  onPrev,
  onNext,
  id,
}: AiVersionPreviewProps) {
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  const handleFullscreen = () => {
    if (wrapperRef.current) {
      wrapperRef.current.requestFullscreen?.();
    }
  };

  if (!hasSelectedProperty) {
    return (
      <EmptyState
        icon={Sparkles}
        title="Select a Property"
        description="Choose a Property above to view its AI generated designs."
        id={id ? `${id}-no-property` : 'ai-version-preview-no-property'}
      />
    );
  }

  if (!hasVersions) {
    return (
      <EmptyState
        icon={Sparkles}
        title="No AI Images Yet"
        description="Generated design versions will appear here once a Design Job produces results."
        id={id ? `${id}-no-versions` : 'ai-version-preview-no-versions'}
      />
    );
  }

  if (!previewVersion) {
    return (
      <EmptyState
        icon={Sparkles}
        title="Select an Image"
        description="Choose a generated design from the filmstrip below to preview it here."
        id={id ? `${id}-no-preview` : 'ai-version-preview-no-preview'}
      />
    );
  }

  const src = resolveDesignImageSrc(previewVersion);
  const isUnapproved = previewVersion.quality_approved === false;

  return (
    <div className={styles.wrapper} id={id || 'ai-version-preview'} ref={wrapperRef}>
      <div className={styles.imageArea}>
        {src ? (
          <img src={src} alt={resolveDesignImageFileName(previewVersion)} className={styles.image} />
        ) : (
          <div className={styles.image} />
        )}
        <span className={styles.versionBadge}>Version {previewVersion.version_number}</span>

        {onPrev && (
          <button type="button" className={`${styles.navBtn} ${styles.navBtnLeft}`} onClick={onPrev} aria-label="Previous version">
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}
        {onNext && (
          <button type="button" className={`${styles.navBtn} ${styles.navBtnRight}`} onClick={onNext} aria-label="Next version">
            <ChevronRight className="w-4 h-4" />
          </button>
        )}

        <button type="button" className={styles.fullscreenBtn} onClick={handleFullscreen} aria-label="Full screen">
          <Maximize2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {isUnapproved && (
        <p className={styles.qualityWarning}>
          <AlertTriangle className="w-3.5 h-3.5" />
          DEV-TOOLS quality review did not approve this image. Review before publishing.
        </p>
      )}

      <div className={styles.metaRow}>
        <span className={styles.fileName}>{resolveDesignImageFileName(previewVersion)}</span>
        <div className={styles.metaChips}>
          {previewVersion.source_provider && <span className={styles.chip}>{previewVersion.source_provider}</span>}
          {previewVersion.source_model && <span className={styles.chip}>{previewVersion.source_model}</span>}
          <span className={styles.chip}>{formatDate(previewVersion.generated_at)}</span>
        </div>
      </div>
    </div>
  );
}
