import { useState } from 'react';
import ExpandableSection from './ExpandableSection';
import EnterpriseSelect from './EnterpriseSelect';
import { designImageVersionService, approvedDesignBaselineService } from '../services/designImageVersionService';
import { DesignImageVersion, ApprovedDesignBaseline, PropertyImage } from '../types/index';
import { AppConfig } from '../config/app';
import { Image as ImageIcon, CheckCircle2 } from 'lucide-react';
import styles from './PropertyImageVersionsPanel.module.css';

/**
 * components/PropertyImageVersionsPanel.tsx
 *
 * AIHOME Phase 1 (Phase D). Renders the three new expandable sections
 * (Versions -> Compare -> Approval, in that fixed order) inside the
 * EXISTING Property Image detail modal - the modal itself, and its
 * existing "Details" content, are untouched; this component is the only
 * new addition, inserted once below what already exists.
 *
 * No business logic lives here: version ordering, design_scope
 * derivation, and the approval/supersede transaction are entirely
 * backend responsibilities (design_result_service.py, already tested).
 * This component only fetches, displays, and forwards a user's approve
 * click - it makes no decisions of its own about which version "should"
 * be approved or how versions relate to each other.
 *
 * Data is fetched once, lazily, the first time any of the three
 * sections is expanded (shared across all three - Versions, Compare,
 * and Approval all read the same version list and active baseline, so
 * there is no reason to fetch it more than once).
 */

export interface PropertyImageVersionsPanelProps {
  propertyImage: PropertyImage;
}

function versionLabel(version: DesignImageVersion): string {
  return `v${version.version_number}`;
}

function resolveVersionImageSrc(path?: string): string | null {
  if (!path) return null;
  return `${AppConfig.uploadBaseUrl}/${path}`;
}

