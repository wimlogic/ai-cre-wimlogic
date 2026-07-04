import { apiClient } from './apiClient';

export interface ResultSection {
  section_id: number;
  result_id: number;
  section_type: string;
  display_order: number;
  title?: string;
  content?: string;
  confidence_score?: number;
  created_at: string;
}

export interface ResultSectionListResponse {
  count: number;
  items: ResultSection[];
}

export const resultSectionsService = {
  list: async (params?: {
    skip?: number;
    limit?: number;
    result_id?: number;
    section_type?: string;
    search?: string;
  }): Promise<ResultSectionListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.skip !== undefined) searchParams.append('skip', String(params.skip));
    if (params?.limit !== undefined) searchParams.append('limit', String(params.limit));
    if (params?.result_id !== undefined) searchParams.append('result_id', String(params.result_id));
    if (params?.section_type) searchParams.append('section_type', params.section_type);
    if (params?.search) searchParams.append('search', params.search);

    const queryStr = searchParams.toString();
    return apiClient.get<ResultSectionListResponse>(`/result-sections/${queryStr ? `?${queryStr}` : ''}`);
  },

  get: async (id: number): Promise<ResultSection> => {
    return apiClient.get<ResultSection>(`/result-sections/${id}`);
  },

  create: async (section: Omit<ResultSection, 'section_id' | 'created_at'>): Promise<ResultSection> => {
    return apiClient.post<ResultSection>('/result-sections/', section);
  },

  update: async (id: number, section: Partial<ResultSection>): Promise<ResultSection> => {
    return apiClient.put<ResultSection>(`/result-sections/${id}`, section);
  },

  delete: async (id: number): Promise<{ success: boolean }> => {
    return apiClient.delete<{ success: boolean }>(`/result-sections/${id}`);
  },
};
