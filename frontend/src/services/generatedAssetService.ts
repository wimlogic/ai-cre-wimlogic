import { apiClient } from './apiClient';
import { GeneratedAsset, ListResponse } from '../types';

export const generatedAssetService = {
  async list(params?: {
    skip?: number;
    limit?: number;
    property_id?: number;
    execution_id?: number;
    asset_type?: string;
    search?: string;
  }): Promise<ListResponse<GeneratedAsset>> {
    const query = new URLSearchParams();
    if (params?.skip !== undefined) query.append('skip', String(params.skip));
    if (params?.limit !== undefined) query.append('limit', String(params.limit));
    if (params?.property_id !== undefined) query.append('property_id', String(params.property_id));
    if (params?.execution_id !== undefined) query.append('execution_id', String(params.execution_id));
    if (params?.asset_type) query.append('asset_type', params.asset_type);
    if (params?.search) query.append('search', params.search);

    const queryString = query.toString();
    const endpoint = queryString ? `/generated-assets/?${queryString}` : '/generated-assets/';
    return apiClient.get<ListResponse<GeneratedAsset>>(endpoint);
  },

  async get(id: number): Promise<GeneratedAsset> {
    return apiClient.get<GeneratedAsset>(`/generated-assets/${id}`);
  },
};
