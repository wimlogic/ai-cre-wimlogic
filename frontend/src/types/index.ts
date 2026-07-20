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
  ai_prompt?: string | null;
  tags?: string[] | null;
  constraints?: string | null;
  priority?: number | null;
  is_primary: number;
  status?: string;
  is_deleted: number;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Design Studio types (Home Studio Frontend Checkpoint 1)
//
// Field-for-field verified against the actual ai_cre_schema.sql table
// definitions (cre_design_tools, cre_design_tool_options,
// cre_design_tool_image_requirements, cre_design_jobs,
// cre_design_job_images, cre_design_job_executions) - not assumed from
// convention. workflow_code is kept on DesignTool/DesignJob because the
// backend record has it, but Home Studio's UI must never render it -
// that constraint lives in the UI layer, not the type.
// ---------------------------------------------------------------------------

export interface DesignTool {
  id: number;
  tool_code: string;
  tool_name: string;
  design_type: string;
  workflow_code: string; // internal only - never rendered in Home Studio
  card_image_path?: string | null;
  icon_code?: string | null;
  business_description?: string | null;
  business_purpose?: string | null;
  business_instructions?: string | null;
  input_config_json?: Record<string, unknown> | null;
  output_expectations_json?: Record<string, unknown> | null;
  status: string; // active | inactive | archived
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface DesignToolOption {
  id: number;
  tool_id: number;
  option_code: string;
  option_label: string;
  /**
   * Intentionally a plain string, not a closed union - the backend
   * defines option_type as str precisely so future business option
   * types can be introduced without an API schema change. Future UI
   * rendering may explicitly support the six current known values
   * (select, multiselect, boolean, number, text, slider) and show a
   * controlled unsupported-type state for anything else, but the type
   * itself must not constrain the API response.
   */
  option_type: string;
  allowed_values_json?: any[] | null;
  default_value?: string | null;
  is_required: number;
  display_order: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface DesignToolImageRequirement {
  id: number;
  tool_id: number;
  /**
   * Business-defined, extensible value (not a closed enum) - the backend
   * treats input_role as free business vocabulary a Tool can define, not
   * a fixed set the frontend should constrain.
   */
  input_role: string;
  allowed_image_roles_json?: string[] | null;
  min_count: number;
  max_count?: number | null;
  display_order: number;
  created_at: string;
  updated_at: string;
}

/** Known Design Job lifecycle values (cre_design_jobs.status CHECK constraint). */
export type DesignJobStatus = 'draft' | 'submitted' | 'processing' | 'completed' | 'failed' | 'cancelled';

export interface DesignJob {
  id: number;
  job_number: string;
  project_id: string;
  property_id: number;
  tool_id: number;
  tool_code: string;
  design_type: string;
  workflow_code: string; // internal only - never rendered in Home Studio
  tool_options_json?: Record<string, any> | null;
  effective_context_json?: Record<string, any> | null;
  submitted_payload_json?: Record<string, any> | null;
  status: DesignJobStatus;
  requested_by?: number | null;
  created_at: string;
  updated_at: string;
}

export interface DesignJobImage {
  id: number;
  design_job_id: number;
  property_image_id: number;
  /** Same extensible business vocabulary as DesignToolImageRequirement.input_role. */
  input_role: string;
  image_knowledge_snapshot_json?: Record<string, any> | null;
  display_order: number;
  created_at: string;
}

export interface DesignJobExecution {
  id: number;
  design_job_id: number;
  workflow_execution_id: number;
  attempt_number: number;
  is_current: number;
  created_at: string;
}

/** Matches the backend's DesignJobSubmitResponse / DesignJobRetryResponse shape. */
export interface DesignJobAttemptResponse {
  design_job_id: number;
  attempt_number: number;
  workflow_execution_id: number;
  devtools_execution_id?: string | null;
  status: string; // verbatim cre_workflow_executions.status
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
  result_sync_error?: string;
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
