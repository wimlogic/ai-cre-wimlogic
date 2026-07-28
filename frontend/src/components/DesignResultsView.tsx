import { useEffect, useState } from 'react';
import { CheckCircle2, AlertTriangle, Download, Layers, Wand2 } from 'lucide-react';
import { designJobService } from '../services/designJobService';
import { designImageVersionService, approvedDesignBaselineService } from '../services/designImageVersionService';
import { propertyImageService } from '../services/propertyImageService';
import { DesignImageVersion, PropertyImage } from '../types/index';
import { resolveDesignImageSrc, resolveDesignImageFileName, resolveImageSrc } from '../utils/imageUrl';
import { formatDate } from '../utils/formatters';
import LoadingState from './LoadingState';
import useToast from '../hooks/useToast';
import styles from './DesignResultsView.module.css';

export interface DesignResultsViewProps {
  designJobId: number;
  hadWarnings: boolean;
  onGenerateAnotherVersion: (versionId: number) => void;
  onUseAsReference: (versionId: number) => void;
  onDone: () => void;
  id?: string;
}

/**
 * components/DesignResultsView.tsx
 *
 * AIHOME Design Studio V2 - Design Job User Experience. Shown
 * automatically when DesignJobProgress reports a terminal
 * Completed/Completed with Warnings status. Displays the images THIS
 * specific Design Job produced (via the existing design_job_id filter -
 * no new backend query), a simple before/after against the first
 * original photo this job actually used as input (if any - a job built
 * entirely from prior AI versions has no "original" side, and this view
 * is honest about that rather than fabricating one), and the real
 * actions currently available: Download (real), Approve (reuses the
 * existing approve_design_version baseline promotion), Generate Another
 * Version / Use as Reference (both re-open the Design Job Workspace with
 * this exact image preselected, per the approved iterative-refinement
 * flow). "Add Notes" is not included - DesignImageVersion has no notes
 * field to save one into.
 */
export default function DesignResultsView({
  designJobId,
  hadWarnings,
  onGenerateAnotherVersion,
  onUseAsReference,
  onDone,
  id,
}: DesignResultsViewProps) {
  const { success, error: toastError } = useToast();
  const [versions, setVersions] = useState<DesignImageVersion[]>([]);
  const [originalImage, setOriginalImage] = useState<PropertyImage | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [approvingId, setApprovingId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setIsLoading(true);
      try {
        const [versionsRes, imagesRes] = await Promise.all([
          designImageVersionService.listForDesignJob(designJobId),
          designJobService.getImages(designJobId),
        ]);
        if (cancelled) return;
        setVersions(versionsRes.items || []);

        const firstOriginalRef = imagesRes.find((img) => img.property_image_id != null);
        if (firstOriginalRef?.property_image_id) {
          try {
            const img = await propertyImageService.get(firstOriginalRef.property_image_id);
            if (!cancelled) setOriginalImage(img);
          } catch {
            // A resolvable original just isn't available to show - the
            // AI results themselves are still shown regardless.
          }
        }
      } catch (err) {
        console.error('[Design Results] Failed to load results:', err);
        toastError('Unable to load the results for this Design Job.');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [designJobId, toastError]);

  const handleApprove = async (versionId: number) => {
    setApprovingId(versionId);
    try {
      await approvedDesignBaselineService.approve(versionId);
      success('Design approved.');
      setVersions((prev) => prev.map((v) => (v.id === versionId ? { ...v, status: 'approved' } : v)));
    } catch (err) {
      console.error('[Design Results] Failed to approve version:', err);
      toastError('Failed to approve this design.');
    } finally {
      setApprovingId(null);
    }
  };

  if (isLoading) {
    return (
      <div className={styles.wrapper} id={id || 'design-results-view'}>
        <LoadingState message="Loading results..." type="skeleton" />
      </div>
    );
  }

  return (
    <div className={styles.wrapper} id={id || 'design-results-view'}>
      <div className={styles.header}>
        {hadWarnings ? (
          <div className={styles.warningBanner}>
            <AlertTriangle className="w-4 h-4" />
            <span>Design Complete - review recommended before approving.</span>
          </div>
        ) : (
          <div className={styles.successBanner}>
            <CheckCircle2 className="w-4 h-4" />
            <span>Design Complete</span>
          </div>
        )}
      </div>

      {versions.length === 0 ? (
        <p className={styles.emptyText}>No images were produced by this Design Job.</p>
      ) : (
        <div className={styles.resultsGrid}>
          {versions.map((version) => {
            const isUnapproved = version.quality_approved === false;
            return (
              <div key={version.id} className={styles.resultCard}>
                <div className={styles.compareRow}>
                  {originalImage && (
                    <div className={styles.compareSide}>
                      <span className={styles.compareLabel}>Original</span>
                      <img src={resolveImageSrc(originalImage)} alt="Original" className={styles.compareImage} />
                    </div>
                  )}
                  <div className={styles.compareSide}>
                    <span className={styles.compareLabel}>AI Generated</span>
                    <img src={resolveDesignImageSrc(version)} alt="AI Generated" className={styles.compareImage} />
                  </div>
                </div>

                <div className={styles.metaRow}>
                  <span className={styles.metaChip}>Version {version.version_number}</span>
                  <span className={styles.metaChip}>{formatDate(version.generated_at)}</span>
                  {version.status === 'approved' && <span className={styles.approvedChip}>Approved</span>}
                </div>

                {isUnapproved && (
                  <p className={styles.qualityWarning}>
                    <AlertTriangle className="w-3.5 h-3.5" />
                    DEV-TOOLS quality review did not approve this image.
                  </p>
                )}

                <div className={styles.actions}>
                  <a
                    className="enterprise-btn enterprise-btn-ghost"
                    href={resolveDesignImageSrc(version)}
                    download={resolveDesignImageFileName(version)}
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download
                  </a>
                  <button
                    type="button"
                    className="enterprise-btn enterprise-btn-ghost"
                    onClick={() => handleApprove(version.id)}
                    disabled={version.status === 'approved' || approvingId === version.id}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    {version.status === 'approved' ? 'Approved' : approvingId === version.id ? 'Approving...' : 'Approve'}
                  </button>
                  <button
                    type="button"
                    className="enterprise-btn enterprise-btn-primary"
                    onClick={() => onGenerateAnotherVersion(version.id)}
                  >
                    <Wand2 className="w-3.5 h-3.5" />
                    Generate Another Version
                  </button>
                  <button type="button" className="enterprise-btn enterprise-btn-ghost" onClick={() => onUseAsReference(version.id)}>
                    <Layers className="w-3.5 h-3.5" />
                    Use as Reference
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <button type="button" className="enterprise-btn enterprise-btn-ghost" onClick={onDone} id="design-results-done-btn">
        Continue Browsing
      </button>
    </div>
  );
}
