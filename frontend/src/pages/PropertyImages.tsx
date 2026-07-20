import { useState, useEffect, useRef, useCallback } from 'react';
import { propertyImageService } from '../services/propertyImageService';
import { projectService } from '../services/projectService';
import { propertyService } from '../services/propertyService';
import type { PropertyImage, Project, Property } from '../types/index';
import {
  Upload,
  Trash2,
  Image as ImageIcon,
  X,
  RefreshCw,
  CircleHelp,
  ChevronLeft,
  ChevronRight,
  Eye,
  Pencil,
  Star,
} from 'lucide-react';

import EnterpriseCard from '../components/EnterpriseCard';
import EnterpriseSelect from '../components/EnterpriseSelect';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';
import ConfirmDialog from '../components/ConfirmDialog';
import StatusBadge from '../components/StatusBadge';
import FormField from '../components/FormField';
import useToast from '../hooks/useToast';
import { formatDate } from '../utils/formatters';
import { resolveImageSrc, resolveImageFileName } from '../utils/imageUrl';
import { IMAGE_ROLE_OPTIONS } from '../utils/imageContext';
import styles from './PropertyImages.module.css';

/**
 * Real image categories, taken directly from the locked backend schema
 * (`cre_property_images.image_type` enum). Only these four exist in the
 * database today.
 */
const IMAGE_CATEGORIES: { value: string; label: string }[] = [
  { value: 'street_view', label: 'Street View' },
  { value: 'satellite', label: 'Satellite / Aerial' },
  { value: 'parcel_map', label: 'Parcel Map' },
  { value: 'uploaded', label: 'Uploaded' },
];

/**
 * Status controlled-vocabulary. AUDIT NOTE: cre_property_images.status is
 * also a plain nullable varchar(50) with zero backend enforcement - no
 * CHECK constraint, no Pydantic Literal, no CRUD/service validation.
 * "deleted" is deliberately excluded: soft-delete is handled entirely
 * through the dedicated DELETE /property-images/{id}?soft=true endpoint
 * (property_image_service.delete_image(), which sets is_deleted=1 and
 * forces is_primary=0 - it never touches this status field at all), so
 * exposing "Deleted" here would invent a second, backend-disconnected
 * deletion path.
 */
const IMAGE_STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: 'uploaded', label: 'Uploaded' },
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
  { value: 'archived', label: 'Archived' },
];

const GALLERY_PAGE_SIZE = 5;

function categoryLabel(value?: string): string {
  return IMAGE_CATEGORIES.find((c) => c.value === value)?.label || value || 'Uncategorized';
}

/**
 * Uses the real is_primary column/endpoint (Checkpoint 5), not the stale
 * image_role === 'primary' text convention this used to rely on -
 * corrected per the Image Role/Status controlled-dropdown pass.
 */
function isPrimaryImage(img: PropertyImage): boolean {
  return img.is_primary === 1;
}

interface UploadQueueItem {
  key: string;
  fileName: string;
  previewUrl: string;
  progress: number;
  status: 'uploading' | 'done' | 'error';
  errorMessage?: string;
}

