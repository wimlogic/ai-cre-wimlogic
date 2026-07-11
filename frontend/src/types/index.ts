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

// ---------------------------------------------------------------------------
// Enterprise Job types (Phase 1A - WACP frontend integration)
//
// These describe the frontend's view of a workflow execution while it is
// being monitored (submitted, polled, completed). They do not replace or
// duplicate WorkflowExecution above - WorkflowExecution is the backend
// record shape; the types below are the client-side monitoring layer built
// on top of it. Backend status strings (WorkflowExecution.status) are
// rendered verbatim throughout - "Pending", "Running", "Completed", "Failed",
// "Cancelled" - per the approved decision that the frontend renders backend
// truth rather than reinterpreting it (see utils/status.ts WORKFLOW_STATUS_MAP,
// which is the single source of label/variant mapping for these statuses).
// ---------------------------------------------------------------------------

/**
 * Client-side lifecycle phase for the Enterprise Job monitor. These phases
 * are owned entirely by the frontend - the brief moment before a job is
 * submitted, and the brief moment after a terminal backend status while
 * results/sections/assets are being refetched. They are layered on top of,
 * and never substitute for, the backend's own status string.
 */
export type EnterpriseJobClientPhase =
  | 'Idle'
  | 'Preparing'
  | 'Submitting'
  | 'Polling'
  | 'ProcessingResults'
  | 'Done';

/**
 * Snapshot of an Enterprise Job as tracked by the frontend: the subset of
 * WorkflowExecution fields relevant to monitoring, plus the client-only
 * phase. `status` is the verbatim backend value and is the only status ever
 * shown to the user.
 */
export interface EnterpriseJobState {
  executionId: number;
  executionNumber: string;
  status: string;
  clientPhase: EnterpriseJobClientPhase;
  workflowCode: string;
  priority: string;
  submittedAt?: string;
  startedAt?: string;
  completedAt?: string;
  retryCount: number;
  errorMessage?: string;
}

/**
 * Backend-exposed action availability for a given job. Both flags default
 * to false and stay false until the AI-CRE backend exposes cancel/retry
 * endpoints (approved decision D1). The UI reads these flags to hide or
 * disable the corresponding controls, so enabling the actions later is a
 * capability-flag change rather than a UI rewrite, and the frontend never
 * calls WACP or invents cancel/retry behavior on its own.
 */
export interface EnterpriseJobCapabilities {
  canCancel: boolean;
  canRetry: boolean;
}

/**
 * Payload accepted by the Enterprise Job submission flow. Mirrors
 * WorkflowSubmitPayload in services/workflowService.ts field-for-field;
 * duplicated here rather than imported because services/ import from
 * types/, never the reverse.
 */
export interface EnterpriseJobSubmitPayload {
  project_id: number;
  property_id: number;
  workflow_code: string;
  scenario_id?: number;
  priority?: string;
  metadata_json?: Record<string, any>;
}

/**
 * Emitted once when a tracked job reaches a terminal backend status
 * (Completed, Failed, or Cancelled). Subscribers - Workflow Results,
 * Generated Assets, and future modules - react to this event instead of
 * each implementing independent polling or refresh logic.
 */
export interface EnterpriseJobCompletedEvent {
  executionId: number;
  status: string;
  succeeded: boolean;
}

/**
 * Subscriber callback signature used by the Enterprise Job completion
 * notification pattern (EnterpriseJobContext).
 */
export type EnterpriseJobCompletedListener = (event: EnterpriseJobCompletedEvent) => void;
