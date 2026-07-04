import { apiClient } from './apiClient';
import { CreWorkflowResult } from '../types';

export interface WorkflowResultListResponse {
  count: number;
  items: CreWorkflowResult[];
}

export const workflowResultsService = {
  list: async (params?: { skip?: number; limit?: number; execution_id?: number; search?: string }): Promise<WorkflowResultListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.skip !== undefined) searchParams.append('skip', String(params.skip));
    if (params?.limit !== undefined) searchParams.append('limit', String(params.limit));
    if (params?.execution_id !== undefined) searchParams.append('execution_id', String(params.execution_id));
    if (params?.search) searchParams.append('search', params.search);

    const queryStr = searchParams.toString();
    return apiClient.get<WorkflowResultListResponse>(`/workflow-results/${queryStr ? `?${queryStr}` : ''}`);
  },

  get: async (id: number): Promise<CreWorkflowResult> => {
    return apiClient.get<CreWorkflowResult>(`/workflow-results/${id}`);
  },

  create: async (result: Omit<CreWorkflowResult, 'result_id' | 'created_at' | 'received_at'> & { received_at?: string }): Promise<CreWorkflowResult> => {
    return apiClient.post<CreWorkflowResult>('/workflow-results/', result);
  },

  update: async (id: number, result: Partial<CreWorkflowResult>): Promise<CreWorkflowResult> => {
    return apiClient.put<CreWorkflowResult>(`/workflow-results/${id}`, result);
  },

  delete: async (id: number): Promise<{ success: boolean }> => {
    return apiClient.delete<{ success: boolean }>(`/workflow-results/${id}`);
  },
};
