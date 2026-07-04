import { apiClient } from './apiClient';
import { Property, ProjectProperty, ListResponse } from '../types';

export const propertyService = {
  async list(params?: {
    skip?: number;
    limit?: number;
    city?: string;
    state?: string;
    search?: string;
  }): Promise<ListResponse<Property>> {
    const query = new URLSearchParams();
    if (params?.skip !== undefined) query.append('skip', String(params.skip));
    if (params?.limit !== undefined) query.append('limit', String(params.limit));
    if (params?.city) query.append('city', params.city);
    if (params?.state) query.append('state', params.state);
    if (params?.search) query.append('search', params.search);

    const queryString = query.toString();
    const endpoint = queryString ? `/properties/?${queryString}` : '/properties/';
    return apiClient.get<ListResponse<Property>>(endpoint);
  },

  async get(id: number): Promise<Property> {
    return apiClient.get<Property>(`/properties/${id}`);
  },

  async getByUid(propertyUid: string): Promise<Property> {
    return apiClient.get<Property>(`/properties/by-uid/${propertyUid}`);
  },

  async create(data: Partial<Property>): Promise<Property> {
    return apiClient.post<Property>('/properties/', data);
  },

  async update(id: number, data: Partial<Property>): Promise<Property> {
    return apiClient.put<Property>(`/properties/${id}`, data);
  },

  async delete(id: number): Promise<{ success: boolean }> {
    return apiClient.delete<{ success: boolean }>(`/properties/${id}`);
  },

  // Project-Property Associations
  async listAssociations(params?: {
    skip?: number;
    limit?: number;
    project_id?: string;
    property_id?: number;
    scan_id?: string;
  }): Promise<ListResponse<ProjectProperty>> {
    const query = new URLSearchParams();
    if (params?.skip !== undefined) query.append('skip', String(params.skip));
    if (params?.limit !== undefined) query.append('limit', String(params.limit));
    if (params?.project_id) query.append('project_id', params.project_id);
    if (params?.property_id) query.append('property_id', String(params.property_id));
    if (params?.scan_id) query.append('scan_id', params.scan_id);

    const queryString = query.toString();
    const endpoint = queryString ? `/project-properties/?${queryString}` : '/project-properties/';
    return apiClient.get<ListResponse<ProjectProperty>>(endpoint);
  },

  async createAssociation(data: {
    project_id: string;
    property_id: number;
    scan_id?: string;
    role?: string;
    selected?: number;
  }): Promise<ProjectProperty> {
    return apiClient.post<ProjectProperty>('/project-properties/', data);
  },

  async deleteAssociation(id: number): Promise<{ success: boolean }> {
    return apiClient.delete<{ success: boolean }>(`/project-properties/${id}`);
  },

  // Combined helper to list all properties for a specific project
  async listByProject(projectId: string): Promise<Property[]> {
    const res = await this.listAssociations({ project_id: projectId, limit: 200 });
    if (!res.items || res.items.length === 0) {
      return [];
    }
    
    // Resolve full property data in parallel
    const properties = await Promise.all(
      res.items.map(async (assoc) => {
        try {
          const prop = await this.get(assoc.property_id);
          return prop;
        } catch (e) {
          console.error(`[Property Service] Failed to fetch details for property ${assoc.property_id}:`, e);
          return null;
        }
      })
    );
    
    return properties.filter((p): p is Property => p !== null);
  },

  // Helper to assign property to a project
  async assignToProject(propertyId: number, projectId: string): Promise<ProjectProperty> {
    return this.createAssociation({
      project_id: projectId,
      property_id: propertyId,
      selected: 1,
    });
  }
};
