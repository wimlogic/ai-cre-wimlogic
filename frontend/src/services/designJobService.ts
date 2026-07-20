import { apiClient } from './apiClient';
import {
  DesignJob,
  DesignJobImage,
  DesignJobExecution,
  DesignJobAttemptResponse,
  ListResponse,
} from '../types/index';

/**
 * services/designJobService.ts
 *
 * Design Job lifecycle service (Home Studio Frontend Checkpoint 1),
 * covering every backend endpoint delivered through Design Studio
 * Checkpoint 8: create -> configure images/options -> submit -> execute
 * -> retry -> execution history. Mirrors propertyImageService.ts's plain
 * apiClient-based pattern - no new HTTP abstraction introduced.
 *
 * This service sends business intent only (project_id, property_id,
 * tool_id, selected images, tool option values) - it never constructs or
 * exposes workflow_code, Workflow Template, or any DEV-TOOLS-facing
 * identifier to its callers beyond passing through whatever the backend
 * Read schema already includes on a DesignJob/DesignTool record.
 */
export const designJobService = {
  async create(data: { project_id: string; property_id: number; tool_id: number }): Promise<DesignJob> {
    return apiClient.post<DesignJob>('/design-studio/jobs/', data);
  },

  async get(jobId: number): Promise<DesignJob> {
    return apiClient.get<DesignJob>(`/design-studio/jobs/${jobId}`);
  },

  async list(params?: {
    property_id?: number;
    project_id?: string;
    tool_id?: number;
    status?: string;
    skip?: number;
    limit?: number;
  }): Promise<ListResponse<DesignJob>> {
    const query = new URLSearchParams();
    if (params?.property_id !== undefined) query.append('property_id', String(params.property_id));
    if (params?.project_id) query.append('project_id', params.project_id);
    if (params?.tool_id !== undefined) query.append('tool_id', String(params.tool_id));
    if (params?.status) query.append('status', params.status);
    if (params?.skip !== undefined) query.append('skip', String(params.skip));
    if (params?.limit !== undefined) query.append('limit', String(params.limit));

    const queryString = query.toString();
    const endpoint = queryString ? `/design-studio/jobs/?${queryString}` : '/design-studio/jobs/';
    return apiClient.get<ListResponse<DesignJob>>(endpoint);
  },

  async setImages(
    jobId: number,
    images: { property_image_id: number; input_role: string }[]
  ): Promise<DesignJobImage[]> {
    return apiClient.put<DesignJobImage[]>(`/design-studio/jobs/${jobId}/images`, { images });
  },

  async getImages(jobId: number): Promise<DesignJobImage[]> {
    return apiClient.get<DesignJobImage[]>(`/design-studio/jobs/${jobId}/images`);
  },

  async setOptions(jobId: number, toolOptions: Record<string, any>): Promise<DesignJob> {
    return apiClient.put<DesignJob>(`/design-studio/jobs/${jobId}/options`, { tool_options: toolOptions });
  },

  async submit(jobId: number): Promise<DesignJob> {
    return apiClient.post<DesignJob>(`/design-studio/jobs/${jobId}/submit`, {});
  },

  async execute(jobId: number): Promise<DesignJobAttemptResponse> {
    return apiClient.post<DesignJobAttemptResponse>(`/design-studio/jobs/${jobId}/execute`, {});
  },

  async retry(jobId: number): Promise<DesignJobAttemptResponse> {
    return apiClient.post<DesignJobAttemptResponse>(`/design-studio/jobs/${jobId}/retry`, {});
  },

  async getExecutions(jobId: number): Promise<ListResponse<DesignJobExecution>> {
    return apiClient.get<ListResponse<DesignJobExecution>>(`/design-studio/jobs/${jobId}/executions`);
  },
};
