import { apiClient } from './apiClient';
import { DesignImageVersion, ApprovedDesignBaseline, ListResponse } from '../types/index';

/**
 * services/designImageVersionService.ts
 *
 * AIHOME Phase 1 (Phase D). Thin HTTP layer only - every business rule
 * (version numbering, lineage, design_scope derivation, the baseline
 * supersede transaction) lives entirely in the backend
 * (design_result_service.py, already tested). This file makes no
 * decisions of its own; it only shapes requests and returns responses.
 */
export const designImageVersionService = {
  /** Every generated version whose lineage traces back to this Property Image. */
  /** Every version produced by one specific Design Job - used by the
   * Design Job Progress/Results flow to show exactly what this
   * submission generated, not the Property's full AI Generated history. */
  async listForDesignJob(designJobId: number): Promise<ListResponse<DesignImageVersion>> {
    return apiClient.get<ListResponse<DesignImageVersion>>(
      `/design-studio/image-versions/?design_job_id=${designJobId}`
    );
  },

  /** Every generated version for this Property, regardless of which
   * Property Image (if any) it traces back to - Home Studio's "AI
   * Generated" tab. Uses the property_id CRUD filter directly (not the
   * lineage lookup below), so this also includes versions imported from
   * a DEV-TOOLS IMAGE_DESIGN result outside the Design Studio flow. */
  async listForProperty(propertyId: number): Promise<ListResponse<DesignImageVersion>> {
    return apiClient.get<ListResponse<DesignImageVersion>>(
      `/design-studio/image-versions/?property_id=${propertyId}&limit=200`
    );
  },

  async listForWorkflowExecution(workflowExecutionId: number): Promise<ListResponse<DesignImageVersion>> {
    return apiClient.get<ListResponse<DesignImageVersion>>(
      `/design-studio/image-versions/?workflow_execution_id=${workflowExecutionId}&limit=200`
    );
  },

  async listForPropertyImage(propertyImageId: number): Promise<ListResponse<DesignImageVersion>> {
    return apiClient.get<ListResponse<DesignImageVersion>>(
      `/design-studio/image-versions/?property_image_id=${propertyImageId}`
    );
  },

  async get(versionId: number): Promise<DesignImageVersion> {
    return apiClient.get<DesignImageVersion>(`/design-studio/image-versions/${versionId}`);
  },
};

export const approvedDesignBaselineService = {
  /** The currently active baseline(s) for a property - normally exactly
   * one, or zero if nothing has been approved yet. */
  async listActiveForProperty(propertyId: number): Promise<ListResponse<ApprovedDesignBaseline>> {
    return apiClient.get<ListResponse<ApprovedDesignBaseline>>(
      `/design-studio/baselines/?property_id=${propertyId}&status=active`
    );
  },

  /** Promotes a version to the active baseline for its scope. design_scope
   * is intentionally not sent - the backend derives it (documented
   * temporary Phase 1 behavior on the request schema itself). */
  async approve(imageVersionId: number): Promise<ApprovedDesignBaseline> {
    return apiClient.post<ApprovedDesignBaseline>('/design-studio/baselines/approve', {
      image_version_id: imageVersionId,
    });
  },
};
