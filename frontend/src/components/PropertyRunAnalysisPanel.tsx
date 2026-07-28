import { useState, useEffect } from 'react';
import EnterpriseJobPanel from './EnterpriseJobPanel';
import BusinessIntentCheckboxes, { ALL_BUSINESS_INTENTS } from './BusinessIntentCheckboxes';
import useEnterpriseJobPolling from '../hooks/useEnterpriseJobPolling';
import { isTerminalWorkflowStatus } from '../utils/status';
import { resolveExecutionRowState } from '../utils/executionRowState';
import { workflowService } from '../services/workflowService';
import { WorkflowExecution } from '../types/index';
import { AlertCircle, CheckCircle2 } from 'lucide-react';
import styles from './PropertyRunAnalysisPanel.module.css';

/**
 * components/PropertyRunAnalysisPanel.tsx
 *
 * Phase 2B. Owns the "Current Analysis" section of a Property's Reports
 * tab - submission, live monitoring (via the existing, unmodified
 * EnterpriseJobPanel + useEnterpriseJobPolling), and the post-completion
 * summary. Reuses resolveExecutionRowState (Phase 2A) for the SAME
 * state resolution Execution History uses, so the two can never
 * disagree about what a given execution's state means.
 *
 * Binding rules enforced here:
 * - Completed status alone never implies View Report is available -
 *   delegated entirely to resolveExecutionRowState, which already
 *   checks executionIdsWithReports + result_sync_error.
 * - Result-sync failure exposes Retry Sync ONLY - never "Run New
 *   Analysis" alongside it - Retry Sync calls the existing status-check
 *   endpoint only, never workflowService.submit().
 * - Queued/Running hide "Run New Analysis" entirely.
 * - Completed (successfully) KEEPS "Run New Analysis" available
 *   alongside the summary - never replaced.
 * - No timing heuristic is used to infer a "Rejected" state - a
 *   Pending/Queued execution is rendered as in-progress, honestly,
 *   per the documented backend limitation (see the separate defect
 *   note in this phase's delivery).
 */

export interface PropertyRunAnalysisPanelProps {
  propertyId: number;
  projectId: number;
  currentExecution: WorkflowExecution | null;
  executionIdsWithReports: Set<number>;
  isLoading: boolean;
  onReload: () => Promise<void>;
  onViewReport: (execution: WorkflowExecution) => void;
}

