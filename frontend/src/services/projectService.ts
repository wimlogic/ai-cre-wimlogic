import { apiClient } from './apiClient';
import { Project, ListResponse } from '../types';

export const projectService = {
  async list(params?: {
    skip?: number;
    limit?: number;
    status?: string;
    search?: string;
  }): Promise<ListResponse<Project>> {
    const query = new URLSearchParams();
    if (params?.skip !== undefined) query.append('skip', String(params.skip));
    if (params?.limit !== undefined) query.append('limit', String(params.limit));
    if (params?.status) query.append('status', params.status);
    if (params?.search) query.append('search', params.search);

    const queryString = query.toString();
    const endpoint = queryString ? `/projects/?${queryString}` : '/projects/';
    return apiClient.get<ListResponse<Project>>(endpoint);
  },

  async get(id: number): Promise<Project> {
    return apiClient.get<Project>(`/projects/${id}`);
  },

  async getByProjectId(projectId: string): Promise<Project> {
    return apiClient.get<Project>(`/projects/by-id/${projectId}`);
  },

  async create(data: Partial<Project>): Promise<Project> {
    return apiClient.post<Project>('/projects/', data);
  },

  async update(id: number, data: Partial<Project>): Promise<Project> {
    return apiClient.put<Project>(`/projects/${id}`, data);
  },

  async delete(id: number): Promise<{ success: boolean }> {
    return apiClient.delete<{ success: boolean }>(`/projects/${id}`);
  },
};
