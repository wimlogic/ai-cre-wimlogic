import { apiClient } from './apiClient';
import { CreWorkflowExecution } from '../types';

export interface WorkflowSubmitRequest {
  project_id: number;
  property_id: number;
  workflow_code: string;
  scenario_id?: number;
  priority?: string;
  metadata_json?: Record<string, any>;
}

export interface WorkflowStatusResponse {
  execution_id: number;
  status: string;
}

export const aiOrchestrationService = {
  submit: async (req: WorkflowSubmitRequest): Promise<CreWorkflowExecution> => {
    return apiClient.post<CreWorkflowExecution>('/ai-orchestration/submit', req);
  },

  checkStatus: async (executionId: number): Promise<WorkflowStatusResponse> => {
    return apiClient.get<WorkflowStatusResponse>(`/ai-orchestration/status/${executionId}`);
  },

  callback: async (data: {
    devtools_execution_id: string;
    status: string;
    payload: Record<string, any>;
  }): Promise<CreWorkflowExecution> => {
    return apiClient.post<CreWorkflowExecution>('/ai-orchestration/callback', data);
  },
};
