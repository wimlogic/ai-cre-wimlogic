import { apiClient } from './apiClient';
import { DesignTool, DesignToolOption, DesignToolImageRequirement, ListResponse } from '../types/index';

/**
 * services/designToolService.ts
 *
 * Read-only Tool Box access (Home Studio Frontend Checkpoint 1). Mirrors
 * propertyImageService.ts's plain apiClient-based pattern. Home Studio
 * never hardcodes Tool controls - every option and image requirement
 * shown to the user comes from these calls, driven by whichever Tool the
 * user selects.
 *
 * getKnowledgeRules() is intentionally NOT included here yet - Tool
 * Knowledge Rules affect Effective AI Context assembly on the backend,
 * but Home Studio has no UI surface that needs to read them directly at
 * this checkpoint. Add it only once a concrete UI need and its validated
 * type exist together, per the approved correction.
 */
export const designToolService = {
  async list(params?: { status?: string; skip?: number; limit?: number }): Promise<ListResponse<DesignTool>> {
    const query = new URLSearchParams();
    if (params?.status) query.append('status', params.status);
    if (params?.skip !== undefined) query.append('skip', String(params.skip));
    if (params?.limit !== undefined) query.append('limit', String(params.limit));

    const queryString = query.toString();
    const endpoint = queryString ? `/design-studio/tools/?${queryString}` : '/design-studio/tools/';
    return apiClient.get<ListResponse<DesignTool>>(endpoint);
  },

  async get(toolId: number): Promise<DesignTool> {
    return apiClient.get<DesignTool>(`/design-studio/tools/${toolId}`);
  },

  async getOptions(toolId: number): Promise<ListResponse<DesignToolOption>> {
    return apiClient.get<ListResponse<DesignToolOption>>(`/design-studio/tools/${toolId}/options`);
  },

  async getImageRequirements(toolId: number): Promise<ListResponse<DesignToolImageRequirement>> {
    return apiClient.get<ListResponse<DesignToolImageRequirement>>(`/design-studio/tools/${toolId}/image-requirements`);
  },
};