export default function PropertyRunAnalysisPanel({
  propertyId,
  projectId,
  currentExecution,
  executionIdsWithReports,
  isLoading,
  onReload,
  onViewReport,
}: PropertyRunAnalysisPanelProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRetryingSync, setIsRetryingSync] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [selectedAdditionalIntents, setSelectedAdditionalIntents] = useState<Set<string>>(new Set(['PROPERTY_ANALYSIS']));

  const toggleAdditionalIntent = (intent: string) => {
    setSelectedAdditionalIntents((prev) => {
      const next = new Set(prev);
      if (next.has(intent)) next.delete(intent);
      else next.add(intent);
      return next;
    });
  };

  const {
    status: pollStatus,
    isPolling,
    isPaused,
    timedOut,
    error: pollError,
    start: startPolling,
  } = useEnterpriseJobPolling({
    onTerminal: async () => {
      await onReload();
    },
  });

  // Resume monitoring on mount if the latest execution was left
  // non-terminal - the actual fix for the original "loses context on
  // navigation" problem this whole redesign exists to solve. Runs once
  // per distinct execution_id, not on every render.
  useEffect(() => {
    if (currentExecution && !isTerminalWorkflowStatus(currentExecution.status)) {
      startPolling(currentExecution.execution_id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentExecution?.execution_id]);

  const handleRunAnalysis = async () => {
    // The Business Intent checkbox UI already disables the trigger
    // button when nothing is selected; this is the same guard applied
    // defensively here too, so this function can never be called with
    // an empty selection regardless of how it's invoked.
    const selectedInOrder = ALL_BUSINESS_INTENTS.filter((intent) => selectedAdditionalIntents.has(intent));
    if (selectedInOrder.length === 0) {
      setSubmitError('Select at least one Business Intent to run an analysis.');
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);
    try {
      // The first selected intent, in the fixed presentation order
      // (regardless of click order), becomes the primary WACP
      // business_intent; the rest become additional_business_intents.
      // workflow_code stays AIHOME's own local pipeline categorization,
      // unchanged, decoupled from which intent(s) are actually
      // requested from DEV-TOOLS.
      const [primaryIntent, ...additionalIntents] = selectedInOrder;
      const exec = await workflowService.submit({
        project_id: projectId,
        property_id: propertyId,
        workflow_code: 'ZONING_ANALYSIS',
        business_intent: primaryIntent,
        ...(additionalIntents.length > 0 ? { additional_business_intents: additionalIntents } : {}),
      });
      setSelectedAdditionalIntents(new Set(['PROPERTY_ANALYSIS']));
      await onReload();
      startPolling(exec.execution_id);
    } catch (err) {
      console.error('[PropertyRunAnalysisPanel] Failed to submit analysis:', err);
      setSubmitError('Could not start a new analysis. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  /** Retries result synchronization ONLY - calls the exact same status-
   * check endpoint the polling loop already uses. Never calls
   * workflowService.submit(); the underlying workflow already succeeded
   * remotely and does not need to be re-run. */
  const handleRetrySync = async () => {
    if (!currentExecution) return;
    setIsRetryingSync(true);
    try {
      await workflowService.checkStatus(currentExecution.execution_id);
      await onReload();
    } catch (err) {
      console.error('[PropertyRunAnalysisPanel] Retry sync failed:', err);
    } finally {
      setIsRetryingSync(false);
    }
  };

  const renderIntentCheckboxes = () => (
    <BusinessIntentCheckboxes
      selected={selectedAdditionalIntents}
      onToggle={toggleAdditionalIntent}
      disabled={isSubmitting}
    />
  );

  if (isLoading) {
    return <div className={styles.loading}>Loading current analysis...</div>;
  }

  // No execution has ever been run for this property.
  if (!currentExecution) {
    return (
      <div className={styles.panel}>
        <p className={styles.emptyText}>No analysis has been run yet for this property.</p>
        {renderIntentCheckboxes()}
        <button
          type="button"
          className={styles.runButton}
          onClick={handleRunAnalysis}
          disabled={isSubmitting || selectedAdditionalIntents.size === 0}
          id="run-new-analysis-button"
        >
          {isSubmitting ? 'Starting...' : 'Run New Analysis'}
        </button>
        {submitError && <p className={styles.errorText}>{submitError}</p>}
      </div>
    );
  }

  const rowState = resolveExecutionRowState(currentExecution, executionIdsWithReports);
  const inProgress = rowState.action === 'view_progress';
  const syncFailed = rowState.action === 'retry_sync';

  return (
    <div className={styles.panel}>
      {inProgress ? (
        // Queued/Running - Run New Analysis is deliberately NOT rendered
        // at all here, per the binding rule.
        <EnterpriseJobPanel
          id="property-run-analysis-job-panel"
          executionId={currentExecution.execution_id}
          executionNumber={currentExecution.execution_number}
          jobLabel={currentExecution.workflow_code}
          status={pollStatus || currentExecution.status}
          clientPhase={isPolling ? 'Polling' : 'Idle'}
          isPolling={isPolling}
          isPaused={isPaused}
          timedOut={timedOut}
          pollError={pollError}
          timelineEntries={[]}
        />
      ) : (
        <>
          <div className={styles.currentAnalysisCard} data-tone={rowState.tone}>
            <div className={styles.cardHeader}>
              {rowState.tone === 'success' ? (
                <CheckCircle2 className={styles.cardIcon} />
              ) : (
                <AlertCircle className={styles.cardIcon} />
              )}
              <span className={styles.cardStatus}>{currentExecution.status}</span>
              {currentExecution.completed_at && (
                <span className={styles.cardTime}>
                  {new Date(currentExecution.completed_at).toLocaleString(undefined, {
                    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
                  })}
                </span>
              )}
            </div>

            {syncFailed && (
              <p className={styles.syncErrorText}>
                DEV-TOOLS completed this workflow, but AI-CRE could not retrieve or process the
                result{currentExecution.result_sync_error ? `: ${currentExecution.result_sync_error}` : '.'}
              </p>
            )}
            {rowState.action === 'view_error' && currentExecution.error_message && (
              <p className={styles.errorText}>{currentExecution.error_message}</p>
            )}

            <div className={styles.cardActions}>
              {rowState.action === 'view_report' && (
                <button type="button" className={styles.viewReportButton} onClick={() => onViewReport(currentExecution)}>
                  View Report
                </button>
              )}
              {syncFailed && (
                <button
                  type="button"
                  className={styles.retrySyncButton}
                  onClick={handleRetrySync}
                  disabled={isRetryingSync}
                >
                  {isRetryingSync ? 'Retrying...' : 'Retry Sync'}
                </button>
              )}
            </div>
          </div>

          {/* Completed/Failed/Cancelled all keep Run New Analysis available -
              only Queued/Running (handled above) and sync-failure hide or
              replace it. Sync-failure offers Retry Sync only, per the
              binding rule - Run New Analysis is intentionally NOT rendered
              in that branch. */}
          {!syncFailed && (
            <>
              {renderIntentCheckboxes()}
              <button
                type="button"
                className={styles.runButton}
                onClick={handleRunAnalysis}
                disabled={isSubmitting || selectedAdditionalIntents.size === 0}
                id="run-new-analysis-button"
              >
                {isSubmitting ? 'Starting...' : 'Run New Analysis'}
              </button>
            </>
          )}
          {submitError && <p className={styles.errorText}>{submitError}</p>}
        </>
      )}
    </div>
  );
}
