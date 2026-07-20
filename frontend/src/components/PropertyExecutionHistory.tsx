import { WorkflowExecution } from '../types/index';
import { resolveExecutionRowState } from '../utils/executionRowState';
import EmptyState from './EmptyState';
import { History, Loader2, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';
import styles from './PropertyExecutionHistory.module.css';

/**
 * components/PropertyExecutionHistory.tsx
 *
 * Phase 2A. Every execution ever attempted for one property, regardless
 * of outcome - sourced from GET /workflow-executions/?property_id=X
 * (already correctly ordered newest-first server-side; re-sorted
 * defensively client-side by the shared hook). This is the ONLY
 * property-scoped view that includes Failed/Cancelled/in-progress rows;
 * PropertyReportHistory (a separate component) never does.
 */

const TONE_ICON = { progress: Loader2, success: CheckCircle2, warning: AlertTriangle, error: XCircle };

export interface PropertyExecutionHistoryProps {
  executions: WorkflowExecution[];
  executionIdsWithReports: Set<number>;
  isLoading: boolean;
  onViewProgress: (execution: WorkflowExecution) => void;
  onViewError: (execution: WorkflowExecution) => void;
  onRetrySync: (execution: WorkflowExecution) => void;
  onViewReport: (execution: WorkflowExecution) => void;
}

export default function PropertyExecutionHistory({
  executions,
  executionIdsWithReports,
  isLoading,
  onViewProgress,
  onViewError,
  onRetrySync,
  onViewReport,
}: PropertyExecutionHistoryProps) {
  if (isLoading) {
    return <div className={styles.loading}>Loading execution history...</div>;
  }

  if (executions.length === 0) {
    return (
      <EmptyState
        icon={History}
        title="No Executions Yet"
        description="Analyses run for this property will appear here, including any that did not complete successfully."
      />
    );
  }

  return (
    <div className={styles.list} id="property-execution-history">
      {executions.map((execution) => {
        const rowState = resolveExecutionRowState(execution, executionIdsWithReports);
        const ToneIcon = TONE_ICON[rowState.tone];
        const handleAction = () => {
          switch (rowState.action) {
            case 'view_progress': return onViewProgress(execution);
            case 'view_error': return onViewError(execution);
            case 'retry_sync': return onRetrySync(execution);
            case 'view_report': return onViewReport(execution);
          }
        };
        return (
          <div key={execution.execution_id} className={styles.row} data-tone={rowState.tone}>
            <ToneIcon className={`${styles.toneIcon} ${rowState.tone === 'progress' ? styles.spin : ''}`} />
            <div className={styles.rowMain}>
              <span className={styles.status}>{execution.status}</span>
              <span className={styles.date}>
                {new Date(execution.created_at).toLocaleString(undefined, {
                  month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit',
                })}
              </span>
            </div>
            <button type="button" className={styles.actionButton} onClick={handleAction}>
              {rowState.label}
            </button>
          </div>
        );
      })}
    </div>
  );
}
