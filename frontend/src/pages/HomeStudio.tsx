import { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { propertyService } from '../services/propertyService';
import { propertyImageService } from '../services/propertyImageService';
import { Property, PropertyImage } from '../types/index';
import { resolvePrimaryPropertyImage } from '../utils/propertyImage';
import PropertySelector from '../components/PropertySelector';
import DesignFilmstrip from '../components/DesignFilmstrip';
import OriginalImagePreview from '../components/OriginalImagePreview';
import ImageInspector from '../components/ImageInspector';
import HomeStudioUploadAction from '../components/HomeStudioUploadAction';
import LoadingState from '../components/LoadingState';
import useToast from '../hooks/useToast';
import styles from './HomeStudio.module.css';

/**
 * pages/HomeStudio.tsx
 *
 * Home Studio - the AI HOME primary design workspace, built on the
 * existing backend (through Design Studio Checkpoint 8) and the existing
 * Enterprise component/CSS library. Internally this remains the same
 * codebase, APIs, and database - nothing here renames or forks backend
 * concepts; this page only presents them under AI HOME public
 * terminology (05_AIHOME_PUBLIC_TERMINOLOGY_STANDARD.md).
 *
 * Frontend Checkpoint 2 scope: Property selection, Property Photo
 * loading, upload, large original-photo preview with prev/next
 * navigation, horizontal filmstrip, multi-selection, primary-photo
 * marking, and a right-side Contextual Inspector. Tool selection, Tool
 * Options, AI Design Job creation, Submit, Run, and Design Results are
 * explicitly NOT implemented yet - those are Checkpoints 3-5.
 *
 * The right column is the Contextual Inspector (components/
 * ImageInspector.tsx), per the WIMLOGIC Enterprise Layout Standard's
 * Inspector pattern - it is NOT a permanently-reserved empty space.
 * Right now it shows Image Information/AI Knowledge/Tags/Notes/AI
 * Readiness/Metadata for the previewed photo (or a clean empty state
 * when none is selected); future checkpoints extend this SAME panel
 * with AI Tool Configuration, AI Job Summary, AI Processing Status, and
 * Design Results as the user's context changes, rather than introducing
 * a second panel.
 *
 * Thumbnail order follows the current API response order (is_primary
 * desc -> priority desc -> created_at asc, computed client-side only).
 * Drag-to-reorder is explicitly deferred - cre_property_images has no
 * persisted ordering column today, and this checkpoint does not modify
 * the backend schema to add one. Each filmstrip item is already a
 * stable, independently-keyed unit (keyed by image id), so drag-and-drop
 * can be added later without restructuring the filmstrip.
 */
export interface HomeStudioProps {
  /**
   * The Property to open with, e.g. handed off from Dashboard's Recent
   * Properties (Checkpoint 2B correction) - lifted at App.tsx level,
   * mirroring the existing selectedProjectId pattern. Home Studio must
   * never silently fall back to whichever Property was previously
   * selected in an unrelated session; this prop is read once at mount
   * (Home Studio remounts fresh every time the user navigates to it,
   * since App.tsx's view switch produces a new element, not a
   * conditionally-hidden one) and is the authoritative starting context.
   */
  selectedPropertyId?: number | null;
  /**
   * Lifts Home Studio's own Property selector changes back up to
   * App.tsx, so the shared selectedPropertyId stays in sync if the user
   * changes Property from within Home Studio itself.
   */
  onSelectProperty?: (id: number | null) => void;
}

export default function HomeStudio({ selectedPropertyId: externalPropertyId, onSelectProperty }: HomeStudioProps) {
  const { success, error: toastError } = useToast();

  const [properties, setProperties] = useState<Property[]>([]);
  const [isLoadingProperties, setIsLoadingProperties] = useState(true);
  const [selectedPropertyId, setSelectedPropertyIdState] = useState<number | null>(externalPropertyId ?? null);

  // Resolved once per Property selection - the upload endpoint's existing
  // contract requires a business Project code, a separate entity from the
  // Property itself (cre_project_properties). Home Studio's own flow
  // selects a Property directly, so this is derived automatically rather
  // than asked of the user.
  const [resolvedProjectId, setResolvedProjectId] = useState<string | null>(null);

  const [propertyImages, setPropertyImages] = useState<PropertyImage[]>([]);
  const [isLoadingImages, setIsLoadingImages] = useState(false);
  const [imagesError, setImagesError] = useState<string | null>(null);

  const [previewImageId, setPreviewImageId] = useState<number | null>(null);
  const [selectedImageIds, setSelectedImageIds] = useState<Set<number>>(new Set());
  const [isSettingPrimary, setIsSettingPrimary] = useState(false);

  // ---- Load Properties (once) ----
  const loadProperties = useCallback(async () => {
    setIsLoadingProperties(true);
    try {
      const res = await propertyService.list({ limit: 300 });
      setProperties(res.items || []);
    } catch (err) {
      console.error('[Home Studio] Failed to load properties:', err);
      toastError('Unable to load Properties.');
    } finally {
      setIsLoadingProperties(false);
    }
  }, [toastError]);

  useEffect(() => {
    loadProperties();
  }, [loadProperties]);

  /**
   * Sort order: is_primary desc -> priority desc (nulls last) ->
   * created_at asc. Client-side only display ordering - never mutates
   * backend data.
   */
  const sortImages = (images: PropertyImage[]): PropertyImage[] => {
    return [...images].sort((a, b) => {
      if (a.is_primary !== b.is_primary) return b.is_primary - a.is_primary;
      const aPriority = a.priority ?? -Infinity;
      const bPriority = b.priority ?? -Infinity;
      if (aPriority !== bPriority) return bPriority - aPriority;
      return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    });
  };

  // ---- Load images + resolve Project association for the selected Property ----
  const loadImagesForProperty = useCallback(async (propertyId: number) => {
    setIsLoadingImages(true);
    setImagesError(null);
    try {
      const res = await propertyImageService.list({ property_id: propertyId, include_deleted: false, limit: 200 });
      const sorted = sortImages(res.items || []);
      setPropertyImages(sorted);
      // AI HOME Image Display Standard: primary -> first uploaded -> none
      // (the "no images" empty state already covers the placeholder
      // case). Uses the SAME shared helper as Dashboard's Recent
      // Properties, rather than this page's own display-sort fallback -
      // display order (priority-based) and "first uploaded" are not the
      // same thing, and conflating them was the inconsistency this
      // standard corrects.
      const primary = resolvePrimaryPropertyImage(sorted);
      setPreviewImageId(primary ? primary.id : null);
    } catch (err) {
      console.error('[Home Studio] Failed to load property photos:', err);
      setImagesError('Unable to load photos for this Property.');
    } finally {
      setIsLoadingImages(false);
    }
  }, []);

  const resolveProjectForProperty = useCallback(async (propertyId: number) => {
    try {
      const res = await propertyService.listAssociations({ property_id: propertyId, limit: 1 });
      setResolvedProjectId(res.items?.[0]?.project_id ?? null);
    } catch (err) {
      console.error('[Home Studio] Failed to resolve Project association:', err);
      setResolvedProjectId(null);
    }
  }, []);

  const handlePropertyChange = (propertyId: number | null) => {
    setSelectedPropertyIdState(propertyId);
    onSelectProperty?.(propertyId);
    setPreviewImageId(null);
    setSelectedImageIds(new Set());
    setImagesError(null);
    setPropertyImages([]);
    setResolvedProjectId(null);

    if (propertyId !== null) {
      loadImagesForProperty(propertyId);
      resolveProjectForProperty(propertyId);
    }
  };

  // Auto-load images/Project context for a Property handed off from
  // elsewhere (e.g. Dashboard's Recent Properties) - runs once on mount
  // only. Home Studio remounts fresh every time the user navigates to
  // it (App.tsx's view switch produces a new element rather than a
  // conditionally-hidden one), so reading externalPropertyId once here
  // is correct and does not need to react to later prop changes.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (externalPropertyId != null) {
      loadImagesForProperty(externalPropertyId);
      resolveProjectForProperty(externalPropertyId);
    }
  }, []);

  const handleRefresh = () => {
    if (selectedPropertyId !== null) {
      loadImagesForProperty(selectedPropertyId);
    }
  };

  // ---- Filmstrip interactions ----
  const handlePreview = (imageId: number) => setPreviewImageId(imageId);

  const handlePrev = () => {
    if (propertyImages.length === 0 || previewImageId === null) return;
    const currentIndex = propertyImages.findIndex((img) => img.id === previewImageId);
    const prevIndex = (currentIndex - 1 + propertyImages.length) % propertyImages.length;
    setPreviewImageId(propertyImages[prevIndex].id);
  };

  const handleNext = () => {
    if (propertyImages.length === 0 || previewImageId === null) return;
    const currentIndex = propertyImages.findIndex((img) => img.id === previewImageId);
    const nextIndex = (currentIndex + 1) % propertyImages.length;
    setPreviewImageId(propertyImages[nextIndex].id);
  };

  const handleToggleSelect = (imageId: number) => {
    setSelectedImageIds((prev) => {
      const next = new Set(prev);
      if (next.has(imageId)) {
        next.delete(imageId);
      } else {
        next.add(imageId);
      }
      return next;
    });
  };

  const handleSetPrimary = async (imageId: number) => {
    setIsSettingPrimary(true);
    try {
      await propertyImageService.setPrimary(imageId);
      if (selectedPropertyId !== null) {
        await loadImagesForProperty(selectedPropertyId);
      }
      success('Primary Photo updated.');
    } catch (err) {
      console.error('[Home Studio] Failed to set primary photo:', err);
      toastError('Failed to update the Primary Photo.');
    } finally {
      setIsSettingPrimary(false);
    }
  };

  const handleUploaded = (newImages: PropertyImage[]) => {
    setPropertyImages((prev) => sortImages([...prev, ...newImages]));
    success(newImages.length === 1 ? 'Photo uploaded.' : `${newImages.length} photos uploaded.`);
  };

  const handleImageContextSaved = async (updated: PropertyImage) => {
    // If the save changed primary status (via ImageInspector's own
    // setPrimary call), a SECOND row may also have changed on the
    // backend - reload the full list rather than patch just this one.
    if (updated.is_primary === 1 && selectedPropertyId !== null) {
      await loadImagesForProperty(selectedPropertyId);
      return;
    }
    setPropertyImages((prev) => sortImages(prev.map((img) => (img.id === updated.id ? updated : img))));
  };

  const previewImage = useMemo(
    () => propertyImages.find((img) => img.id === previewImageId) ?? null,
    [propertyImages, previewImageId]
  );

  return (
    <div className={styles.workspaceContainer} id="home-studio-page">
      <div className={styles.headerArea}>
        <h1 className={styles.pageTitle}>Home Studio</h1>
        <p className={styles.pageSubtitle}>Design and visualize property improvements.</p>
      </div>

      <div className={styles.commandBar}>
        <PropertySelector
          properties={properties}
          selectedPropertyId={selectedPropertyId}
          onChange={handlePropertyChange}
        />

        {selectedPropertyId !== null && (
          <HomeStudioUploadAction
            propertyId={selectedPropertyId}
            resolvedProjectId={resolvedProjectId}
            onUploaded={handleUploaded}
            onError={toastError}
          />
        )}

        <button
          type="button"
          className="enterprise-btn enterprise-btn-ghost"
          onClick={handleRefresh}
          disabled={selectedPropertyId === null}
          id="home-studio-refresh-btn"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {imagesError && <div className={styles.errorBanner}>{imagesError}</div>}

      <div className={styles.mainRow}>
        <div className={styles.previewColumn}>
          {isLoadingProperties || isLoadingImages ? (
            <LoadingState message="Loading..." type="skeleton" />
          ) : (
            <OriginalImagePreview
              hasSelectedProperty={selectedPropertyId !== null}
              hasImages={propertyImages.length > 0}
              previewImage={previewImage}
              onPrev={propertyImages.length > 1 ? handlePrev : undefined}
              onNext={propertyImages.length > 1 ? handleNext : undefined}
            />
          )}

          <div className={styles.filmstripArea}>
            {selectedPropertyId !== null && (
              <div className={styles.filmstripHeader}>
                <div className={styles.filmstripHeaderLeft}>
                  <span className={styles.filmstripTitle}>Property Photos</span>
                  <span className={styles.filmstripCount}>{propertyImages.length}</span>
                </div>
                {/* Reserved for future actions (Upload / Refresh / Compare /
                    Expand) - spacing only, no functionality yet per Checkpoint 2B. */}
                <div className={styles.filmstripHeaderRight} />
              </div>
            )}
            {!isLoadingImages && selectedPropertyId !== null && (
              <DesignFilmstrip
                images={propertyImages}
                previewImageId={previewImageId}
                selectedImageIds={selectedImageIds}
                onPreview={handlePreview}
                onToggleSelect={handleToggleSelect}
                onSetPrimary={handleSetPrimary}
                isSettingPrimary={isSettingPrimary}
              />
            )}
          </div>
        </div>

        <div className={styles.inspectorColumn} id="home-studio-inspector-panel">
          <ImageInspector image={previewImage} onSaved={handleImageContextSaved} />
        </div>
      </div>
    </div>
  );
}