export default function PropertyImages() {
  const { success, error: toastError } = useToast();

  const [projects, setProjects] = useState<Project[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [selectedPropertyId, setSelectedPropertyId] = useState<string>('');

  const [images, setImages] = useState<PropertyImage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  const [galleryPage, setGalleryPage] = useState(0);

  const [detailImage, setDetailImage] = useState<PropertyImage | null>(null);
  const [detailDraft, setDetailDraft] = useState<{ notes: string; status: string; image_role: string }>({
    notes: '',
    status: '',
    image_role: '',
  });
  const [isSavingDetail, setIsSavingDetail] = useState(false);

  const [confirmSingleDeleteId, setConfirmSingleDeleteId] = useState<number | null>(null);

  // Compact upload toolbar state
  const [uploadCategory, setUploadCategory] = useState('uploaded');
  const [uploadNotes, setUploadNotes] = useState('');
  const [uploadIsPrimary, setUploadIsPrimary] = useState(false);
  const [uploadQueue, setUploadQueue] = useState<UploadQueueItem[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // ---- Load Projects ----
  const loadInitialData = useCallback(async () => {
    try {
      const res = await projectService.list({ limit: 300 });
      setProjects(res.items || []);
      if (res.items.length > 0) {
        setSelectedProjectId(res.items[0].project_id);
      }
    } catch (err) {
      console.error('[Property Images] Failed to load projects:', err);
      setErrorMsg('Unable to load projects from the backend.');
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // ---- Load Properties for selected Project ----
  useEffect(() => {
    async function loadPropertiesForProject() {
      if (!selectedProjectId) {
        setProperties([]);
        setSelectedPropertyId('');
        return;
      }
      try {
        const props = await propertyService.listByProject(selectedProjectId);
        setProperties(props);
        setSelectedPropertyId(props.length > 0 ? String(props[0].id) : '');
      } catch (err) {
        console.error('[Property Images] Failed to load properties:', err);
        setErrorMsg('Unable to load properties for the selected project.');
      }
    }
    loadPropertiesForProject();
  }, [selectedProjectId]);

  // ---- Load Images ----
  const loadImages = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg('');
    try {
      const params: Record<string, unknown> = {
        include_deleted: false,
        limit: 200,
      };
      if (selectedProjectId) params.project_id = selectedProjectId;
      if (selectedPropertyId) params.property_id = Number(selectedPropertyId);

      const res = await propertyImageService.list(params);
      setImages(res.items || []);
      setGalleryPage(0);
    } catch (err) {
      console.error('[Property Images] Failed to load images:', err);
      setErrorMsg('Error loading property images from backend.');
    } finally {
      setIsLoading(false);
    }
  }, [selectedProjectId, selectedPropertyId]);

  useEffect(() => {
    loadImages();
  }, [selectedProjectId, selectedPropertyId]);

  const selectedProperty = properties.find((p) => String(p.id) === selectedPropertyId);
  const currentProject = projects.find((p) => p.project_id === selectedProjectId);

  const totalPages = Math.max(1, Math.ceil(images.length / GALLERY_PAGE_SIZE));
  const visibleImages = images.slice(
    galleryPage * GALLERY_PAGE_SIZE,
    galleryPage * GALLERY_PAGE_SIZE + GALLERY_PAGE_SIZE
  );

  const goPrevPage = () => setGalleryPage((p) => Math.max(0, p - 1));
  const goNextPage = () => setGalleryPage((p) => Math.min(totalPages - 1, p + 1));

  // ---- Detail panel ----
  const openDetail = (img: PropertyImage) => {
    setDetailImage(img);
    setDetailDraft({
      notes: img.notes || '',
      status: img.status || '',
      image_role: img.image_role || '',
    });
  };

  const closeDetail = () => setDetailImage(null);

  const handleSaveDetail = async () => {
    if (!detailImage) return;
    setIsSavingDetail(true);
    try {
      const wantsPrimary = detailDraft.image_role === 'primary';
      const isCurrentlyPrimary = detailImage.is_primary === 1;

      let updated: PropertyImage;

      if (wantsPrimary && !isCurrentlyPrimary) {
        // Selecting "Primary" must use the real primary-image endpoint -
        // it enforces the one-primary-per-property invariant and clears
        // whichever OTHER image currently holds it. A plain text write
        // to image_role alone would never do that.
        await propertyImageService.setPrimary(detailImage.id);
        updated = await propertyImageService.update(detailImage.id, {
          notes: detailDraft.notes,
          status: detailDraft.status,
          image_role: detailDraft.image_role,
        });
      } else if (!wantsPrimary && isCurrentlyPrimary) {
        // Moving THIS image away from Primary. Confirmed via source
        // audit that the backend's generic update path supports
        // explicitly clearing is_primary (falls through to a plain
        // single-row update when is_primary=0 is supplied) without
        // requiring another image to take over first - the Property may
        // temporarily have no primary image, same as the existing
        // soft-delete behavior already does. No frontend-only state is
        // invented here; this is the backend's own supported operation.
        updated = await propertyImageService.update(detailImage.id, {
          notes: detailDraft.notes,
          status: detailDraft.status,
          image_role: detailDraft.image_role,
          is_primary: 0,
        });
      } else {
        updated = await propertyImageService.update(detailImage.id, {
          notes: detailDraft.notes,
          status: detailDraft.status,
          image_role: detailDraft.image_role,
        });
      }

      // A primary change (either branch above) can affect a SECOND row
      // too - reload the full list so every card reflects the backend's
      // actual current state, not just this one row.
      if (wantsPrimary !== isCurrentlyPrimary) {
        await loadImages();
      } else {
        setImages((prev) => prev.map((img) => (img.id === updated.id ? updated : img)));
      }
      setDetailImage(updated);
      success('Image details updated.');
    } catch (err: any) {
      console.error('[Property Images] Failed to update image:', err);
      toastError(err?.message || 'Failed to save image details.');
    } finally {
      setIsSavingDetail(false);
    }
  };

  const handleMakePrimary = async (img: PropertyImage) => {
    try {
      await propertyImageService.setPrimary(img.id);
      // A primary change affects a SECOND row too (the prior primary
      // image's is_primary flips to 0 on the backend) - a full reload is
      // the correct way to reflect that, not a local single-row patch.
      await loadImages();
      if (detailImage?.id === img.id) {
        setDetailImage((prev) => (prev ? { ...prev, is_primary: 1 } : prev));
      }
      success('Marked as primary image.');
    } catch (err) {
      console.error('[Property Images] Failed to set primary image:', err);
      toastError('Failed to update primary image.');
    }
  };

  // ---- Delete ----
  const handleConfirmSingleDelete = async () => {
    if (confirmSingleDeleteId === null) return;
    try {
      await propertyImageService.delete(confirmSingleDeleteId, false);
      setImages((prev) => prev.filter((img) => img.id !== confirmSingleDeleteId));
      if (detailImage?.id === confirmSingleDeleteId) setDetailImage(null);
      success('Image removed.');
    } catch (err) {
      console.error('[Property Images] Failed to delete image:', err);
      toastError('Failed to remove image.');
    } finally {
      setConfirmSingleDeleteId(null);
    }
  };

  // ---- Upload ----
  const handleFiles = (files: FileList | File[]) => {
    if (!selectedPropertyId || !selectedProjectId) {
      toastError('Select a Project and Property before uploading images.');
      return;
    }

    // IMPORTANT: the upload endpoint requires the numeric database property_id,
    // never the business-facing property_uid. Resolve it from the
    // already-fetched Property record's `.id` field.
    const propertyId = selectedProperty?.id;
    if (propertyId === undefined || Number.isNaN(propertyId)) {
      toastError('Could not resolve the numeric property ID for the selected property.');
      return;
    }
    const projectId = selectedProjectId;

    Array.from(files).forEach((file) => {
      const key = `${file.name}-${file.size}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      const previewUrl = URL.createObjectURL(file);

      setUploadQueue((prev) => [
        ...prev,
        { key, fileName: file.name, previewUrl, progress: 0, status: 'uploading' },
      ]);

      const { promise } = propertyImageService.uploadWithProgress(
        {
          file,
          property_id: propertyId,
          project_id: projectId,
          image_type: uploadCategory,
          notes: uploadNotes || undefined,
          image_role: uploadIsPrimary ? 'primary' : undefined,
        },
        (percent) => {
          setUploadQueue((prev) =>
            prev.map((item) => (item.key === key ? { ...item, progress: percent } : item))
          );
        }
      );

      promise
        .then((newImage) => {
          setUploadQueue((prev) =>
            prev.map((item) => (item.key === key ? { ...item, progress: 100, status: 'done' } : item))
          );
          setImages((prev) => [newImage, ...prev]);
          setGalleryPage(0);
          success(`${file.name} uploaded.`);
          setTimeout(() => {
            setUploadQueue((prev) => prev.filter((item) => item.key !== key));
          }, 2000);
        })
        .catch((err) => {
          console.error('[Property Images] Upload failed:', err);
          setUploadQueue((prev) =>
            prev.map((item) =>
              item.key === key
                ? { ...item, status: 'error', errorMessage: err?.message || 'Upload failed' }
                : item
            )
          );
          toastError(`Failed to upload ${file.name}.`);
        });
    });
  };

  const dismissUploadItem = (key: string) => {
    setUploadQueue((prev) => prev.filter((item) => item.key !== key));
  };

  return (
    <div className={styles.workspaceContainer} id="property-images-page">
      {/* Header */}
      <div className={styles.headerArea}>
        <div className={styles.titleArea}>
          <h1 className={styles.pageTitle}>Property Images</h1>
          <p className={styles.pageSubtitle}>
            Manage image assets and prepare properties for AI-assisted design.
          </p>
        </div>

        <div className={styles.headerActions}>
          <div className={styles.contextSelects}>
            <select
              className={styles.contextSelect}
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              id="property-images-project-select"
            >
              {projects.length === 0 && <option value="">No Projects</option>}
              {projects.map((p) => (
                <option key={p.project_id} value={p.project_id}>
                  [{p.project_id}] {p.project_name}
                </option>
              ))}
            </select>
            <select
              className={styles.contextSelect}
              value={selectedPropertyId}
              onChange={(e) => setSelectedPropertyId(e.target.value)}
              disabled={properties.length === 0}
              id="property-images-property-select"
            >
              {properties.length === 0 && <option value="">No Properties</option>}
              {properties.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.address || p.property_uid}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            className="enterprise-btn enterprise-btn-secondary"
            onClick={loadImages}
            id="property-images-refresh-btn"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
        </div>
      </div>

      {errorMsg && <div className={styles.errorBanner}>{errorMsg}</div>}

      {/* TOP: Property Summary */}
      <EnterpriseCard id="property-images-summary-card">
        <div className={styles.summaryRow}>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Project</span>
            <span className={styles.summaryValue}>{currentProject?.project_name || '—'}</span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Property</span>
            <span className={styles.summaryValue}>
              {selectedProperty?.address || selectedProperty?.property_uid || '—'}
            </span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Property UID</span>
            <span className={`${styles.summaryValue} ${styles.summaryValueMono}`}>
              {selectedProperty?.property_uid || '—'}
            </span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Status</span>
            <span className={styles.summaryValue}>{selectedProperty?.status || '—'}</span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Image Count</span>
            <span className={`${styles.summaryValue} ${styles.summaryValueMono}`}>{images.length}</span>
          </div>
        </div>
      </EnterpriseCard>

      {/* MIDDLE: Horizontal Image Gallery, max 5 visible at once */}
      <EnterpriseCard
        title="Image Gallery"
        subtitle={images.length > 0 ? `Showing ${visibleImages.length} of ${images.length} images` : undefined}
        id="property-images-gallery-card"
      >
        {isLoading ? (
          <LoadingState message="Loading property images..." type="skeleton" />
        ) : images.length === 0 ? (
          <EmptyState
            title="No Images Available"
            description={
              selectedPropertyId
                ? 'This property has no image records yet. Upload images below to get started.'
                : 'Select a Project and Property to view or upload images.'
            }
            icon={ImageIcon}
          />
        ) : (
          <div className={styles.galleryRow}>
            <button
              type="button"
              className={styles.galleryNavBtn}
              onClick={goPrevPage}
              disabled={galleryPage === 0}
              aria-label="Previous images"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <div className={styles.galleryTrack} id="property-images-gallery-track">
              {visibleImages.map((img) => (
                <div key={img.id} className={`${styles.galleryCard} enterprise-card`}>
                  <div className={styles.galleryThumbWrap}>
                    {resolveImageSrc(img) ? (
                      <img src={resolveImageSrc(img)} alt={resolveImageFileName(img)} className={styles.galleryThumb} />
                    ) : (
                      <div className={styles.galleryThumb} />
                    )}
                    {isPrimaryImage(img) && (
                      <span className={styles.primaryBadge}>
                        <Star className="w-3 h-3" />
                        Primary
                      </span>
                    )}
                    <span className={styles.categoryBadge}>{categoryLabel(img.image_type)}</span>
                  </div>
                  <div className={styles.galleryCardBody}>
                    <div className={styles.galleryCardTitleRow}>
                      <span className={styles.galleryFileName}>{resolveImageFileName(img)}</span>
                      <StatusBadge status={img.status} type="property" />
                    </div>
                    <div className={styles.galleryActions}>
                      <button
                        type="button"
                        className={styles.galleryActionBtn}
                        onClick={() => openDetail(img)}
                        title="View"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        className={styles.galleryActionBtn}
                        onClick={() => openDetail(img)}
                        title="Edit"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        className={styles.galleryActionBtn}
                        onClick={() => handleMakePrimary(img)}
                        title="Set as primary"
                        disabled={isPrimaryImage(img)}
                      >
                        <Star className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        className={`${styles.galleryActionBtn} ${styles.galleryActionBtnDanger}`}
                        onClick={() => setConfirmSingleDeleteId(img.id)}
                        title="Delete"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <button
              type="button"
              className={styles.galleryNavBtn}
              onClick={goNextPage}
              disabled={galleryPage >= totalPages - 1}
              aria-label="Next images"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {images.length > GALLERY_PAGE_SIZE && (
          <div className={styles.galleryPagerInfo}>
            Page {galleryPage + 1} of {totalPages}
          </div>
        )}
      </EnterpriseCard>

      {/* BOTTOM: Compact single-row Upload toolbar */}
      <EnterpriseCard title="Upload Images" id="property-images-upload-card">
        <div className={styles.uploadToolbarRow}>
          <select
            className="enterprise-form-input"
            value={uploadCategory}
            onChange={(e) => setUploadCategory(e.target.value)}
            id="upload-category-select"
            style={{ maxWidth: '11rem' }}
          >
            {IMAGE_CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>

          <input
            type="text"
            className="enterprise-form-input"
            value={uploadNotes}
            onChange={(e) => setUploadNotes(e.target.value)}
            placeholder="Notes (optional)"
            id="upload-notes-input"
            style={{ flex: '1 1 auto', minWidth: '10rem' }}
          />

          <label className={styles.uploadPrimaryCheckboxLabel}>
            <input
              type="checkbox"
              className="enterprise-form-checkbox"
              checked={uploadIsPrimary}
              onChange={(e) => setUploadIsPrimary(e.target.checked)}
              id="upload-primary-checkbox"
            />
            Primary Image
          </label>

          <button
            type="button"
            className="enterprise-btn enterprise-btn-secondary"
            onClick={() => fileInputRef.current?.click()}
            id="upload-choose-files-btn"
          >
            <Upload className="w-3.5 h-3.5" />
            Choose Files
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept=".jpg,.jpeg,.png,.webp"
            multiple
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files?.length) handleFiles(e.target.files);
              e.target.value = '';
            }}
            id="property-images-file-input"
          />
        </div>

        {uploadQueue.length > 0 && (
          <div className={styles.uploadQueue}>
            {uploadQueue.map((item) => (
              <div key={item.key} className={styles.uploadQueueItem}>
                <img src={item.previewUrl} alt={item.fileName} className={styles.uploadThumb} />
                <div className={styles.uploadItemBody}>
                  <span className={styles.uploadItemName}>{item.fileName}</span>
                  <div className={styles.progressTrack}>
                    <div
                      className={`${styles.progressFill} ${
                        item.status === 'error' ? styles.progressFillError : ''
                      } ${item.status === 'done' ? styles.progressFillDone : ''}`}
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                  <span className={styles.uploadItemMeta}>
                    {item.status === 'uploading' && `Uploading - ${item.progress}%`}
                    {item.status === 'done' && 'Upload complete'}
                    {item.status === 'error' && (item.errorMessage || 'Upload failed')}
                  </span>
                </div>
                <button
                  type="button"
                  className={styles.uploadItemAction}
                  onClick={() => dismissUploadItem(item.key)}
                  title="Dismiss"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </EnterpriseCard>

      {/* Detail Panel */}
      {detailImage && (
        <div className={styles.detailOverlay} onClick={closeDetail} id="property-images-detail-overlay">
          <div className={styles.detailPanel} onClick={(e) => e.stopPropagation()}>
            <div className={styles.detailHeader}>
              <span className={styles.detailHeaderTitle}>{resolveImageFileName(detailImage)}</span>
              <button type="button" className={styles.detailCloseBtn} onClick={closeDetail}>
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className={styles.detailScroll}>
              <div className={styles.detailPreview}>
                {resolveImageSrc(detailImage) ? (
                  <img
                    src={resolveImageSrc(detailImage)}
                    alt={resolveImageFileName(detailImage)}
                    className={styles.detailPreviewImg}
                  />
                ) : null}
              </div>

              <div>
                <div className={styles.detailSectionTitle}>General Information</div>
                <div className={styles.metaGrid}>
                  <div className={styles.metaItem}>
                    <span className={styles.metaLabel}>Category</span>
                    <span className={styles.metaValue}>{categoryLabel(detailImage.image_type)}</span>
                  </div>
                  <div className={styles.metaItem}>
                    <span className={styles.metaLabel}>Provider</span>
                    <span className={styles.metaValue}>{detailImage.provider || '—'}</span>
                  </div>
                  <div className={styles.metaItem}>
                    <span className={styles.metaLabel}>File Type</span>
                    <span className={styles.metaValue}>{detailImage.file_type || '—'}</span>
                  </div>
                  <div className={styles.metaItem}>
                    <span className={styles.metaLabel}>Uploaded</span>
                    <span className={styles.metaValue}>{formatDate(detailImage.created_at)}</span>
                  </div>
                </div>
              </div>

              <div>
                <div className={styles.detailSectionTitle}>AI Workflow Readiness</div>
                <div className={styles.readinessCard}>
                  <CircleHelp className="w-4 h-4" style={{ color: 'var(--color-neutral-400)' }} />
                  <span className={styles.readinessText}>
                    Not available - no AI readiness field is configured on the backend for this image yet.
                  </span>
                </div>
              </div>

              <div>
                <div className={styles.detailSectionTitle}>Business Notes</div>
                <FormField label="Image Role" id="detail-image-role-field" helpText="Selecting Primary makes this the property's one Primary Image; any other image currently primary will be cleared.">
                  <EnterpriseSelect
                    id="detail-image-role-select"
                    value={detailDraft.image_role}
                    options={IMAGE_ROLE_OPTIONS}
                    placeholder="Select a role"
                    onChange={(value) => setDetailDraft((prev) => ({ ...prev, image_role: value }))}
                    disabled={isSavingDetail}
                  />
                </FormField>
                <FormField label="Status" id="detail-status-field">
                  <EnterpriseSelect
                    id="detail-status-select"
                    value={detailDraft.status}
                    options={IMAGE_STATUS_OPTIONS}
                    placeholder="Select a status"
                    onChange={(value) => setDetailDraft((prev) => ({ ...prev, status: value }))}
                    disabled={isSavingDetail}
                  />
                </FormField>
                <FormField label="Notes" id="detail-notes-field">
                  <textarea
                    className="enterprise-form-input"
                    rows={3}
                    value={detailDraft.notes}
                    onChange={(e) => setDetailDraft((prev) => ({ ...prev, notes: e.target.value }))}
                    placeholder="Visual observations, structural notes, capture quality..."
                  />
                </FormField>
              </div>
            </div>

            <div className={styles.detailFooter}>
              <button
                type="button"
                className="enterprise-btn enterprise-btn-secondary"
                onClick={() => setConfirmSingleDeleteId(detailImage.id)}
                style={{ color: '#ef4444' }}
              >
                <Trash2 className="w-3.5 h-3.5" />
                Delete
              </button>
              <button
                type="button"
                className="enterprise-btn enterprise-btn-primary"
                onClick={handleSaveDetail}
                disabled={isSavingDetail || !detailDraft.image_role || !detailDraft.status}
                title={
                  !detailDraft.image_role || !detailDraft.status
                    ? 'Select an Image Role and a Status before saving'
                    : undefined
                }
              >
                {isSavingDetail ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={confirmSingleDeleteId !== null}
        title="Remove Image"
        message="Are you sure you want to remove this image record? This action cannot be undone."
        confirmLabel="Remove"
        isDanger
        onConfirm={handleConfirmSingleDelete}
        onCancel={() => setConfirmSingleDeleteId(null)}
      />
    </div>
  );
}
