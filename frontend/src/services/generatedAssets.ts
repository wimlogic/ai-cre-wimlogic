import { apiClient } from './apiClient';
import { CreGeneratedAsset } from '../types';

export interface GeneratedAssetListResponse {
  count: number;
  items: CreGeneratedAsset[];
}

export const generatedAssetsService = {
  list: async (params?: {
    skip?: number;
    limit?: number;
    property_id?: number;
    execution_id?: number;
    asset_type?: string;
    search?: string;
  }): Promise<GeneratedAssetListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.skip !== undefined) searchParams.append('skip', String(params.skip));
    if (params?.limit !== undefined) searchParams.append('limit', String(params.limit));
    if (params?.property_id !== undefined) searchParams.append('property_id', String(params.property_id));
    if (params?.execution_id !== undefined) searchParams.append('execution_id', String(params.execution_id));
    if (params?.asset_type) searchParams.append('asset_type', params.asset_type);
    if (params?.search) searchParams.append('search', params.search);

    const queryStr = searchParams.toString();
    return apiClient.get<GeneratedAssetListResponse>(`/generated-assets/${queryStr ? `?${queryStr}` : ''}`);
  },

  get: async (id: number): Promise<CreGeneratedAsset> => {
    return apiClient.get<CreGeneratedAsset>(`/generated-assets/${id}`);
  },

  create: async (asset: Omit<CreGeneratedAsset, 'asset_id' | 'created_at'>): Promise<CreGeneratedAsset> => {
    return apiClient.post<CreGeneratedAsset>('/generated-assets/', asset);
  },

  update: async (id: number, asset: Partial<CreGeneratedAsset>): Promise<CreGeneratedAsset> => {
    return apiClient.put<CreGeneratedAsset>(`/generated-assets/${id}`, asset);
  },

  delete: async (id: number): Promise<{ success: boolean }> => {
    return apiClient.delete<{ success: boolean }>(`/generated-assets/${id}`);
  },
};
