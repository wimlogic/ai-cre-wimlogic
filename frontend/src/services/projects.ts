import { apiClient } from './apiClient';
import { CreProject } from '../types';

export interface ProjectListResponse {
  count: number;
  items: CreProject[];
}

export const projectsService = {
  list: async (params?: { skip?: number; limit?: number; status?: string; search?: string }): Promise<ProjectListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.skip !== undefined) searchParams.append('skip', String(params.skip));
    if (params?.limit !== undefined) searchParams.append('limit', String(params.limit));
    if (params?.status) searchParams.append('status', params.status);
    if (params?.search) searchParams.append('search', params.search);

    const queryStr = searchParams.toString();
    return apiClient.get<ProjectListResponse>(`/projects/${queryStr ? `?${queryStr}` : ''}`);
  },

  get: async (id: number): Promise<CreProject> => {
    return apiClient.get<CreProject>(`/projects/${id}`);
  },

  getByProjectId: async (projectId: string): Promise<CreProject> => {
    return apiClient.get<CreProject>(`/projects/by-id/${projectId}`);
  },

  create: async (project: Omit<CreProject, 'id' | 'created_at' | 'updated_at'>): Promise<CreProject> => {
    return apiClient.post<CreProject>('/projects/', project);
  },

  update: async (id: number, project: Partial<CreProject>): Promise<CreProject> => {
    return apiClient.put<CreProject>(`/projects/${id}`, project);
  },

  delete: async (id: number): Promise<{ success: boolean }> => {
    return apiClient.delete<{ success: boolean }>(`/projects/${id}`);
  },
};
