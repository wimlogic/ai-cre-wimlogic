import { apiClient } from './apiClient';
import { CreRenovationScenario, CrePropertyAnalysisReport, CreConceptDesign } from '../types';

export const additionalService = {
  listScenarios: async (params?: { project_id?: string; property_id?: number; status?: string; search?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.project_id) searchParams.append('project_id', params.project_id);
    if (params?.property_id !== undefined) searchParams.append('property_id', String(params.property_id));
    if (params?.status) searchParams.append('status', params.status);
    if (params?.search) searchParams.append('search', params.search);
    return apiClient.get<{ count: number; items: CreRenovationScenario[] }>(`/renovation-scenarios/${searchParams.toString() ? `?${searchParams.toString()}` : ''}`);
  },

  listReports: async (params?: { project_id?: string; property_id?: number; search?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.project_id) searchParams.append('project_id', params.project_id);
    if (params?.property_id !== undefined) searchParams.append('property_id', String(params.property_id));
    if (params?.search) searchParams.append('search', params.search);
    return apiClient.get<{ count: number; items: CrePropertyAnalysisReport[] }>(`/property-analysis-reports/${searchParams.toString() ? `?${searchParams.toString()}` : ''}`);
  },

  listConceptDesigns: async (params?: { project_id?: string; property_id?: number; status?: string; search?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.project_id) searchParams.append('project_id', params.project_id);
    if (params?.property_id !== undefined) searchParams.append('property_id', String(params.property_id));
    if (params?.status) searchParams.append('status', params.status);
    if (params?.search) searchParams.append('search', params.search);
    return apiClient.get<{ count: number; items: CreConceptDesign[] }>(`/concept-designs/${searchParams.toString() ? `?${searchParams.toString()}` : ''}`);
  },
};
