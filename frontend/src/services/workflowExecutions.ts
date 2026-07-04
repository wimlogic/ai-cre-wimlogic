import { apiClient } from './apiClient';
import { CreWorkflowExecution, CreWorkflowEvent } from '../types';

export interface WorkflowExecutionListResponse {
  count: number;
  items: CreWorkflowExecution[];
}

export interface WorkflowEventListResponse {
  count: number;
  items: CreWorkflowEvent[];
}

export const workflowExecutionsService = {
  list: async (params?: {
    skip?: number;
    limit?: number;
    project_id?: number;
    property_id?: number;
    status?: string;
    search?: string;
  }): Promise<WorkflowExecutionListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.skip !== undefined) searchParams.append('skip', String(params.skip));
    if (params?.limit !== undefined) searchParams.append('limit', String(params.limit));
    if (params?.project_id !== undefined) searchParams.append('project_id', String(params.project_id));
    if (params?.property_id !== undefined) searchParams.append('property_id', String(params.property_id));
    if (params?.status) searchParams.append('status', params.status);
    if (params?.search) searchParams.append('search', params.search);

    const queryStr = searchParams.toString();
    return apiClient.get<WorkflowExecutionListResponse>(`/workflow-executions/${queryStr ? `?${queryStr}` : ''}`);
  },

  get: async (id: number): Promise<CreWorkflowExecution> => {
    return apiClient.get<CreWorkflowExecution>(`/workflow-executions/${id}`);
  },

  getByNumber: async (executionNumber: string): Promise<CreWorkflowExecution> => {
    return apiClient.get<CreWorkflowExecution>(`/workflow-executions/by-number/${executionNumber}`);
  },

  create: async (execution: Omit<CreWorkflowExecution, 'execution_id' | 'execution_number' | 'created_at' | 'updated_at' | 'retry_count'> & { retry_count?: number }): Promise<CreWorkflowExecution> => {
    return apiClient.post<CreWorkflowExecution>('/workflow-executions/', execution);
  },

  update: async (id: number, execution: Partial<CreWorkflowExecution>): Promise<CreWorkflowExecution> => {
    return apiClient.put<CreWorkflowExecution>(`/workflow-executions/${id}`, execution);
  },

  delete: async (id: number): Promise<{ success: boolean }> => {
    return apiClient.delete<{ success: boolean }>(`/workflow-executions/${id}`);
  },

  listEvents: async (id: number, skip: number = 0, limit: number = 100): Promise<WorkflowEventListResponse> => {
    return apiClient.get<WorkflowEventListResponse>(`/workflow-executions/${id}/events?skip=${skip}&limit=${limit}`);
  },

  addEvent: async (id: number, event: Omit<CreWorkflowEvent, 'event_id' | 'execution_id' | 'created_at'>): Promise<CreWorkflowEvent> => {
    return apiClient.post<CreWorkflowEvent>(`/workflow-executions/${id}/events`, event);
  },
};
