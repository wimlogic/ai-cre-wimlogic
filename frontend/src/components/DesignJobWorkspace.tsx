import { useCallback, useEffect, useMemo, useState } from 'react';
import { X } from 'lucide-react';
import { propertyImageService } from '../services/propertyImageService';
import { designImageVersionService } from '../services/designImageVersionService';
import { designToolService } from '../services/designToolService';
import { designJobService } from '../services/designJobService';
import { PropertyImage, DesignImageVersion, DesignTool, DesignToolOption, DesignToolImageRequirement } from '../types/index';
import ImageLibraryPanel from './ImageLibraryPanel';
import WorkspacePreview, { WorkspaceAsset } from './WorkspacePreview';
import DesignJobPanel from './DesignJobPanel';
import LoadingState from './LoadingState';
import useToast from '../hooks/useToast';
import styles from './DesignJobWorkspace.module.css';

export interface DesignJobWorkspaceProps {
  isOpen: boolean;
  onClose: () => void;
  propertyId: number;
  /** Resolved once by the parent (Home Studio already does this for its
   * own upload flow) - passed in rather than re-resolved here, since the
   * parent already holds this value for the same Property. */
  projectId: string | null;
  /** "Use as Reference" - opens the workspace with this AI version
   * already checked, so the user never has to manually find and
   * reselect it. */
  preselectedVersionId?: number | null;
  /** Called after a Design Job is successfully submitted, so the parent
   * can refresh its own AI Generated list. */
  /** AIHOME Design Studio V2 - Design Job User Experience. Replaces the
   * previous onSubmitted/onClose-only behavior: the parent now
   * transitions to the Design Job Progress screen instead of just
   * closing the modal, per the approved new UX flow. */
  onGenerated?: (info: { designJobId: number; executionId: number; toolName: string }) => void;
}

/**
 * components/DesignJobWorkspace.tsx
 *
 * AIHOME Design Studio V2 - Image Workspace Evolution. The Design Job
 * Workspace: browse Original Photos and AI Generated Images side by
 * side, select any combination of both, write a brand-new instruction,
 * pick a Design Tool, and submit - create -> configure images ->
 * configure instruction -> submit, using the existing Design Job
 * lifecycle service (designJobService.ts), previously built but never
 * wired into any real page until now.
 *
 * Every AI-generated image is treated as a permanent Design Asset, not
 * a transient workflow output - selecting one here as a reference for a
 * NEW job is architecturally identical to selecting an original photo;
 * this component (and the backend it calls) never treats the two
 * differently except for which id field gets populated.
 *
 * Structured for future extension without redesign: ImageLibraryPanel's
 * groups can gain filtering; WorkspacePreview's asset union is what a
 * future Before/After comparison view would consume; DesignJobPanel's
 * sections can grow additional fields. None of that is built here, per
 * the approved scope - only the architecture is shaped to allow it.
 */
