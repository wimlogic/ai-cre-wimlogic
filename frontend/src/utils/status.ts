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
  failed: { label: 'Failed', variant: 'error' },
  cancelled: { label: 'Cancelled', variant: 'neutral' },
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
  type: 'project' | 'property' | 'workflow'
): StatusConfig {
  if (!rawStatus) return DEFAULT_STATUS_CONFIG;
  const normalized = rawStatus.trim().toLowerCase();

  const map =
    type === 'project'
      ? PROJECT_STATUS_MAP
      : type === 'property'
        ? PROPERTY_STATUS_MAP
        : WORKFLOW_STATUS_MAP;

  return (
    map[normalized] || {
      ...DEFAULT_STATUS_CONFIG,
      label: rawStatus.charAt(0).toUpperCase() + rawStatus.slice(1),
    }
  );
}
