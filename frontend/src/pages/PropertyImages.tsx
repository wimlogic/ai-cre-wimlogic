import React, { useState, useEffect, useRef, useCallback } from 'react';
import { propertyImageService } from '../services/propertyImageService';
import { projectService } from '../services/projectService';
import { propertyService } from '../services/propertyService';
import type { PropertyImage, Project, Property } from '../types/index';
import { AppConfig } from '../config/app';
import {
  Upload,
  Trash2,
  Image as ImageIcon,
  X,
  LayoutGrid,
  Rows3,
  RefreshCw,
  CircleHelp,
} from 'lucide-react';

import EnterpriseToolbar from '../components/EnterpriseToolbar';
import EnterpriseCard from '../components/EnterpriseCard';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';
import ConfirmDialog from '../components/ConfirmDialog';
import StatusBadge from '../components/StatusBadge';
import FormField from '../components/FormField';
import useToast from '../hooks/useToast';
import { formatDate } from '../utils/formatters';
import styles from './PropertyImages.module.css';

/**
 * Real image categories, taken directly from the locked backend schema
 * (`cre_property_images.image_type` enum). The WIMLOGIC Property Images spec
 * lists additional categories (drone photography, floor plans, comparable
 * photos, etc.) that do not exist in the database today - only these four
 * are real, so only these four are used for category-coverage reporting.
 */
const IMAGE_CATEGORIES: { value: string; label: string }[] = [
  { value: 'street_view', label: 'Street View' },
  { value: 'satellite', label: 'Satellite / Aerial' },
  { value: 'parcel_map', label: 'Parcel Map' },
  { value: 'uploaded', label: 'Uploaded' },
];

function categoryLabel(value?: string): string {
  return IMAGE_CATEGORIES.find((c) => c.value === value)?.label || value || 'Uncategorized';
}

