import { useState } from 'react';
import { Activity, RotateCcw, XCircle } from 'lucide-react';
import EnterpriseCard from './EnterpriseCard';
import StatusBadge from './StatusBadge';
import EmptyState from './EmptyState';
import ConfirmDialog from './ConfirmDialog';
import EnterpriseJobProgress, { EnterpriseJobProgressStep } from './EnterpriseJobProgress';
import EnterpriseJobTimeline, { EnterpriseJobTimelineEntry } from './EnterpriseJobTimeline';
// NOTE: imported via the explicit '../types/index' path rather than '../types'.
// A sibling legacy file, types.ts, currently shadows the types/ directory
// under the project's bundler module resolution (a pre-existing issue
// surfaced during File 2 and deferred to Phase 1C - Type Architecture
// Cleanup). Using the explicit path reaches the intended file without
// touching or renaming either types.ts or types/index.ts.
import type { EnterpriseJobClientPhase, EnterpriseJobCapabilities } from '../types/index';
import styles from './EnterpriseJobPanel.module.css';

/**
 * components/EnterpriseJobPanel.tsx
 *
 * Enterprise Job Panel - a WIMLOGIC Enterprise Component (Phase 1A).
 *
 * The composite monitor for a single WACP Enterprise Job: header (job
 * label, job number, status), the progress stepper, transient
 * polling/timeout notices, the activity timeline, and capability-gated
 * Cancel/Retry actions. It composes EnterpriseCard, StatusBadge, EmptyState,
 * ConfirmDialog, EnterpriseJobProgress, and EnterpriseJobTimeline rather
 * than reimplementing any of their presentation - this panel only adds the
 * layout that arranges them and the small amount of glue logic (resolving
 * the progress stepper's current key, gating the action buttons) that
 * doesn't belong in any single one of them.
 *
 * This component is deliberately embedded inline in a page rather than
 * shown as a modal/dialog, matching the existing two-column AI Orchestration
 * layout and avoiding a second dialog paradigm beyond ConfirmDialog (which
 * this panel still uses, for the destructive Cancel confirmation only).
 *
 * Like the components it composes, this panel carries no AI-CRE-specific
 * concepts in its props - `jobLabel` is a generic caption supplied by the
 * consuming application (AI-CRE passes its workflow_code; another WACP
 * application would pass whatever it calls its own job type), and
 * `timelineEntries` is the generic EnterpriseJobTimelineEntry[] shape, not
 * AI-CRE's WorkflowEvent. It does not poll, submit, or fetch anything
 * itself - all data and actions are passed in as props, so any WACP
 * Business Application can drive this same panel from its own hook/state
 * without modification.
 *
 * Cancel/Retry (approved decision D1): both actions are capability-gated.
 * `capabilities.canCancel` / `capabilities.canRetry` default to false, and
 * when false the corresponding control is not rendered at all (cleanly
 * hidden, not a permanently-disabled dead button). This panel never calls
 * WACP directly and never invents cancel/retry behavior - it only renders
 * the controls and defers to `onCancel` / `onRetry` callbacks supplied by
 * the page, which remain no-ops until the AI-CRE backend exposes the
 * corresponding endpoints.
 */

/** Resolves which EnterpriseJobProgress step key currently applies, given the client phase and the verbatim backend status. */
function resolveProgressKey(clientPhase: EnterpriseJobClientPhase, status: string | null | undefined): string {
  switch (clientPhase) {
    case 'Preparing':
    case 'Submitting':
      return clientPhase;
    case 'ProcessingResults':
      return 'ProcessingResults';
    case 'Done':
      return 'Completed';
    case 'Polling':
    case 'Idle':
    default:
      return status || clientPhase;
  }
}

export interface EnterpriseJobPanelProps {
  /** Backend execution id of the job being monitored. Null renders an idle empty state instead of a monitor. */
  executionId: number | null;
  /** Human-readable job number/reference (e.g. AI-CRE's execution_number). */
  executionNumber?: string;
  /** Generic caption for the kind of job being run (e.g. a workflow code). Never a hardcoded business term. */
  jobLabel?: string;
  /** Verbatim backend status ("Pending", "Running", "Completed", "Failed", "Cancelled", etc.), or undefined before the first poll response. */
  status?: string | null;
  /** Client-owned lifecycle phase layered on top of `status` (see types/index.ts). */
  clientPhase: EnterpriseJobClientPhase;
  /** True while the polling loop is actively scheduled. */
  isPolling?: boolean;
  /** True while polling is paused (tab hidden or offline) - see useEnterpriseJobPolling. */
  isPaused?: boolean;
  /** True once the polling timeout has elapsed without reaching a terminal status. */
  timedOut?: boolean;
  /** Enterprise-friendly transient error surfaced by the polling loop after repeated failures, or null. */
  pollError?: string | null;
  /** Backend-side error detail for a Failed job (e.g. WorkflowExecution.error_message). */
  errorMessage?: string | null;
  /** Optional override of the default progress step sequence. */
  progressSteps?: EnterpriseJobProgressStep[];
  /** Timeline entries, oldest first. */
  timelineEntries: EnterpriseJobTimelineEntry[];
  isTimelineLoading?: boolean;
  /** Cancel/Retry availability. Both default to false (hidden) per approved decision D1. */
  capabilities?: EnterpriseJobCapabilities;
  onCancel?: () => void;
  onRetry?: () => void;
  isCancelling?: boolean;
  isRetrying?: boolean;
  id?: string;
}

