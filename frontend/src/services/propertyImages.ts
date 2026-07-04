import { apiClient } from './apiClient';
import { CrePropertyImage } from '../types';

export interface PropertyImageListResponse {
  count: number;
  items: CrePropertyImage[];
}

export const propertyImagesService = {
  list: async (params?: {
    skip?: number;
    limit?: number;
    property_id?: number;
    project_id?: string;
    image_type?: string;
    include_deleted?: boolean;
    search?: string;
  }): Promise<PropertyImageListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.skip !== undefined) searchParams.append('skip', String(params.skip));
    if (params?.limit !== undefined) searchParams.append('limit', String(params.limit));
    if (params?.property_id !== undefined) searchParams.append('property_id', String(params.property_id));
    if (params?.project_id) searchParams.append('project_id', params.project_id);
    if (params?.image_type) searchParams.append('image_type', params.image_type);
    if (params?.include_deleted !== undefined) searchParams.append('include_deleted', String(params.include_deleted));
    if (params?.search) searchParams.append('search', params.search);

    const queryStr = searchParams.toString();
    return apiClient.get<PropertyImageListResponse>(`/property-images/${queryStr ? `?${queryStr}` : ''}`);
  },

  get: async (id: number): Promise<CrePropertyImage> => {
    return apiClient.get<CrePropertyImage>(`/property-images/${id}`);
  },

  create: async (image: Omit<CrePropertyImage, 'id' | 'created_at' | 'is_deleted'> & { is_deleted?: number }): Promise<CrePropertyImage> => {
    return apiClient.post<CrePropertyImage>('/property-images/', image);
  },

  update: async (id: number, image: Partial<CrePropertyImage>): Promise<CrePropertyImage> => {
    return apiClient.put<CrePropertyImage>(`/property-images/${id}`, image);
  },

  delete: async (id: number, soft: boolean = true): Promise<{ success: boolean }> => {
    return apiClient.delete<{ success: boolean }>(`/property-images/${id}?soft=${soft}`);
  },
};
