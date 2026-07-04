export interface Project {
  id: number;
  project_id: string; // PRJ001 etc
  project_name: string;
  description?: string;
  status: string; // active, completed, etc.
  default_city?: string;
  default_state?: string;
  main_street?: string;
  beginning_address?: string;
  ending_address?: string;
  side?: string;
  scan_mode?: string;
  created_at: string;
  updated_at: string;
}

export interface Property {
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
  street_number?: string;
  street_name?: string;
  side_of_street?: string;
  phase2_source?: string;
  display_address?: string;
  status?: string;
  source?: string;
  notes?: string;
  confidence_score?: string;
  raw_api_json?: string;
  api_source_url?: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectProperty {
  id: number;
  project_id: string;
  property_id: number;
  scan_id?: string;
  role?: string;
  selected: number;
  created_at: string;
}

export interface PropertyImage {
  id: number;
  property_id: number;
  image_type: string;
  image_url?: string;
  provider?: string;
  heading?: number;
  pitch?: number;
  fov?: number;
  cached_path?: string;
  last_checked_at?: string;
  project_id?: string;
  original_file_name?: string;
  file_size?: number;
  file_type?: string;
  image_role?: string;
  notes?: string;
  status?: string;
  is_deleted: number;
  created_at: string;
}

export interface WorkflowExecution {
  execution_id: number;
  execution_number: string;
  project_id: number;
  property_id: number;
  scenario_id?: number;
  workflow_code: string;
  workflow_version?: string;
  devtools_execution_id?: string;
  status: string; // Pending, Running, Completed, Failed
  priority: string; // Normal, High, Low
  requested_by?: number;
  started_at?: string;
  completed_at?: string;
  retry_count: number;
  error_message?: string;
  metadata_json?: Record<string, any>;
  submitted_at: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowEvent {
  event_id: number;
  execution_id: number;
  event_type: string;
  status: string;
  message: string;
  created_at: string;
}

export interface WorkflowResult {
  result_id: number;
  execution_id: number;
  result_type: string;
  result_version?: string;
  response_json?: string; // JSON String
  normalized: number;
  received_at: string;
  created_at: string;
}

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

export interface GeneratedAsset {
  asset_id: number;
  execution_id: number;
  property_id: number;
  asset_type: string;
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

export interface ListResponse<T> {
  count: number;
  items: T[];
}