export default function PropertyImageVersionsPanel({ propertyImage }: PropertyImageVersionsPanelProps) {
  const [versions, setVersions] = useState<DesignImageVersion[]>([]);
  const [activeBaseline, setActiveBaseline] = useState<ApprovedDesignBaseline | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const [compareLeftId, setCompareLeftId] = useState<string>('original');
  const [compareRightId, setCompareRightId] = useState<string>('');

  const [selectedApprovalId, setSelectedApprovalId] = useState<string>('');
  const [isApproving, setIsApproving] = useState(false);
  const [approveError, setApproveError] = useState('');

  const loadData = async () => {
    if (hasLoaded) return;
    setIsLoading(true);
    setErrorMsg('');
    try {
      const [versionsRes, baselineRes] = await Promise.all([
        designImageVersionService.listForPropertyImage(propertyImage.id),
        approvedDesignBaselineService.listActiveForProperty(propertyImage.property_id),
      ]);
      setVersions(versionsRes.items || []);
      setActiveBaseline(baselineRes.items?.[0] || null);
      setHasLoaded(true);
    } catch (err) {
      console.error('[PropertyImageVersionsPanel] Failed to load versions:', err);
      setErrorMsg('Unable to load version history for this image.');
    } finally {
      setIsLoading(false);
    }
  };

  const reload = async () => {
    setHasLoaded(false);
    await loadData();
  };

  const handleApprove = async () => {
    if (!selectedApprovalId) return;
    setIsApproving(true);
    setApproveError('');
    try {
      await approvedDesignBaselineService.approve(Number(selectedApprovalId));
      await reload();
      setSelectedApprovalId('');
    } catch (err) {
      console.error('[PropertyImageVersionsPanel] Approval failed:', err);
      setApproveError('Could not approve this version. Please try again.');
    } finally {
      setIsApproving(false);
    }
  };

  const versionOptions = [
    { value: 'original', label: 'Original' },
    ...versions.map((v) => ({ value: String(v.id), label: `${versionLabel(v)} (${v.file_name})` })),
  ];

  const originalSrc = propertyImage.image_url || null;
  const compareLeftSrc = compareLeftId === 'original' ? originalSrc : resolveVersionImageSrc(versions.find((v) => String(v.id) === compareLeftId)?.storage_path);
  const compareRightSrc = compareRightId === 'original' ? originalSrc : resolveVersionImageSrc(versions.find((v) => String(v.id) === compareRightId)?.storage_path);

  return (
    <>
      <ExpandableSection title="Versions" onFirstExpand={loadData}>
        {isLoading && <div className={styles.loading}>Loading versions...</div>}
        {errorMsg && <div className={styles.error}>{errorMsg}</div>}
        {!isLoading && !errorMsg && (
          <div className={styles.versionsList}>
            <div className={styles.versionRow}>
              <div className={styles.versionThumb}>
                {originalSrc ? <img src={originalSrc} alt="Original" /> : <ImageIcon className="w-5 h-5" />}
              </div>
              <div className={styles.versionMain}>
                <span className={styles.versionLabel}>Original</span>
              </div>
            </div>

            {versions.length === 0 ? (
              <div className={styles.emptyText}>No generated versions yet for this image.</div>
            ) : (
              versions.map((v) => {
                const isActive = activeBaseline?.image_version_id === v.id;
                const thumbSrc = resolveVersionImageSrc(v.thumbnail_path || v.storage_path);
                return (
                  <div className={styles.versionRow} key={v.id}>
                    <div className={styles.versionThumb}>
                      {thumbSrc ? <img src={thumbSrc} alt={versionLabel(v)} /> : <ImageIcon className="w-5 h-5" />}
                    </div>
                    <div className={styles.versionMain}>
                      <span className={styles.versionLabel}>{versionLabel(v)} - {v.file_name}</span>
                      <span className={styles.versionDate}>{new Date(v.generated_at).toLocaleDateString()}</span>
                    </div>
                    {isActive && (
                      <span className={styles.activeBadge}>
                        <CheckCircle2 className="w-3.5 h-3.5" /> Active Baseline
                      </span>
                    )}
                    {!isActive && v.status === 'superseded' && (
                      <span className={styles.supersededBadge}>Superseded</span>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}
      </ExpandableSection>

      <ExpandableSection title="Compare" onFirstExpand={loadData}>
        {isLoading && <div className={styles.loading}>Loading...</div>}
        {!isLoading && (
          <div className={styles.compareArea}>
            <div className={styles.compareSelectors}>
              <EnterpriseSelect
                id="compare-left-select"
                value={compareLeftId}
                options={versionOptions}
                onChange={setCompareLeftId}
              />
              <span className={styles.vsLabel}>vs</span>
              <EnterpriseSelect
                id="compare-right-select"
                value={compareRightId}
                options={versionOptions}
                placeholder="Select a version"
                onChange={setCompareRightId}
              />
            </div>
            <div className={styles.compareImages}>
              <div className={styles.comparePane}>
                {compareLeftSrc ? <img src={compareLeftSrc} alt="Left comparison" /> : <div className={styles.emptyText}>No image</div>}
              </div>
              <div className={styles.comparePane}>
                {compareRightSrc ? <img src={compareRightSrc} alt="Right comparison" /> : <div className={styles.emptyText}>Select a version above</div>}
              </div>
            </div>
          </div>
        )}
      </ExpandableSection>

      <ExpandableSection title="Approval" onFirstExpand={loadData}>
        {isLoading && <div className={styles.loading}>Loading...</div>}
        {!isLoading && !errorMsg && (
          <div className={styles.approvalArea}>
            <div className={styles.currentBaselineRow}>
              <span className={styles.metaLabel}>Currently Active Baseline</span>
              <span className={styles.metaValue}>
                {activeBaseline
                  ? `${versionLabel(versions.find((v) => v.id === activeBaseline.image_version_id) || versions[0])} (${activeBaseline.design_scope})`
                  : 'None approved yet'}
              </span>
            </div>

            {versions.length === 0 ? (
              <div className={styles.emptyText}>No generated versions available to approve yet.</div>
            ) : (
              <div className={styles.approvalOptions}>
                {versions.map((v) => (
                  <label key={v.id} className={styles.approvalOption}>
                    <input
                      type="radio"
                      name="approval-version"
                      value={v.id}
                      checked={selectedApprovalId === String(v.id)}
                      onChange={() => setSelectedApprovalId(String(v.id))}
                    />
                    <span>{versionLabel(v)} - {v.file_name}</span>
                    {activeBaseline?.image_version_id === v.id && (
                      <span className={styles.activeBadge}>Currently Active</span>
                    )}
                  </label>
                ))}
              </div>
            )}

            {approveError && <div className={styles.error}>{approveError}</div>}

            <button
              type="button"
              className="enterprise-btn enterprise-btn-primary"
              onClick={handleApprove}
              disabled={!selectedApprovalId || isApproving}
            >
              {isApproving ? 'Approving...' : 'Approve Selected Version'}
            </button>
            <p className={styles.helpText}>
              Approving replaces the current active baseline. Prior baselines remain visible in
              Versions, marked Superseded.
            </p>
          </div>
        )}
      </ExpandableSection>
    </>
  );
}
