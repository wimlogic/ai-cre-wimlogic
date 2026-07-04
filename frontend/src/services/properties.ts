import { apiClient } from './apiClient';
import { CreProperty } from '../types';

export interface PropertyListResponse {
  count: number;
  items: CreProperty[];
}

export const propertiesService = {
  list: async (params?: { skip?: number; limit?: number; city?: string; state?: string; search?: string }): Promise<PropertyListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.skip !== undefined) searchParams.append('skip', String(params.skip));
    if (params?.limit !== undefined) searchParams.append('limit', String(params.limit));
    if (params?.city) searchParams.append('city', params.city);
    if (params?.state) searchParams.append('state', params.state);
    if (params?.search) searchParams.append('search', params.search);

    const queryStr = searchParams.toString();
    return apiClient.get<PropertyListResponse>(`/properties/${queryStr ? `?${queryStr}` : ''}`);
  },

  get: async (id: number): Promise<CreProperty> => {
    return apiClient.get<CreProperty>(`/properties/${id}`);
  },

  getByUid: async (uid: string): Promise<CreProperty> => {
    return apiClient.get<CreProperty>(`/properties/by-uid/${uid}`);
  },

  create: async (property: Omit<CreProperty, 'id' | 'created_at' | 'updated_at'>): Promise<CreProperty> => {
    return apiClient.post<CreProperty>('/properties/', property);
  },

  update: async (id: number, property: Partial<CreProperty>): Promise<CreProperty> => {
    return apiClient.put<CreProperty>(`/properties/${id}`, property);
  },

  delete: async (id: number): Promise<{ success: boolean }> => {
    return apiClient.delete<{ success: boolean }>(`/properties/${id}`);
  },
};
