import { useMemo } from 'react';
import { Image as ImageIcon } from 'lucide-react';
import EmptyState from './EmptyState';
import { PropertyImage, DesignImageVersion } from '../types/index';
import { resolveImageSrc, resolveImageFileName, resolveDesignImageSrc, resolveDesignImageFileName } from '../utils/imageUrl';
import styles from './WorkspacePreview.module.css';

export type WorkspaceAsset =
  | { kind: 'original'; id: number; image: PropertyImage }
  | { kind: 'version'; id: number; version: DesignImageVersion };

export interface WorkspacePreviewProps {
  selectedAssets: WorkspaceAsset[];
  /** The single asset to show large, e.g. whichever thumbnail the user
   * just clicked in the strip below, or whatever's under hover. Falls
   * back to the first selected asset when not provided. */
  activeAsset?: WorkspaceAsset | null;
  onSetActive?: (asset: WorkspaceAsset) => void;
  id?: string;
}

function assetSrc(asset: WorkspaceAsset, useThumbnail = false): string {
  return asset.kind === 'original' ? resolveImageSrc(asset.image) : resolveDesignImageSrc(asset.version, useThumbnail);
}

function assetFileName(asset: WorkspaceAsset): string {
  return asset.kind === 'original' ? resolveImageFileName(asset.image) : resolveDesignImageFileName(asset.version);
}

/**
 * components/WorkspacePreview.tsx
 *
 * AIHOME Design Studio V2 - Image Workspace Evolution. Center panel of
 * the Design Job Workspace. One selected asset -> a single large
 * preview. Multiple selected -> the same large preview plus a thumbnail
 * strip beneath it for navigating between them, mirroring the same
 * "preview vs. selection are separate concepts" pattern already
 * established in Home Studio's own filmstrips.
 *
 * Before/After comparison (a genuinely different, more involved UI -
 * side-by-side and slider modes) is intentionally NOT built in this
 * pass; this component's asset-union shape is what a future comparison
 * view would consume, so adding it later doesn't require restructuring
 * this component, only extending it.
 */
export default function WorkspacePreview({ selectedAssets, activeAsset, onSetActive, id }: WorkspacePreviewProps) {
  const active = useMemo(
    () => activeAsset ?? selectedAssets[0] ?? null,
    [activeAsset, selectedAssets]
  );

  if (selectedAssets.length === 0) {
    return (
      <EmptyState
        icon={ImageIcon}
        title="No Images Selected"
        description="Select one or more images from the library on the left to preview them here."
        id={id ? `${id}-empty` : 'workspace-preview-empty'}
      />
    );
  }

  return (
    <div className={styles.wrapper} id={id || 'workspace-preview'}>
      <div className={styles.imageArea}>
        {active ? (
          <img src={assetSrc(active)} alt={assetFileName(active)} className={styles.image} />
        ) : (
          <div className={styles.image} />
        )}
        <span className={styles.sourceBadge}>{active?.kind === 'original' ? 'Original' : 'AI Generated'}</span>
      </div>

      {selectedAssets.length > 1 && (
        <div className={styles.strip} role="listbox" aria-label="Selected images">
          {selectedAssets.map((asset) => {
            const isActive = active && active.kind === asset.kind && active.id === asset.id;
            return (
              <button
                key={`${asset.kind}-${asset.id}`}
                type="button"
                className={`${styles.stripThumbButton} ${isActive ? styles.stripThumbButtonActive : ''}`}
                onClick={() => onSetActive?.(asset)}
                role="option"
                aria-selected={!!isActive}
              >
                <img src={assetSrc(asset, true)} alt="" className={styles.stripThumb} />
                <span className={styles.stripBadge}>{asset.kind === 'original' ? 'Orig' : 'AI'}</span>
              </button>
            );
          })}
        </div>
      )}

      <p className={styles.fileName}>{active ? assetFileName(active) : ''}</p>
    </div>
  );
}
