import { apiClient } from './apiClient';
import { WorkflowExecution, WorkflowEvent, WorkflowResult, ResultSection, ListResponse } from '../types';

export interface WorkflowSubmitPayload {
  project_id: number;
  property_id: number;
  workflow_code: string;
  scenario_id?: number;
  priority?: string;
  metadata_json?: Record<string, any>;
}

export const workflowService = {
  // Submit new workflow execution through orchestrator
  async submit(payload: WorkflowSubmitPayload): Promise<WorkflowExecution> {
    return apiClient.post<WorkflowExecution>('/ai-orchestration/submit', payload);
  },

  // Check specific execution status directly
  async checkStatus(executionId: number): Promise<{ execution_id: number; status: string }> {
    return apiClient.get<{ execution_id: number; status: string }>(`/ai-orchestration/status/${executionId}`);
  },

  // List past and current executions
  async listExecutions(params?: {
    skip?: number;
    limit?: number;
    project_id?: number;
    property_id?: number;
    status?: string;
    search?: string;
  }): Promise<ListResponse<WorkflowExecution>> {
    const query = new URLSearchParams();
    if (params?.skip !== undefined) query.append('skip', String(params.skip));
    if (params?.limit !== undefined) query.append('limit', String(params.limit));
    if (params?.project_id !== undefined) query.append('project_id', String(params.project_id));
    if (params?.property_id !== undefined) query.append('property_id', String(params.property_id));
    if (params?.status) query.append('status', params.status);
    if (params?.search) query.append('search', params.search);

    const queryString = query.toString();
    const endpoint = queryString ? `/workflow-executions/?${queryString}` : '/workflow-executions/';
    return apiClient.get<ListResponse<WorkflowExecution>>(endpoint);
  },

  // Get specific execution
  async getExecution(id: number): Promise<WorkflowExecution> {
    return apiClient.get<WorkflowExecution>(`/workflow-executions/${id}`);
  },

  // Get events (timeline logs) for an execution
  async getExecutionEvents(id: number): Promise<ListResponse<WorkflowEvent>> {
    return apiClient.get<ListResponse<WorkflowEvent>>(`/workflow-executions/${id}/events`);
  },

  // List all workflow results
  async listResults(params?: {
    skip?: number;
    limit?: number;
    execution_id?: number;
    search?: string;
  }): Promise<ListResponse<WorkflowResult>> {
    const query = new URLSearchParams();
    if (params?.skip !== undefined) query.append('skip', String(params.skip));
    if (params?.limit !== undefined) query.append('limit', String(params.limit));
    if (params?.execution_id !== undefined) query.append('execution_id', String(params.execution_id));
    if (params?.search) query.append('search', params.search);

    const queryString = query.toString();
    const endpoint = queryString ? `/workflow-results/?${queryString}` : '/workflow-results/';
    return apiClient.get<ListResponse<WorkflowResult>>(endpoint);
  },

  // Get single result
  async getResult(id: number): Promise<WorkflowResult> {
    return apiClient.get<WorkflowResult>(`/workflow-results/${id}`);
  },

  // Get parsed sections of a result
  async getResultSections(id: number): Promise<ListResponse<ResultSection>> {
    return apiClient.get<ListResponse<ResultSection>>(`/workflow-results/${id}/sections`);
  },
};
