/**
 * AI-CRE WIMLOGIC V1.0 - Core System Types & Interfaces
 * Matches exactly with the cre_ projects MySQL schema
 */

export interface CreProject {
  id: number;
  project_id: string;
  project_name: string;
  description: string;
  status: 'active' | 'archived' | 'completed';
  created_at: string;
  updated_at: string;
  default_city?: string;
  default_state?: string;
  main_street?: string;
  beginning_address?: string;
  ending_address?: string;
  side?: string;
  scan_mode?: string;
}

export interface CreProperty {
  id: number;
  property_uid: string;
  address?: string;
  city?: string;
  state?: string;
  zip?: string;
  apn?: string;
  latitude?: number;
  longitude?: number;
  lot_sqft?: number;
  building_sqft?: number;
  year_built?: number;
  zoning_code?: string;
  existing_use?: string;
  business_name?: string;
  land_value?: number;
  improvement_value?: number;
  total_assessed_value?: number;
  data_source?: string;
  created_at: string;
  updated_at: string;
  street_number?: string;
  street_name?: string;
  side_of_street?: string;
  phase2_source?: string;
  display_address?: string;
  status?: string;
  source?: string;
  notes?: string;
  confidence_score?: string;
  raw_api_json?: string; // stringified JSON
  api_source_url?: string;
}

export interface CreProjectProperty {
  id: number;
  project_id: string;
  property_id: number;
  scan_id?: string;
  role?: string;
  selected: number; // 0 or 1
  created_at: string;
}

export interface CrePropertyImage {
  id: number;
  property_id: number;
  image_type: 'street_view' | 'satellite' | 'parcel_map' | 'uploaded';
  image_url?: string;
  provider?: string;
  heading?: number;
  pitch?: number;
  fov?: number;
  cached_path?: string;
  last_checked_at?: string;
  created_at: string;
  project_id?: string;
  original_file_name?: string;
  file_size?: number;
  file_type?: string;
  image_role?: string;
  notes?: string;
  status?: string;
  is_deleted: number; // 0 or 1
}

export interface CreScanJob {
  id: number;
  scan_id: string;
  project_id: string;
  project_name: string;
  main_street: string;
  beginning_address: string;
  ending_address: string;
  side_selection: string;
  status: 'created' | 'pending' | 'running' | 'completed' | 'failed';
  found_count: number;
  notes?: string;
  created_at: string;
  updated_at: string;
  scan_source?: string;
}

export interface CreScan {
  id: number;
  scan_uid: string;
  city?: string;
  state?: string;
  main_street?: string;
  start_address?: string;
  end_address?: string;
  side: 'north' | 'south' | 'east' | 'west' | 'both';
  scan_mode: 'quick' | 'full';
  status: 'pending' | 'processing' | 'complete' | 'failed';
  created_at: string;
  updated_at: string;
  project_id?: string;
  project_name?: string;
  scan_source?: string;
}

export interface CreWorkflowExecution {
  execution_id: number;
  execution_number: string;
  project_id: number;
  property_id: number;
  scenario_id?: number;
  workflow_code: string;
  workflow_version?: string;
  devtools_execution_id?: string;
  status: 'Submitted' | 'Running' | 'Completed' | 'Failed' | 'Pending';
  priority: 'Low' | 'Normal' | 'High' | 'Critical';
  requested_by?: number;
  submitted_at: string;
  started_at?: string;
  completed_at?: string;
  retry_count: number;
  error_message?: string;
  metadata_json?: string;
  created_at: string;
  updated_at: string;
}

export interface CreWorkflowResult {
  result_id: number;
  execution_id: number;
  result_type: string;
  result_version?: string;
  response_json?: string; // stringified JSON
  normalized: number; // 0 or 1
  received_at: string;
  created_at: string;
}

export interface CreWorkflowEvent {
  event_id: number;
  execution_id: number;
  event_type: string;
  status: string;
  message?: string;
  created_at: string;
}

export interface CreRenovationScenario {
  id: number;
  project_id: string;
  property_id: number;
  renovation_type: string;
  scenario_type?: string;
  scenario_name?: string;
  rationale?: string;
  risk_level?: 'low' | 'medium' | 'high';
  estimated_complexity?: 'low' | 'medium' | 'high';
  custom_notes?: string;
  status: 'draft' | 'approved' | 'rejected';
  source?: string;
  created_at: string;
  updated_at: string;
}

export interface CrePropertyAnalysisReport {
  id: number;
  project_id: string;
  property_id: number;
  scenario_id?: number;
  estimate_low?: number;
  estimate_high?: number;
  zoning_notes?: string;
  risk_notes?: string;
  recommendation?: string;
  score?: number;
  report_json?: string; // stringified JSON
  created_at: string;
  updated_at: string;
  workflow_execution_id?: number;
  workflow_result_id?: number;
  analysis_version?: string;
  confidence_score?: number;
  workflow_status?: string;
  completed_at?: string;
}

export interface CreConceptDesign {
  id: number;
  project_id: string;
  property_id: number;
  scenario_id?: number;
  title?: string;
  concept_prompt: string;
  concept_notes?: string;
  image_reference_ids?: string; // stringified JSON
  status: 'draft' | 'under_review' | 'approved';
  created_at: string;
  updated_at: string;
  workflow_execution_id?: number;
  design_version?: string;
  approved_by?: number;
  approved_at?: string;
}

export interface CreGeneratedAsset {
  asset_id: number;
  execution_id: number;
  property_id: number;
  asset_type: 'report' | 'image' | 'pdf' | 'spreadsheet' | 'json';
  asset_category?: string;
  title?: string;
  description?: string;
  file_name: string;
  storage_path: string;
  thumbnail_path?: string;
  mime_type?: string;
  file_size?: number;
  version?: string;
  created_at: string;
}

export interface CreEstimate {
  id: number;
  property_id: number;
  scenario: 'cosmetic' | 'heavy_remodel' | 'demo_rebuild' | 'custom';
  proposed_use?: string;
  proposed_building_sqft?: number;
  proposed_units?: number;
  low_cost?: number;
  mid_cost?: number;
  high_cost?: number;
  cost_per_sqft_low?: number;
  cost_per_sqft_high?: number;
  assumptions?: string;
  risk_level: 'low' | 'medium' | 'high';
  created_at: string;
  workflow_execution_id?: number;
  estimate_source?: string;
  estimate_version?: string;
}

export interface CreZoningNote {
  id: number;
  property_id: number;
  zoning_code?: string;
  allowed_use_summary?: string;
  conditional_use_notes?: string;
  parking_notes?: string;
  entitlement_risk: 'low' | 'medium' | 'high';
  source_url?: string;
  created_at: string;
}

export interface ApiUsageLog {
  id: number;
  provider?: string;
  api_name?: string;
  endpoint?: string;
  request_count: number;
  estimated_cost?: number;
  created_at: string;
}

// User representation
export interface LoggedUser {
  name: string;
  role: string;
  email: string;
}

// Stats summary for high-level visualization
export interface CreStats {
  totalProjects: number;
  totalProperties: number;
  activeWorkflows: number;
  generatedAssetsCount: number;
  apiUsageCost: number;
}
