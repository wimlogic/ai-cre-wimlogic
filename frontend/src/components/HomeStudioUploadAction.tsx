import { useRef, useState } from 'react';
import { Upload, X } from 'lucide-react';
import { propertyImageService } from '../services/propertyImageService';
import { PropertyImage } from '../types/index';
import styles from './HomeStudioUploadAction.module.css';

export interface HomeStudioUploadActionProps {
  propertyId: number;
  /**
   * The business project code (cre_projects.project_id) this Property is
   * associated with - REQUIRED by the existing upload endpoint's
   * contract (a separate business entity from the Property itself, per
   * cre_project_properties). Home Studio's own flow selects a Property
   * directly, not a Project, so HomeStudio.tsx resolves this once via
   * propertyService.listAssociations({ property_id }) when a Property is
   * selected - see the "no association" state below for what happens
   * when a Property has none.
   */
  resolvedProjectId: string | null;
  onUploaded: (newImages: PropertyImage[]) => void;
  onError: (message: string) => void;
  id?: string;
}

interface UploadQueueItem {
  key: string;
  fileName: string;
  progress: number;
  status: 'uploading' | 'done' | 'error';
  errorMessage?: string;
}

/**
 * components/HomeStudioUploadAction.tsx
 *
 * Home Studio Frontend Checkpoint 2. Reuses the exact per-file upload
 * loop already proven in PropertyImages.tsx - propertyImageService's
 * single-file uploadWithProgress(), called once per selected file. No
 * second upload client, no assumed /upload/batch endpoint (unverified
 * against the actual backend, not wrapped anywhere in this codebase
 * today).
 */
export default function HomeStudioUploadAction({
  propertyId,
  resolvedProjectId,
  onUploaded,
  onError,
  id,
}: HomeStudioUploadActionProps) {
  const [queue, setQueue] = useState<UploadQueueItem[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFiles = (files: FileList) => {
    if (!resolvedProjectId) {
      onError('This Property is not yet linked to a Project, so photos cannot be uploaded here yet.');
      return;
    }

    Array.from(files).forEach((file) => {
      const key = `${file.name}-${file.size}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

      setQueue((prev) => [...prev, { key, fileName: file.name, progress: 0, status: 'uploading' }]);

      const { promise } = propertyImageService.uploadWithProgress(
        {
          file,
          property_id: propertyId,
          project_id: resolvedProjectId,
          image_type: 'uploaded',
        },
        (percent) => {
          setQueue((prev) => prev.map((item) => (item.key === key ? { ...item, progress: percent } : item)));
        }
      );

      promise
        .then((newImage) => {
          setQueue((prev) => prev.map((item) => (item.key === key ? { ...item, progress: 100, status: 'done' } : item)));
          onUploaded([newImage]);
          setTimeout(() => {
            setQueue((prev) => prev.filter((item) => item.key !== key));
          }, 2000);
        })
        .catch((err) => {
          setQueue((prev) =>
            prev.map((item) =>
              item.key === key ? { ...item, status: 'error', errorMessage: err?.message || 'Upload failed' } : item
            )
          );
          onError(`Failed to upload ${file.name}.`);
        });
    });
  };

  return (
    <div id={id || 'home-studio-upload-action'}>
      <button
        type="button"
        className="enterprise-btn enterprise-btn-secondary"
        onClick={() => fileInputRef.current?.click()}
        id="home-studio-upload-btn"
        disabled={!resolvedProjectId}
        title={resolvedProjectId ? undefined : 'This Property is not yet linked to a Project'}
      >
        <Upload className="w-3.5 h-3.5" />
        Upload Photos
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
        id="home-studio-file-input"
      />

      {queue.length > 0 && (
        <div className={styles.queue}>
          {queue.map((item) => (
            <div key={item.key} className={styles.queueItem}>
              <span className={styles.queueName}>{item.fileName}</span>
              <div className={styles.progressTrack}>
                <div
                  className={`${styles.progressFill} ${item.status === 'error' ? styles.progressFillError : ''} ${
                    item.status === 'done' ? styles.progressFillDone : ''
                  }`}
                  style={{ width: `${item.progress}%` }}
                />
              </div>
              <span className={styles.queueMeta}>
                {item.status === 'uploading' && `${item.progress}%`}
                {item.status === 'done' && 'Done'}
                {item.status === 'error' && (item.errorMessage || 'Failed')}
              </span>
              <button
                type="button"
                className={styles.dismissBtn}
                onClick={() => setQueue((prev) => prev.filter((q) => q.key !== item.key))}
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
