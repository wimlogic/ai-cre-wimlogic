/**
 * AI-CRE WIMLOGIC V1.0 - Decoupled REST API Service Layer
 * Connects directly to the Express + Vite backend service
 */

import { 
  CreProject, 
  CreProperty, 
  CrePropertyImage, 
  CreScan,
  CreWorkflowExecution, 
  CreWorkflowResult, 
  CreWorkflowEvent, 
  CreRenovationScenario, 
  CrePropertyAnalysisReport, 
  CreConceptDesign, 
  CreGeneratedAsset,
  ApiUsageLog,
  CreStats
} from '../types';

export interface ApiResponse<T> {
  status: number;
  message?: string;
  data: T;
}

export const CreApi = {
  /**
   * Fetch core metrics for the dashboard
   */
  async getStats(): Promise<ApiResponse<CreStats>> {
    const res = await fetch('/api/v1/stats');
    if (!res.ok) throw new Error('Failed to load stats');
    return res.json();
  },

  /**
   * Settings endpoints
   */
  async getSettings(): Promise<ApiResponse<any>> {
    const res = await fetch('/api/v1/settings');
    if (!res.ok) throw new Error('Failed to load settings');
    return res.json();
  },

  async updateSettings(settings: any): Promise<ApiResponse<any>> {
    const res = await fetch('/api/v1/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings)
    });
    if (!res.ok) throw new Error('Failed to update settings');
    return res.json();
  },

  /**
   * Project management endpoints
   */
  async getProjects(filters?: { status?: string; search?: string }): Promise<{ count: number; items: CreProject[] }> {
    const params = new URLSearchParams();
    if (filters?.status) params.append('status', filters.status);
    if (filters?.search) params.append('search', filters.search);

    const res = await fetch(`/api/v1/projects?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to load projects');
    return res.json();
  },

  async getProject(id: number | string): Promise<CreProject> {
    const res = await fetch(`/api/v1/projects/${id}`);
    if (!res.ok) throw new Error('Failed to load project details');
    return res.json();
  },

  async createProject(projectData: Partial<CreProject>): Promise<CreProject> {
    const res = await fetch('/api/v1/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(projectData)
    });
    if (!res.ok) throw new Error('Failed to create project workspace');
    return res.json();
  },

  async deleteProject(id: number): Promise<{ success: boolean }> {
    const res = await fetch(`/api/v1/projects/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete project');
    return res.json();
  },

  /**
   * Property management endpoints
   */
  async getProperties(filters?: { project_id?: string; search?: string; status?: string }): Promise<{ count: number; items: CreProperty[] }> {
    const params = new URLSearchParams();
    if (filters?.project_id) params.append('project_id', filters.project_id);
    if (filters?.search) params.append('search', filters.search);
    if (filters?.status) params.append('status', filters.status);

    const res = await fetch(`/api/v1/properties?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to load properties');
    return res.json();
  },

  async getProperty(id: number): Promise<CreProperty> {
    const res = await fetch(`/api/v1/properties/${id}`);
    if (!res.ok) throw new Error('Failed to load property detail');
    return res.json();
  },

  async createProperty(propertyData: Partial<CreProperty> & { project_id?: string }): Promise<CreProperty> {
    const res = await fetch('/api/v1/properties', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(propertyData)
    });
    if (!res.ok) throw new Error('Failed to create property record');
    return res.json();
  },

  async deleteProperty(id: number): Promise<{ success: boolean }> {
    const res = await fetch(`/api/v1/properties/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete property record');
    return res.json();
  },

  /**
   * Property image management
   */
  async getPropertyImages(propertyId: number): Promise<{ count: number; items: CrePropertyImage[] }> {
    const res = await fetch(`/api/v1/properties/${propertyId}/images`);
    if (!res.ok) throw new Error('Failed to load property imagery');
    return res.json();
  },

  async uploadPropertyImage(propertyId: number, imageData: Partial<CrePropertyImage>): Promise<CrePropertyImage> {
    const res = await fetch(`/api/v1/properties/${propertyId}/images`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(imageData)
    });
    if (!res.ok) throw new Error('Failed to attach property image');
    return res.json();
  },

  async deletePropertyImage(id: number): Promise<{ success: boolean }> {
    const res = await fetch(`/api/v1/property-images/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete image');
    return res.json();
  },

  /**
   * LIDAR and GIS Scan Syncing
   */
  async getScans(): Promise<{ count: number; items: CreScan[] }> {
    const res = await fetch('/api/v1/scans');
    if (!res.ok) throw new Error('Failed to fetch street scans');
    return res.json();
  },

  async executeScan(id: number): Promise<{ success: boolean; data: CreScan }> {
    const res = await fetch(`/api/v1/scans/${id}/execute`, { method: 'PUT' });
    if (!res.ok) throw new Error('Failed to execute scan sync');
    return res.json();
  },

  /**
   * DEV-TOOLS Workflow orchestration
   */
  async getWorkflows(filters?: { property_id?: number }): Promise<{ count: number; items: CreWorkflowExecution[] }> {
    const params = new URLSearchParams();
    if (filters?.property_id) params.append('property_id', String(filters.property_id));

    const res = await fetch(`/api/v1/workflows?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to load workflows');
    return res.json();
  },

  async getWorkflowDetails(id: number): Promise<CreWorkflowExecution & { events: CreWorkflowEvent[]; result?: CreWorkflowResult }> {
    const res = await fetch(`/api/v1/workflows/${id}`);
    if (!res.ok) throw new Error('Failed to load workflow execution details');
    return res.json();
  },

  async dispatchWorkflow(workflowData: { project_id?: number; property_id: number; workflow_code: string; priority?: string }): Promise<CreWorkflowExecution> {
    const res = await fetch('/api/v1/workflows', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(workflowData)
    });
    if (!res.ok) throw new Error('Failed to dispatch orchestrator workflow');
    return res.json();
  },

  /**
   * Renovation scenarios
   */
  async getScenarios(filters?: { property_id?: number }): Promise<{ count: number; items: CreRenovationScenario[] }> {
    const params = new URLSearchParams();
    if (filters?.property_id) params.append('property_id', String(filters.property_id));

    const res = await fetch(`/api/v1/scenarios?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to load renovation scenarios');
    return res.json();
  },

  async createScenario(scenarioData: Partial<CreRenovationScenario>): Promise<CreRenovationScenario> {
    const res = await fetch('/api/v1/scenarios', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(scenarioData)
    });
    if (!res.ok) throw new Error('Failed to save renovation scenario');
    return res.json();
  },

  async updateScenarioStatus(id: number, status: 'draft' | 'approved' | 'rejected'): Promise<CreRenovationScenario> {
    const res = await fetch(`/api/v1/scenarios/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
    if (!res.ok) throw new Error('Failed to update scenario approval status');
    return res.json();
  },

  /**
   * Feasibility analysis reports
   */
  async getReports(filters?: { property_id?: number }): Promise<{ count: number; items: CrePropertyAnalysisReport[] }> {
    const params = new URLSearchParams();
    if (filters?.property_id) params.append('property_id', String(filters.property_id));

    const res = await fetch(`/api/v1/reports?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to load analysis reports');
    return res.json();
  },

  async getReport(id: number): Promise<CrePropertyAnalysisReport> {
    const res = await fetch(`/api/v1/reports/${id}`);
    if (!res.ok) throw new Error('Failed to load analysis report detail');
    return res.json();
  },

  /**
   * Concept Designs
   */
  async getConceptDesigns(filters?: { property_id?: number }): Promise<{ count: number; items: CreConceptDesign[] }> {
    const params = new URLSearchParams();
    if (filters?.property_id) params.append('property_id', String(filters.property_id));

    const res = await fetch(`/api/v1/concept-designs?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to load conceptual designs');
    return res.json();
  },

  async createConceptDesign(designData: Partial<CreConceptDesign>): Promise<CreConceptDesign> {
    const res = await fetch('/api/v1/concept-designs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(designData)
    });
    if (!res.ok) throw new Error('Failed to save conceptual elevation');
    return res.json();
  },

  async updateConceptDesignStatus(id: number, status: 'draft' | 'under_review' | 'approved'): Promise<CreConceptDesign> {
    const res = await fetch(`/api/v1/concept-designs/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
    if (!res.ok) throw new Error('Failed to update design approval state');
    return res.json();
  },

  /**
   * Generated Assets
   */
  async getGeneratedAssets(filters?: { property_id?: number }): Promise<{ count: number; items: CreGeneratedAsset[] }> {
    const params = new URLSearchParams();
    if (filters?.property_id) params.append('property_id', String(filters.property_id));

    const res = await fetch(`/api/v1/generated-assets?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch generated assets');
    return res.json();
  },

  /**
   * API logs
   */
  async getApiLogs(): Promise<{ count: number; items: ApiUsageLog[] }> {
    const res = await fetch('/api/v1/api-logs');
    if (!res.ok) throw new Error('Failed to fetch API logging sequence');
    return res.json();
  }
};