function formatBytes(bytes?: number): string {
  if (bytes === undefined || bytes === null) return '—';
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function displayFileName(img: PropertyImage): string {
  if (img.original_file_name) return img.original_file_name;
  if (img.image_url) {
    try {
      const parts = img.image_url.split('/');
      return parts[parts.length - 1] || `image-${img.id}`;
    } catch {
      return `image-${img.id}`;
    }
  }
  return `image-${img.id}`;
}

function resolveSrc(img: PropertyImage): string {
  // Imported images (Street View, satellite, external URLs) already have a
  // full absolute image_url - render directly.
  if (img.image_url) return img.image_url;

  // Uploaded images only have cached_path, a relative POSIX-style path
  // (e.g. "properties/927/original/6e3dc6c2....jpg") with no scheme or host.
  // Using it directly as an <img src> resolves it relative to the current
  // page URL, not the backend's static file server - that mismatch is what
  // produced the broken image icon. Resolve it against the configured
  // upload base URL instead.
  if (img.cached_path) {
    const base = AppConfig.uploadBaseUrl.replace(/\/$/, '');
    const path = img.cached_path.replace(/^\//, '');
    return `${base}/${path}`;
  }

  return '';
}

type ViewMode = 'gallery' | 'list';

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

  const [searchQuery, setSearchQuery] = useState('');
  const [imageTypeFilter, setImageTypeFilter] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('gallery');

  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [detailImage, setDetailImage] = useState<PropertyImage | null>(null);
  const [detailDraft, setDetailDraft] = useState<{ notes: string; status: string; image_role: string }>({
    notes: '',
    status: '',
    image_role: '',
  });
  const [isSavingDetail, setIsSavingDetail] = useState(false);

  const [confirmSingleDeleteId, setConfirmSingleDeleteId] = useState<number | null>(null);
  const [confirmBulkDelete, setConfirmBulkDelete] = useState(false);

  const [uploadCategory, setUploadCategory] = useState('uploaded');
  const [isDropzoneActive, setIsDropzoneActive] = useState(false);
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
      if (imageTypeFilter) params.image_type = imageTypeFilter;
      if (searchQuery.trim()) params.search = searchQuery.trim();

      const res = await propertyImageService.list(params);
      setImages(res.items || []);
      setSelectedIds(new Set());
    } catch (err) {
      console.error('[Property Images] Failed to load images:', err);
      setErrorMsg('Error loading property images from backend.');
    } finally {
      setIsLoading(false);
    }
  }, [selectedProjectId, selectedPropertyId, imageTypeFilter, searchQuery]);

  useEffect(() => {
    const timeout = setTimeout(
      () => {
        loadImages();
      },
      searchQuery ? 300 : 0
    );
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProjectId, selectedPropertyId, imageTypeFilter, searchQuery]);

  const selectedProperty = properties.find((p) => String(p.id) === selectedPropertyId);

  // ---- KPI derivations (real data only) ----
  const totalImages = images.length;
  const totalStorage = images.reduce((sum, img) => sum + (img.file_size || 0), 0);
  const statusCounts = images.reduce<Record<string, number>>((acc, img) => {
    const key = (img.status || 'Unspecified').trim();
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  const presentCategories = new Set(images.map((img) => img.image_type));

  // ---- Selection ----
  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const clearSelection = () => setSelectedIds(new Set());

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
      const updated = await propertyImageService.update(detailImage.id, {
        notes: detailDraft.notes,
        status: detailDraft.status,
        image_role: detailDraft.image_role,
      });
      setImages((prev) => prev.map((img) => (img.id === updated.id ? updated : img)));
      setDetailImage(updated);
      success('Image details updated.');
    } catch (err) {
      console.error('[Property Images] Failed to update image:', err);
      toastError('Failed to save image details.');
    } finally {
      setIsSavingDetail(false);
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

  const handleConfirmBulkDelete = async () => {
    const ids = Array.from(selectedIds);
    try {
      await Promise.all(ids.map((id) => propertyImageService.delete(id, false)));
      setImages((prev) => prev.filter((img) => !selectedIds.has(img.id)));
      clearSelection();
      success(`${ids.length} image${ids.length === 1 ? '' : 's'} removed.`);
    } catch (err) {
      console.error('[Property Images] Bulk delete failed:', err);
      toastError('Some images could not be removed.');
      loadImages();
    } finally {
      setConfirmBulkDelete(false);
    }
  };

  // ---- Upload ----
  const handleFiles = (files: FileList | File[]) => {
    if (!selectedPropertyId || !selectedProjectId) {
      toastError('Select a Project and Property before uploading images.');
      return;
    }

    // IMPORTANT: the upload endpoint requires the numeric database property_id
    // (e.g. 927), never the business-facing property_uid (e.g. "UID-83788").
    // Resolve it from the already-fetched Property record's `.id` field rather
    // than trusting derived string state, to guarantee the correct value.
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

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDropzoneActive(false);
    if (e.dataTransfer.files?.length) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const dismissUploadItem = (key: string) => {
    setUploadQueue((prev) => prev.filter((item) => item.key !== key));
  };

  const filteredImages = images;

  return (
    <div className={styles.workspaceContainer} id="property-images-page">
      {/* Header */}
      <div className={styles.headerArea}>
        <div className={styles.titleArea}>
          <div className={styles.breadcrumbs}>
            <span>WIMLOGIC</span>
            <span>/</span>
            <span className={styles.breadcrumbActive}>Property Images</span>
          </div>
          <h1 className={styles.pageTitle}>Property Images</h1>
          <p className={styles.pageSubtitle}>
            Manage image assets and prepare properties for AI-assisted workflows.
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

      {/* KPI Summary */}
      <div className={styles.summaryGrid}>
        <div className={`enterprise-card ${styles.summaryCard}`}>
          <span className={styles.summaryLabel}>Total Images</span>
          <span className={styles.summaryValue}>{totalImages}</span>
        </div>
        <div className={`enterprise-card ${styles.summaryCard}`}>
          <span className={styles.summaryLabel}>Storage Used</span>
          <span className={styles.summaryValue}>{formatBytes(totalStorage)}</span>
          <span className={styles.summaryHint}>Based on file_size across loaded records</span>
        </div>
        <div className={`enterprise-card ${styles.summaryCard}`}>
          <span className={styles.summaryLabel}>Category Coverage</span>
          <span className={styles.summaryValue}>
            {presentCategories.size}/{IMAGE_CATEGORIES.length}
          </span>
          <div className={styles.categoryChipRow}>
            {IMAGE_CATEGORIES.map((cat) => (
              <span
                key={cat.value}
                className={`${styles.categoryChip} ${
                  presentCategories.has(cat.value) ? styles.categoryChipPresent : styles.categoryChipMissing
                }`}
              >
                {cat.label}
              </span>
            ))}
          </div>
        </div>
        <div className={`enterprise-card ${styles.summaryCard}`}>
          <span className={styles.summaryLabel}>By Status</span>
          {Object.keys(statusCounts).length === 0 ? (
            <span className={styles.summaryValueMuted}>No records</span>
          ) : (
            <div className={styles.categoryChipRow}>
              {Object.entries(statusCounts).map(([status, count]) => (
                <span key={status} className={styles.categoryChip}>
                  {status}: {count}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className={`enterprise-card ${styles.summaryCard}`}>
          <span className={styles.summaryLabel}>AI Readiness</span>
          <span className={styles.summaryValueMuted}>Not available</span>
          <span className={styles.summaryHint}>No backend field configured for this property yet</span>
        </div>
      </div>

      {/* Upload Dropzone */}
      <EnterpriseCard title="Upload Images" id="property-images-upload-card">
        <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <FormField label="Category for new uploads" id="upload-category-field">
              <select
                className="enterprise-form-input"
                value={uploadCategory}
                onChange={(e) => setUploadCategory(e.target.value)}
                id="upload-category-select"
              >
                {IMAGE_CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </FormField>
          </div>

          <div
            className={`${styles.dropzone} ${isDropzoneActive ? styles.dropzoneActive : ''}`}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDropzoneActive(true);
            }}
            onDragLeave={() => setIsDropzoneActive(false)}
            onDrop={handleDrop}
            id="property-images-dropzone"
          >
            <div className={styles.dropzoneIcon}>
              <Upload className="w-5 h-5" />
            </div>
            <span className={styles.dropzoneTitle}>Drag & drop images here, or click to browse</span>
            <span className={styles.dropzoneSubtitle}>JPG, JPEG, PNG, WEBP - multiple files supported</span>
            <input
              ref={fileInputRef}
              type="file"
              accept=".jpg,.jpeg,.png,.webp"
              multiple
              className={styles.dropzoneInput}
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
        </div>
      </EnterpriseCard>

      {/* Toolbar */}
      <EnterpriseToolbar
        id="property-images-toolbar"
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        searchPlaceholder="Search by file name, category, provider..."
        filterContent={
          <select
            className="enterprise-form-input"
            value={imageTypeFilter}
            onChange={(e) => setImageTypeFilter(e.target.value)}
            id="property-images-category-filter"
          >
            <option value="">All Categories</option>
            {IMAGE_CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>
        }
        actionContent={
          <div className={styles.toolbarActions}>
            <div className={styles.viewToggle}>
              <button
                type="button"
                className={`${styles.viewToggleBtn} ${
                  viewMode === 'gallery' ? styles.viewToggleBtnActive : ''
                }`}
                onClick={() => setViewMode('gallery')}
                title="Gallery view"
                id="property-images-view-gallery-btn"
              >
                <LayoutGrid className="w-4 h-4" />
              </button>
              <button
                type="button"
                className={`${styles.viewToggleBtn} ${
                  viewMode === 'list' ? styles.viewToggleBtnActive : ''
                }`}
                onClick={() => setViewMode('list')}
                title="List view"
                id="property-images-view-list-btn"
              >
                <Rows3 className="w-4 h-4" />
              </button>
            </div>
          </div>
        }
      />

      {/* Bulk action bar */}
      {selectedIds.size > 0 && (
        <div className={styles.bulkBar} id="property-images-bulk-bar">
          <span className={styles.bulkBarLabel}>
            {selectedIds.size} image{selectedIds.size === 1 ? '' : 's'} selected
          </span>
          <div className={styles.bulkBarActions}>
            <button type="button" className={styles.bulkBtn} onClick={clearSelection}>
              Clear
            </button>
            <button
              type="button"
              className={`${styles.bulkBtn} ${styles.bulkBtnDanger}`}
              onClick={() => setConfirmBulkDelete(true)}
            >
              <Trash2 className="w-3.5 h-3.5" style={{ marginRight: '0.25rem' }} />
              Delete Selected
            </button>
          </div>
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <LoadingState message="Loading property images..." type="skeleton" />
      ) : filteredImages.length === 0 ? (
        <EmptyState
          title="No Images Available"
          description={
            selectedPropertyId
              ? 'This property has no image records yet. Upload images to get started.'
              : 'Select a Project and Property to view or upload images.'
          }
          icon={ImageIcon}
          actionLabel="Upload Images"
          onAction={() => fileInputRef.current?.click()}
        />
      ) : viewMode === 'gallery' ? (
        <div className={styles.galleryGrid} id="property-images-gallery">
          {filteredImages.map((img) => (
            <div
              key={img.id}
              className={`${styles.imageCard} enterprise-card ${
                selectedIds.has(img.id) ? styles.imageCardSelected : ''
              }`}
              onClick={() => openDetail(img)}
            >
              <div className={styles.thumbWrap}>
                <input
                  type="checkbox"
                  className={styles.thumbCheckbox}
                  checked={selectedIds.has(img.id)}
                  onClick={(e) => e.stopPropagation()}
                  onChange={() => toggleSelect(img.id)}
                />
                {resolveSrc(img) ? (
                  <img src={resolveSrc(img)} alt={displayFileName(img)} className={styles.thumbImg} />
                ) : (
                  <div className={styles.thumbImg} />
                )}
                <div className={styles.thumbFooterOverlay}>
                  <span className={styles.thumbCategory}>{categoryLabel(img.image_type)}</span>
                </div>
              </div>
              <div className={styles.cardBody}>
                <div className={styles.cardTitleRow}>
                  <span className={styles.cardFileName}>{displayFileName(img)}</span>
                  <StatusBadge status={img.status} type="property" />
                </div>
                <div className={styles.cardMetaRow}>
                  <span>{formatDate(img.created_at)}</span>
                  <span>{formatBytes(img.file_size)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className={`${styles.galleryList} enterprise-card`} id="property-images-list">
          {filteredImages.map((img) => (
            <div
              key={img.id}
              className={`${styles.listRow} ${selectedIds.has(img.id) ? styles.listRowSelected : ''}`}
              onClick={() => openDetail(img)}
            >
              <input
                type="checkbox"
                checked={selectedIds.has(img.id)}
                onClick={(e) => e.stopPropagation()}
                onChange={() => toggleSelect(img.id)}
              />
              {resolveSrc(img) ? (
                <img src={resolveSrc(img)} alt={displayFileName(img)} className={styles.listThumb} />
              ) : (
                <div className={styles.listThumb} />
              )}
              <div className={styles.listBody}>
                <span className={styles.listFileName}>{displayFileName(img)}</span>
                <span className={styles.listMeta}>{categoryLabel(img.image_type)}</span>
                <span className={styles.listMeta}>{formatDate(img.created_at)}</span>
                <span className={styles.listMeta}>{formatBytes(img.file_size)}</span>
                <StatusBadge status={img.status} type="property" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Detail Panel */}
      {detailImage && (
        <div className={styles.detailOverlay} onClick={closeDetail} id="property-images-detail-overlay">
          <div className={styles.detailPanel} onClick={(e) => e.stopPropagation()}>
            <div className={styles.detailHeader}>
              <span className={styles.detailHeaderTitle}>{displayFileName(detailImage)}</span>
              <button type="button" className={styles.detailCloseBtn} onClick={closeDetail}>
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className={styles.detailScroll}>
              <div className={styles.detailPreview}>
                {resolveSrc(detailImage) ? (
                  <img
                    src={resolveSrc(detailImage)}
                    alt={displayFileName(detailImage)}
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
                    <span className={styles.metaLabel}>File Size</span>
                    <span className={styles.metaValue}>{formatBytes(detailImage.file_size)}</span>
                  </div>
                  <div className={styles.metaItem}>
                    <span className={styles.metaLabel}>File Type</span>
                    <span className={styles.metaValue}>{detailImage.file_type || '—'}</span>
                  </div>
                  <div className={styles.metaItem}>
                    <span className={styles.metaLabel}>Uploaded</span>
                    <span className={styles.metaValue}>{formatDate(detailImage.created_at)}</span>
                  </div>
                  <div className={styles.metaItem}>
                    <span className={styles.metaLabel}>Property</span>
                    <span className={styles.metaValue}>
                      {selectedProperty?.address || selectedProperty?.property_uid || '—'}
                    </span>
                  </div>
                  {(detailImage.heading !== undefined || detailImage.pitch !== undefined) && (
                    <>
                      <div className={styles.metaItem}>
                        <span className={styles.metaLabel}>Heading</span>
                        <span className={styles.metaValue}>
                          {detailImage.heading !== undefined ? `${detailImage.heading}°` : '—'}
                        </span>
                      </div>
                      <div className={styles.metaItem}>
                        <span className={styles.metaLabel}>Pitch</span>
                        <span className={styles.metaValue}>
                          {detailImage.pitch !== undefined ? `${detailImage.pitch}°` : '—'}
                        </span>
                      </div>
                    </>
                  )}
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
                <FormField label="Image Role" id="detail-image-role-field">
                  <input
                    type="text"
                    className="enterprise-form-input"
                    value={detailDraft.image_role}
                    onChange={(e) => setDetailDraft((prev) => ({ ...prev, image_role: e.target.value }))}
                    placeholder="e.g. Primary front entrance elevation"
                  />
                </FormField>
                <FormField label="Status" id="detail-status-field">
                  <input
                    type="text"
                    className="enterprise-form-input"
                    value={detailDraft.status}
                    onChange={(e) => setDetailDraft((prev) => ({ ...prev, status: e.target.value }))}
                    placeholder="e.g. Active"
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
                disabled={isSavingDetail}
              >
                {isSavingDetail ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirm dialogs */}
      <ConfirmDialog
        isOpen={confirmSingleDeleteId !== null}
        title="Remove Image"
        message="Are you sure you want to remove this image record? This action cannot be undone."
        confirmLabel="Remove"
        isDanger
        onConfirm={handleConfirmSingleDelete}
        onCancel={() => setConfirmSingleDeleteId(null)}
      />
      <ConfirmDialog
        isOpen={confirmBulkDelete}
        title="Remove Selected Images"
        message={`Are you sure you want to remove ${selectedIds.size} image${
          selectedIds.size === 1 ? '' : 's'
        }? This action cannot be undone.`}
        confirmLabel="Remove All"
        isDanger
        onConfirm={handleConfirmBulkDelete}
        onCancel={() => setConfirmBulkDelete(false)}
      />
    </div>
  );
}
