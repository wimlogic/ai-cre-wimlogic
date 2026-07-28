/**
 * Enterprise status configuration and mapping utilities for the WIMLOGIC app.
 *
 * This module only maps a raw backend status string to a business label and
 * a semantic variant. Presentation (colors, dots, borders) lives in
 * StatusBadge's own CSS Module, driven by tokens.css - keeping this file
 * framework/styling-agnostic.
 */

export type StatusVariant = 'success' | 'warning' | 'error' | 'info' | 'neutral' | 'primary';

export interface StatusConfig {
  label: string;
  variant: StatusVariant;
}

const DEFAULT_STATUS_CONFIG: StatusConfig = {
  label: 'Unknown',
  variant: 'neutral',
};

/**
 * Enterprise maps for various statuses used in the platform
 */
export const PROJECT_STATUS_MAP: Record<string, StatusConfig> = {
  active: { label: 'Active', variant: 'success' },
  pipeline: { label: 'Pipeline', variant: 'info' },
  completed: { label: 'Completed', variant: 'neutral' },
  on_hold: { label: 'On Hold', variant: 'warning' },
  archived: { label: 'Archived', variant: 'neutral' },
};

export const PROPERTY_STATUS_MAP: Record<string, StatusConfig> = {
  listed: { label: 'Listed', variant: 'success' },
  under_contract: { label: 'Under Contract', variant: 'warning' },
  sold: { label: 'Sold', variant: 'neutral' },
  leased: { label: 'Leased', variant: 'info' },
  draft: { label: 'Draft', variant: 'neutral' },
};

/**
 * Workflow execution status map.
 *
 * These keys are the AI-CRE backend's actual local execution statuses
 * (see app/services/ai_orchestration_service.py and
 * app/services/workflow_execution_service.py), which is intentionally the
 * only vocabulary the frontend renders - it is faithful to backend truth
 * rather than reinterpreted into a separate frontend-invented vocabulary
 * (e.g. "Pending" is never relabeled as "Queued" here).
 *
 * 'queued' and 'cancelled' are included ahead of current backend emission
 * so that a future WACP-driven status addition on the backend is picked up
 * automatically by this existing map, with no frontend code change
 * required. 'succeeded' is retained for backward compatibility with any
 * historical records, though the backend's terminal-success status is
 * 'Completed'.
 */
export const WORKFLOW_STATUS_MAP: Record<string, StatusConfig> = {
  pending: { label: 'Pending', variant: 'neutral' },
  queued: { label: 'Queued', variant: 'info' },
  running: { label: 'Running', variant: 'primary' },
  completed: { label: 'Completed', variant: 'success' },
  succeeded: { label: 'Succeeded', variant: 'success' },
  // WIM Module V2 terminal SUCCESS state (COMPLETED_WITH_WARNINGS) - a
  // job that finished successfully but with non-fatal warnings. Warning-
  // toned (amber), never error-toned (red): the job did NOT fail.
  'completed with warnings': { label: 'Completed with Warnings', variant: 'warning' },
  failed: { label: 'Failed', variant: 'error' },
  cancelled: { label: 'Cancelled', variant: 'neutral' },
};

/**
 * Design Job status map (Home Studio Frontend Checkpoint 1).
 *
 * These keys are cre_design_jobs.status's own CHECK-constrained
 * vocabulary (draft, submitted, processing, completed, failed,
 * cancelled) - a distinct lifecycle from WORKFLOW_STATUS_MAP above,
 * which describes a single runtime cre_workflow_executions attempt.
 * A Design Job's status reflects the JOB (which may span multiple
 * execution attempts via Retry), not any one attempt's runtime state.
 */
export const DESIGN_JOB_STATUS_MAP: Record<string, StatusConfig> = {
  draft: { label: 'Draft', variant: 'neutral' },
  submitted: { label: 'Submitted', variant: 'info' },
  processing: { label: 'Processing', variant: 'primary' },
  completed: { label: 'Completed', variant: 'success' },
  failed: { label: 'Failed', variant: 'error' },
  cancelled: { label: 'Cancelled', variant: 'neutral' },
};

/**
 * AIHOME Result Rendering Framework — severity vs. confidence.
 *
 * These two maps use the SAME words ("Low", "Medium", "High") for
 * opposite semantic meanings, so they are deliberately kept separate
 * rather than sharing one map: a "Low" RISK is good news (green), while
 * "Low" CONFIDENCE is a caution about the assessment itself, not a
 * finding of severity - it always renders neutral, never colored as if
 * it were a risk level. Consumers must pick the correct type; there is
 * no shared "Low" entry that could accidentally apply the wrong tone.
 */
export const SEVERITY_STATUS_MAP: Record<string, StatusConfig> = {
  critical: { label: 'Critical', variant: 'error' },
  high: { label: 'High', variant: 'error' },
  medium: { label: 'Medium', variant: 'warning' },
  low: { label: 'Low', variant: 'success' },
};

export const CONFIDENCE_STATUS_MAP: Record<string, StatusConfig> = {
  high: { label: 'High Confidence', variant: 'neutral' },
  medium: { label: 'Medium Confidence', variant: 'neutral' },
  low: { label: 'Low Confidence', variant: 'neutral' },
};

/**
 * Backend workflow execution statuses that represent a terminal state - no
 * further transitions occur and polling should stop. Kept alongside the
 * status map since both describe the same backend vocabulary; consumers
 * (e.g. the Enterprise Job polling hook) should use this helper rather than
 * re-declaring their own terminal-status list.
 */
const WORKFLOW_TERMINAL_STATUSES = new Set(['completed', 'succeeded', 'failed', 'cancelled']);

/**
 * Returns true if the given raw workflow status string is a terminal
 * backend status (Completed, Succeeded, Failed, or Cancelled).
 */
export function isTerminalWorkflowStatus(rawStatus: string | undefined | null): boolean {
  if (!rawStatus) return false;
  return WORKFLOW_TERMINAL_STATUSES.has(rawStatus.trim().toLowerCase());
}

/**
 * Gets a unified status configuration for any raw string status
 */
export function getStatusConfig(
  rawStatus: string | undefined | null,
  type: 'project' | 'property' | 'workflow' | 'designJob' | 'severity' | 'confidence'
): StatusConfig {
  if (!rawStatus) return DEFAULT_STATUS_CONFIG;
  const normalized = rawStatus.trim().toLowerCase();

  const map =
    type === 'project'
      ? PROJECT_STATUS_MAP
      : type === 'property'
        ? PROPERTY_STATUS_MAP
        : type === 'designJob'
          ? DESIGN_JOB_STATUS_MAP
          : type === 'severity'
            ? SEVERITY_STATUS_MAP
            : type === 'confidence'
              ? CONFIDENCE_STATUS_MAP
              : WORKFLOW_STATUS_MAP;

  return (
    map[normalized] || {
      ...DEFAULT_STATUS_CONFIG,
      label: rawStatus.charAt(0).toUpperCase() + rawStatus.slice(1),
    }
  );
}
