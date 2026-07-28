import { useState } from 'react';
import { Sparkles, AlertTriangle, MoreVertical, Layers, Download } from 'lucide-react';
import EmptyState from './EmptyState';
import { DesignImageVersion } from '../types/index';
import { resolveDesignImageSrc, resolveDesignImageFileName } from '../utils/imageUrl';
import styles from './AiVersionFilmstrip.module.css';

export interface AiVersionFilmstripProps {
  versions: DesignImageVersion[];
  previewVersionId: number | null;
  onPreview: (id: number) => void;
  /** AIHOME Design Studio V2 - "Use as Reference": opens the Design Job
   * Workspace with this version already selected, so the user never has
   * to manually find and reselect it for an iterative refinement. */
  onUseAsReference?: (versionId: number) => void;
  id?: string;
}

/**
 * components/AiVersionFilmstrip.tsx
 *
 * Home Studio's "AI Generated" counterpart to DesignFilmstrip (which
 * remains Original-Photo-only, unchanged). A separate component rather
 * than an extension of DesignFilmstrip because the concepts genuinely
 * differ: no "select for a Design Job", no "set primary" - a
 * DesignImageVersion instead carries its own version_number, provider/
 * model provenance, and an optional quality warning, none of which map
 * onto DesignFilmstrip's PropertyImage-shaped props.
 *
 * Clicking a thumbnail here IS the version switcher - each entry is one
 * Design Image Version for the Property, ordered as returned by the
 * backend (newest first, per crud_design_image_version.get_multi()).
 *
 * Each card's "..." menu: Use as Reference and Download are real,
 * functional actions. Rename and Delete are shown but disabled - no
 * backend endpoint exists for either yet, and this project's own
 * Honest System States convention (see OriginalImagePreview.tsx) means
 * a control that looks clickable but does nothing is worse than one
 * that's visibly reserved for later.
 */
export default function AiVersionFilmstrip({ versions, previewVersionId, onPreview, onUseAsReference, id }: AiVersionFilmstripProps) {
  const [openMenuId, setOpenMenuId] = useState<number | null>(null);

  if (versions.length === 0) {
    return (
      <EmptyState
        icon={Sparkles}
        title="No AI Images Yet"
        description="Generated design versions will appear here once a Design Job produces results."
        id={id ? `${id}-empty` : 'ai-version-filmstrip-empty'}
      />
    );
  }

  return (
    <div className={styles.track} id={id || 'ai-version-filmstrip'} role="listbox" aria-label="AI generated design versions">
      {versions.map((version) => {
        const isPreview = version.id === previewVersionId;
        const src = resolveDesignImageSrc(version, true);
        const isUnapproved = version.quality_approved === false;
        const isMenuOpen = openMenuId === version.id;

        return (
          <div key={version.id} className={`${styles.thumbWrap} ${isPreview ? styles.thumbWrapPreview : ''}`}>
            <button
              type="button"
              className={styles.thumbButton}
              onClick={() => onPreview(version.id)}
              role="option"
              aria-selected={isPreview}
              aria-label={`Preview design version ${version.version_number}`}
              id={`ai-version-filmstrip-thumb-${version.id}`}
            >
              {src ? <img src={src} alt="" className={styles.thumbImage} /> : <div className={styles.thumbImage} />}

              {isUnapproved && (
                <span className={styles.warningMarker} title="Quality review: not approved">
                  <AlertTriangle className="w-3 h-3" />
                </span>
              )}

              <div className={styles.thumbFooter}>
                <span className={styles.versionLabel}>V{version.version_number}</span>
                {version.source_provider && <span className={styles.providerLabel}>{version.source_provider}</span>}
              </div>
            </button>

            <button
              type="button"
              className={styles.cardMenuBtn}
              onClick={(e) => { e.stopPropagation(); setOpenMenuId(isMenuOpen ? null : version.id); }}
              aria-label="Image actions"
              aria-expanded={isMenuOpen}
            >
              <MoreVertical className="w-3.5 h-3.5" />
            </button>

            {isMenuOpen && (
              <>
                <div className={styles.menuBackdrop} onClick={() => setOpenMenuId(null)} />
                <div className={styles.cardMenu} role="menu">
                  <button
                    type="button"
                    className={styles.menuItem}
                    role="menuitem"
                    onClick={() => { setOpenMenuId(null); onUseAsReference?.(version.id); }}
                  >
                    <Layers className="w-3.5 h-3.5" />
                    Use as Reference
                  </button>
                  <a
                    className={styles.menuItem}
                    role="menuitem"
                    href={resolveDesignImageSrc(version)}
                    download={resolveDesignImageFileName(version)}
                    onClick={() => setOpenMenuId(null)}
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download
                  </a>
                  <button type="button" className={`${styles.menuItem} ${styles.menuItemDisabled}`} role="menuitem" disabled title="Coming soon">
                    Rename
                  </button>
                  <button type="button" className={`${styles.menuItem} ${styles.menuItemDisabled}`} role="menuitem" disabled title="Coming soon">
                    Delete
                  </button>
                </div>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}