export default function DesignJobWorkspace({
  isOpen,
  onClose,
  propertyId,
  projectId,
  preselectedVersionId,
  onGenerated,
}: DesignJobWorkspaceProps) {
  const { error: toastError } = useToast();

  const [originalImages, setOriginalImages] = useState<PropertyImage[]>([]);
  const [aiVersions, setAiVersions] = useState<DesignImageVersion[]>([]);
  const [tools, setTools] = useState<DesignTool[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const [selectedOriginalIds, setSelectedOriginalIds] = useState<Set<number>>(new Set());
  const [selectedVersionIds, setSelectedVersionIds] = useState<Set<number>>(new Set());
  const [hoveredAsset, setHoveredAsset] = useState<WorkspaceAsset | null>(null);
  const [activeAsset, setActiveAsset] = useState<WorkspaceAsset | null>(null);

  const [instruction, setInstruction] = useState('');
  const [selectedToolId, setSelectedToolId] = useState<number | null>(null);
  // The selected Tool's OWN configurable options (e.g. paint palette,
  // aspect ratio) - fetched fresh whenever the Tool changes. Sending an
  // empty tool_options={} unconditionally (the prior behavior) fails
  // submission with DesignJobValidationError for any Tool that has a
  // required option with no default_value - confirmed as the likely
  // cause of Generate silently doing nothing.
  const [toolOptions, setToolOptions] = useState<DesignToolOption[]>([]);
  const [toolOptionValues, setToolOptionValues] = useState<Record<string, any>>({});
  // The selected Tool's Image Requirements (e.g. 'primary' max 1,
  // 'reference' max 3) - fetched alongside options. Previously unused
  // anywhere in the workspace; every selected image was hardcoded to
  // input_role='primary' regardless of count, which fails submission
  // for any Tool whose 'primary' requirement has max_count=1 the moment
  // more than one image is selected - confirmed as a real, reproducible
  // failure ("Tool allows at most 1 image(s) with input_role 'primary';
  // 2 selected").
  const [imageRequirements, setImageRequirements] = useState<DesignToolImageRequirement[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadWorkspaceData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [imagesRes, versionsRes, toolsRes] = await Promise.all([
        propertyImageService.list({ property_id: propertyId, include_deleted: false, limit: 200 }),
        designImageVersionService.listForProperty(propertyId),
        designToolService.list({ status: 'active', limit: 100 }),
      ]);
      setOriginalImages(imagesRes.items || []);
      setAiVersions(versionsRes.items || []);
      // GENERIC_ARTIFACT_IMPORT is the internal implicit Tool
      // auto-provisioned by ensure_import_design_job() for images
      // imported outside the Design Studio flow (RC1) - it was never
      // meant to be user-selectable and was confirmed leaking into this
      // dropdown.
      setTools((toolsRes.items || []).filter((t) => t.tool_code !== 'GENERIC_ARTIFACT_IMPORT'));
    } catch (err) {
      console.error('[Design Job Workspace] Failed to load workspace data:', err);
      toastError('Unable to load images for this Property.');
    } finally {
      setIsLoading(false);
    }
  }, [propertyId, toastError]);

  // Reset to a clean workspace every time it opens - a brand-new
  // instruction and selection every session, never carried over from a
  // previous one, except for an explicit "Use as Reference" preselection.
  useEffect(() => {
    if (!isOpen) return;
    setSelectedOriginalIds(new Set());
    setSelectedVersionIds(preselectedVersionId ? new Set([preselectedVersionId]) : new Set());
    setInstruction('');
    setSelectedToolId(null);
    setActiveAsset(null);
    setHoveredAsset(null);
    loadWorkspaceData();
  }, [isOpen, preselectedVersionId, loadWorkspaceData]);

  // Fetch the selected Tool's own configurable options whenever it
  // changes, and seed defaults for any active option that has one - the
  // same default resolution the backend would otherwise apply silently
  // at submit time, done here so the user can actually see and adjust
  // them before Generate, rather than have invisible values applied.
  useEffect(() => {
    if (selectedToolId === null) {
      setToolOptions([]);
      setToolOptionValues({});
      setImageRequirements([]);
      return;
    }
    let cancelled = false;
    designToolService
      .getOptions(selectedToolId)
      .then((res) => {
        if (cancelled) return;
        // These endpoints return a PLAIN ARRAY (response_model=List[...]),
        // not a {items, count} envelope - handled defensively so this
        // works either way, but the array form is what the backend
        // actually sends today. The prior `res.items || []` silently
        // produced an empty list on every call.
        const all = Array.isArray(res) ? res : (res as any)?.items || [];
        const active = all.filter((opt: DesignToolOption) => opt.status === 'active');
        setToolOptions(active);
        const seeded: Record<string, any> = {};
        for (const opt of active) {
          if (opt.default_value !== null && opt.default_value !== undefined) {
            if (opt.option_type === 'boolean') seeded[opt.option_code] = opt.default_value === 'true';
            else if (opt.option_type === 'number') seeded[opt.option_code] = Number(opt.default_value);
            else seeded[opt.option_code] = opt.default_value;
          }
        }
        setToolOptionValues(seeded);
      })
      .catch((err) => {
        console.error('[Design Job Workspace] Failed to load Tool Options:', err);
        if (!cancelled) { setToolOptions([]); setToolOptionValues({}); }
      });
    designToolService
      .getImageRequirements(selectedToolId)
      .then((res) => {
        if (cancelled) return;
        const all = Array.isArray(res) ? res : (res as any)?.items || [];
        setImageRequirements(all.slice().sort(
          (a: DesignToolImageRequirement, b: DesignToolImageRequirement) => a.display_order - b.display_order
        ));
      })
      .catch((err) => {
        console.error('[Design Job Workspace] Failed to load Image Requirements:', err);
        if (!cancelled) setImageRequirements([]);
      });
    return () => { cancelled = true; };
  }, [selectedToolId]);

  const handleToolOptionChange = (optionCode: string, value: any) => {
    setToolOptionValues((prev) => ({ ...prev, [optionCode]: value }));
  };

  const toggleOriginal = (id: number) => {
    setSelectedOriginalIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleVersion = (id: number) => {
    setSelectedVersionIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectedAssets: WorkspaceAsset[] = useMemo(() => {
    const originals: WorkspaceAsset[] = originalImages
      .filter((img) => selectedOriginalIds.has(img.id))
      .map((image) => ({ kind: 'original' as const, id: image.id, image }));
    const versions: WorkspaceAsset[] = aiVersions
      .filter((v) => selectedVersionIds.has(v.id))
      .map((version) => ({ kind: 'version' as const, id: version.id, version }));
    return [...originals, ...versions];
  }, [originalImages, aiVersions, selectedOriginalIds, selectedVersionIds]);

  // Distributes selected images across the Tool's actual Image
  // Requirements (by display_order, respecting each requirement's
  // min_count/max_count) rather than hardcoding every image to
  // input_role='primary' - confirmed as the real cause of "Tool allows
  // at most 1 image(s) with input_role 'primary'; 2 selected" for any
  // multi-image selection. Falls back to 'primary' for everyone only
  // when the Tool has no requirements configured at all (preserves the
  // old single-image behavior for such Tools). Returns a clear,
  // pre-submit error rather than letting an invalid combination reach
  // the backend and fail there instead.
  const imageRoleAssignment = useMemo((): { roles: Map<string, string> | null; error: string | null } => {
    const assetKey = (a: WorkspaceAsset) => `${a.kind}-${a.id}`;
    if (selectedAssets.length === 0) return { roles: new Map(), error: null };
    if (imageRequirements.length === 0) {
      const roles = new Map<string, string>();
      for (const a of selectedAssets) roles.set(assetKey(a), 'primary');
      return { roles, error: null };
    }
    const counts: Record<string, number> = {};
    const roles = new Map<string, string>();
    for (const asset of selectedAssets) {
      let placed = false;
      for (const req of imageRequirements) {
        const current = counts[req.input_role] || 0;
        const hasCapacity = req.max_count == null || current < req.max_count;
        if (!hasCapacity) continue;
        // AIHOME Design Studio V2 - checked here, not just at capacity:
        // an original photo's OWN image_role must be in the
        // requirement's allowed_image_roles_json when that list is set
        // (mirrors _validate_image_requirements() server-side exactly -
        // confirmed as the real, correct rejection reason for
        // "Property Image 56 has image_role 'detail'... not in
        // ['primary', 'exterior']"). Checked client-side, using data
        // already on hand (PropertyImage.image_role), so the user finds
        // out BEFORE a round trip to the backend, not after.
        if (asset.kind === 'original' && req.allowed_image_roles_json && req.allowed_image_roles_json.length > 0) {
          const photoRole = asset.image.image_role;
          if (!photoRole || !req.allowed_image_roles_json.includes(photoRole)) continue;
        }
        roles.set(assetKey(asset), req.input_role);
        counts[req.input_role] = current + 1;
        placed = true;
        break;
      }
      if (!placed) {
        if (asset.kind === 'original') {
          const photoRole = asset.image.image_role || 'unspecified';
          const compatibleRoles = Array.from(new Set(
            imageRequirements.flatMap((r) => r.allowed_image_roles_json || [])
          ));
          return {
            roles: null,
            error: compatibleRoles.length > 0
              ? `This photo's type ("${photoRole}") isn't accepted by this Tool - it needs: ${compatibleRoles.join(', ')}.`
              : `This Tool cannot accept the selected image(s) - no room left for another image.`,
          };
        }
        const totalCapacity = imageRequirements.reduce((sum, r) => sum + (r.max_count ?? Infinity), 0);
        return {
          roles: null,
          error: totalCapacity === Infinity
            ? 'This Tool could not accept all selected images.'
            : `This Tool accepts at most ${totalCapacity} image(s) total; ${selectedAssets.length} selected.`,
        };
      }
    }
    for (const req of imageRequirements) {
      const have = counts[req.input_role] || 0;
      if (have < req.min_count) {
        return {
          roles: null,
          error: `This Tool requires at least ${req.min_count} image(s) for '${req.input_role}'; ${have} selected.`,
        };
      }
    }
    return { roles, error: null };
  }, [selectedAssets, imageRequirements]);

  const handleHoverOriginal = (id: number | null) => {
    if (id === null) { setHoveredAsset(null); return; }
    const image = originalImages.find((img) => img.id === id);
    if (image) setHoveredAsset({ kind: 'original', id, image });
  };

  const handleHoverVersion = (id: number | null) => {
    if (id === null) { setHoveredAsset(null); return; }
    const version = aiVersions.find((v) => v.id === id);
    if (version) setHoveredAsset({ kind: 'version', id, version });
  };

  const handleGenerate = async () => {
    if (!projectId) {
      toastError('This Property has no associated Project yet - cannot submit a Design Job.');
      return;
    }
    if (selectedToolId === null) return;
    if (imageRoleAssignment.roles === null) {
      toastError(imageRoleAssignment.error || 'Selected images do not match this Tool\'s requirements.');
      return;
    }

    setIsSubmitting(true);
    try {
      const job = await designJobService.create({ project_id: projectId, property_id: propertyId, tool_id: selectedToolId });

      const roles = imageRoleAssignment.roles!;
      const imagePayload = [
        ...Array.from(selectedOriginalIds).map((id) => ({ property_image_id: id, input_role: roles.get(`original-${id}`) || 'primary' })),
        ...Array.from(selectedVersionIds).map((id) => ({ source_image_version_id: id, input_role: roles.get(`version-${id}`) || 'primary' })),
      ];
      await designJobService.setImages(job.id, imagePayload);
      await designJobService.setOptions(job.id, toolOptionValues, instruction.trim());
      // submit() only validates and freezes the payload (draft ->
      // submitted) - it explicitly does NOT call WACP, per the backend's
      // own router docstring. execute() is the separate, required call
      // that actually creates the Workflow Execution and dispatches the
      // frozen payload to DEV-TOOLS. Without this second call, a
      // "submitted" job would sit untouched forever - confirmed as a
      // real gap in this exact function before this fix.
      await designJobService.submit(job.id);
      const attempt = await designJobService.execute(job.id);

      const toolName = tools.find((t) => t.id === selectedToolId)?.tool_name || 'Design Job';
      onGenerated?.({ designJobId: job.id, executionId: attempt.workflow_execution_id, toolName });
      onClose();
    } catch (err) {
      console.error('[Design Job Workspace] Failed to submit Design Job:', err);
      toastError('Failed to submit the Design Job. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="enterprise-dialog-overlay" onClick={onClose} id="design-job-workspace-overlay">
      <div className={`enterprise-dialog-panel ${styles.workspacePanel}`} onClick={(e) => e.stopPropagation()}>
        <div className="enterprise-dialog-header">
          <div>
            <div className="enterprise-dialog-title">Design Job Workspace</div>
            <div className="enterprise-dialog-subtitle">Select images, write a new instruction, and generate.</div>
          </div>
          <button type="button" className={styles.closeBtn} onClick={onClose} aria-label="Close" id="design-job-workspace-close-btn">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="enterprise-dialog-body" style={{ padding: 0, overflow: 'hidden', flex: '1 1 auto', display: 'flex' }}>
          {isLoading ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <LoadingState message="Loading workspace..." type="skeleton" />
            </div>
          ) : (
            <div className={styles.workspaceBody}>
              <div className={styles.libraryColumn}>
                <ImageLibraryPanel
                  originalImages={originalImages}
                  aiVersions={aiVersions}
                  selectedOriginalIds={selectedOriginalIds}
                  selectedVersionIds={selectedVersionIds}
                  onToggleOriginal={toggleOriginal}
                  onToggleVersion={toggleVersion}
                  onHoverOriginal={handleHoverOriginal}
                  onHoverVersion={handleHoverVersion}
                />
              </div>
              <div className={styles.previewColumn}>
                <WorkspacePreview
                  selectedAssets={selectedAssets}
                  activeAsset={hoveredAsset ?? activeAsset}
                  onSetActive={setActiveAsset}
                />
              </div>
              <div className={styles.jobColumn}>
                <DesignJobPanel
                  selectedOriginalCount={selectedOriginalIds.size}
                  selectedVersionCount={selectedVersionIds.size}
                  instruction={instruction}
                  onInstructionChange={setInstruction}
                  tools={tools}
                  selectedToolId={selectedToolId}
                  onSelectTool={setSelectedToolId}
                  toolOptions={toolOptions}
                  toolOptionValues={toolOptionValues}
                  onToolOptionChange={handleToolOptionChange}
                  imageRoleError={imageRoleAssignment.error}
                  onGenerate={handleGenerate}
                  isSubmitting={isSubmitting}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
