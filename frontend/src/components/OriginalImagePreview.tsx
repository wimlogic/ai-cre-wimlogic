import { useRef } from 'react';
import { Home, Star, ChevronLeft, ChevronRight, Maximize2 } from 'lucide-react';
import EmptyState from './EmptyState';
import { PropertyImage } from '../types/index';
import { resolveImageSrc, resolveImageFileName } from '../utils/imageUrl';
import styles from './OriginalImagePreview.module.css';

export interface OriginalImagePreviewProps {
  hasSelectedProperty: boolean;
  hasImages: boolean;
  previewImage: PropertyImage | null;
  onPrev?: () => void;
  onNext?: () => void;
  id?: string;
}

/**
 * components/OriginalImagePreview.tsx
 *
 * Home Studio Frontend Checkpoint 2. Owns only the ORIGINAL-image side of
 * the future Before/After canvas - the "After" (generated design) side is
 * explicitly deferred to a later checkpoint, per the Honest System States
 * principle (AI HOME UX Manifest 4.6): no fake generated image is ever
 * shown here.
 *
 * Image metadata/knowledge details have moved to the right-side
 * Contextual Inspector (components/ImageInspector.tsx) - this component
 * now owns only the visual preview itself plus prev/next navigation and
 * a real (not decorative) fullscreen toggle via the browser's Fullscreen
 * API. Zoom/pan interaction is intentionally deferred as a future
 * enhancement rather than built partially here.
 */
export default function OriginalImagePreview({
  hasSelectedProperty,
  hasImages,
  previewImage,
  onPrev,
  onNext,
  id,
}: OriginalImagePreviewProps) {
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  const handleFullscreen = () => {
    if (wrapperRef.current) {
      wrapperRef.current.requestFullscreen?.();
    }
  };

  if (!hasSelectedProperty) {
    return (
      <EmptyState
        icon={Home}
        title="Select a Property"
        description="Choose a Property above to begin working with its photos."
        id={id ? `${id}-no-property` : 'original-image-preview-no-property'}
      />
    );
  }

  if (!hasImages) {
    return (
      <EmptyState
        icon={Home}
        title="Upload Photos to Begin"
        description="This Property has no photos yet. Upload photos below to get started."
        id={id ? `${id}-no-images` : 'original-image-preview-no-images'}
      />
    );
  }

  if (!previewImage) {
    return (
      <EmptyState
        icon={Home}
        title="Select a Photo"
        description="Choose a photo from the filmstrip below to preview it here."
        id={id ? `${id}-no-preview` : 'original-image-preview-no-preview'}
      />
    );
  }

  const src = resolveImageSrc(previewImage);

  return (
    <div className={styles.wrapper} id={id || 'original-image-preview'} ref={wrapperRef}>
      <div className={styles.imageArea}>
        {src ? (
          <img src={src} alt={resolveImageFileName(previewImage)} className={styles.image} />
        ) : (
          <div className={styles.image} />
        )}
        {previewImage.is_primary === 1 && (
          <span className={styles.primaryBadge}>
            <Star className="w-3 h-3" />
            Primary Photo
          </span>
        )}

        {onPrev && (
          <button type="button" className={`${styles.navBtn} ${styles.navBtnLeft}`} onClick={onPrev} aria-label="Previous photo">
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}
        {onNext && (
          <button type="button" className={`${styles.navBtn} ${styles.navBtnRight}`} onClick={onNext} aria-label="Next photo">
            <ChevronRight className="w-4 h-4" />
          </button>
        )}

        <button type="button" className={styles.fullscreenBtn} onClick={handleFullscreen} aria-label="Full screen">
          <Maximize2 className="w-3.5 h-3.5" />
        </button>
      </div>
      <div className={styles.metaRow}>
        <span className={styles.fileName}>{resolveImageFileName(previewImage)}</span>
        {previewImage.image_role && <span className={styles.roleChip}>{previewImage.image_role}</span>}
      </div>
    </div>
  );
}