const DEFAULT_CAPABILITIES: EnterpriseJobCapabilities = { canCancel: false, canRetry: false };

export default function EnterpriseJobPanel({
  executionId,
  executionNumber,
  jobLabel,
  status,
  clientPhase,
  isPolling = false,
  isPaused = false,
  timedOut = false,
  pollError = null,
  errorMessage = null,
  progressSteps,
  timelineEntries,
  isTimelineLoading = false,
  capabilities = DEFAULT_CAPABILITIES,
  onCancel,
  onRetry,
  isCancelling = false,
  isRetrying = false,
  id,
}: EnterpriseJobPanelProps) {
  const [isCancelConfirmOpen, setIsCancelConfirmOpen] = useState(false);

  if (executionId === null) {
    return (
      <EnterpriseCard id={id || 'enterprise-job-panel'}>
        <EmptyState
          icon={Activity}
          title="No Active Job"
          description="Submit a job to begin monitoring its progress here."
        />
      </EnterpriseCard>
    );
  }

  const normalizedStatus = (status || '').trim().toLowerCase();
  const isFailed = normalizedStatus === 'failed';
  const isCancelled = normalizedStatus === 'cancelled';
  const progressCurrentKey = resolveProgressKey(clientPhase, status);

  const showCancel = capabilities.canCancel && Boolean(onCancel);
  const showRetry = capabilities.canRetry && isFailed && Boolean(onRetry);

  return (
    <EnterpriseCard
      id={id || 'enterprise-job-panel'}
      title={jobLabel || 'Enterprise Job'}
      subtitle={executionNumber ? `Job ${executionNumber}` : `Execution #${executionId}`}
      headerAction={<StatusBadge status={status || clientPhase} type="workflow" />}
    >
      <div className={styles.body}>
        <EnterpriseJobProgress
          steps={progressSteps}
          currentKey={progressCurrentKey}
          isFailed={isFailed}
          isCancelled={isCancelled}
          terminalMessage={isFailed ? errorMessage || undefined : undefined}
        />

        {isPaused && (
          <div className={`${styles.notice} ${styles.noticeInfo}`}>
            Monitoring paused - will resume automatically when this tab is active and online.
          </div>
        )}

        {pollError && (
          <div className={`${styles.notice} ${styles.noticeWarning}`}>{pollError}</div>
        )}

        {timedOut && (
          <div className={`${styles.notice} ${styles.noticeWarning}`}>
            Automatic monitoring stopped after 15 minutes without a final status. The job may
            still be running on the backend - refresh to check again.
          </div>
        )}

        <div>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Activity Timeline</span>
            {isPolling && !isPaused && (
              <span className={styles.liveIndicator}>
                <span className={styles.liveDot} />
                Live
              </span>
            )}
          </div>
          <EnterpriseJobTimeline entries={timelineEntries} isLoading={isTimelineLoading} />
        </div>

        {(showCancel || showRetry) && (
          <div className={styles.actions}>
            {showCancel && (
              <button
                type="button"
                onClick={() => setIsCancelConfirmOpen(true)}
                disabled={isCancelling}
                className={`enterprise-btn enterprise-btn-secondary ${isCancelling ? 'enterprise-btn-loading' : ''}`}
                id={id ? `${id}-cancel-btn` : 'enterprise-job-panel-cancel-btn'}
              >
                <XCircle className={styles.actionIcon} />
                Cancel Job
              </button>
            )}
            {showRetry && (
              <button
                type="button"
                onClick={onRetry}
                disabled={isRetrying}
                className={`enterprise-btn enterprise-btn-primary ${isRetrying ? 'enterprise-btn-loading' : ''}`}
                id={id ? `${id}-retry-btn` : 'enterprise-job-panel-retry-btn'}
              >
                <RotateCcw className={styles.actionIcon} />
                Retry Job
              </button>
            )}
          </div>
        )}
      </div>

      <ConfirmDialog
        isOpen={isCancelConfirmOpen}
        title="Cancel this job?"
        message="This will request cancellation of the running Enterprise Job. This action cannot be undone."
        confirmLabel="Cancel Job"
        cancelLabel="Keep Running"
        isDanger
        onCancel={() => setIsCancelConfirmOpen(false)}
        onConfirm={() => {
          setIsCancelConfirmOpen(false);
          onCancel?.();
        }}
        id={id ? `${id}-cancel-confirm` : 'enterprise-job-panel-cancel-confirm'}
      />
    </EnterpriseCard>
  );
}
