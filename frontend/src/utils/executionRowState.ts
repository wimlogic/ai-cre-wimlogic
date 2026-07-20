import { WorkflowExecution } from '../types/index';

/**
 * utils/executionRowState.ts
 *
 * Phase 2A - pure, unit-testable resolution of "what should this one
 * Execution History row show" per the approved state matrix. Exactly
 * the four row-level actions named in the required correction:
 * View Progress, View Error, Retry Sync, View Report. "Run New Analysis"
 * is deliberately NOT one of these - it is a property-level action
 * (Phase 2B's PropertyRunAnalysisPanel), never rendered per history row.
 *
 * KNOWN LIMITATION (found during this phase, out of scope to fix here
 * since this task is frontend-only): a WACP-level rejection at
 * submission time (e.g. WORKFLOW_NOT_FOUND) does not currently update
 * WorkflowExecution.status at all - confirmed directly against
 * ai_orchestration_service.py's dispatch_via_wacp() and the
 * /ai-orchestration/submit route, both of which only log an ERROR-type
 * WorkflowEvent and re-raise, never writing a terminal status back to
 * the execution row. A rejected submission is therefore
 * indistinguishable, from this data alone, from a genuinely still-
 * pending one. This function does not attempt to guess via a time-based
 * heuristic (e.g. "Pending for over N minutes") - that would be an
 * unverified assumption dressed up as a real state. It surfaces
 * Pending/Queued honestly as "in progress" and defers a real fix to a
 * backend change explicitly outside this phase's approved scope.
 */

export type ExecutionRowAction = 'view_progress' | 'view_error' | 'retry_sync' | 'view_report';

export interface ExecutionRowState {
  action: ExecutionRowAction;
  label: string;
  /** Visual treatment - not the exact backend status string, since
   * e.g. both Failed and Cancelled render as the same "unsuccessful"
   * tone even though their labels differ. */
  tone: 'progress' | 'success' | 'warning' | 'error';
}

const IN_PROGRESS_STATUSES = new Set(['Pending', 'Queued', 'Running']);

export function resolveExecutionRowState(
  execution: WorkflowExecution,
  executionIdsWithReports: Set<number>
): ExecutionRowState {
  const status = execution.status;

  if (IN_PROGRESS_STATUSES.has(status)) {
    return { action: 'view_progress', label: 'View Progress', tone: 'progress' };
  }

  if (status === 'Completed') {
    const hasReport = executionIdsWithReports.has(execution.execution_id);
    const syncFailed = Boolean(execution.result_sync_error);
    if (hasReport && !syncFailed) {
      return { action: 'view_report', label: 'View Report', tone: 'success' };
    }
    // Completed remotely but no report row exists yet, or a sync error
    // is recorded - never rendered as if a report exists.
    return { action: 'retry_sync', label: 'Retry Sync', tone: 'warning' };
  }

  // Failed / Cancelled / anything else terminal-but-unsuccessful.
  return { action: 'view_error', label: 'View Error', tone: 'error' };
}
