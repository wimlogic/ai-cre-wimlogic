import { useEffect, useRef, useState } from 'react';
import { CheckCircle2, Circle, Loader2, AlertTriangle } from 'lucide-react';
import { workflowService } from '../services/workflowService';
import styles from './DesignJobProgress.module.css';

const POLL_INTERVAL_MS = 3000;

export type DesignJobPhase = 'preparing' | 'processing' | 'completed' | 'completed_with_warnings' | 'failed' | 'cancelled';

/**
 * AIHOME's own local WorkflowExecution.status vocabulary (Pending,
 * Running, Completed, Completed with Warnings, Failed, Cancelled) maps
 * onto exactly two real non-terminal phases plus terminal outcomes.
 *
 * IMPORTANT, honest deviation from the requested 5-step example
 * (Preparing Images / AI Processing / Generating Design Concepts /
 * Quality Review / Finalizing): the backend genuinely cannot
 * distinguish those five from each other - "Running" is the only
 * non-terminal signal DEV-TOOLS reports back once a job starts
 * executing. Displaying five separately-lit checklist steps would mean
 * three of them light up based on nothing real, and the checklist would
 * visibly "stick" on one step for the entire processing duration with
 * no way to tell if that's normal or stuck. Two honest phases -
 * Preparing Images, then a single AI Processing step with an
 * indeterminate spinner for its whole duration - reflects what AIHOME
 * can actually know, per this feature's own instruction not to
 * duplicate or invent polling/orchestration logic.
 */
function mapStatusToPhase(status: string): DesignJobPhase {
  switch (status) {
    case 'Pending':
    case 'Submitted':
      return 'preparing';
    case 'Running':
      return 'processing';
    case 'Completed':
      return 'completed';
    case 'Completed with Warnings':
      return 'completed_with_warnings';
    case 'Failed':
      return 'failed';
    case 'Cancelled':
      return 'cancelled';
    default:
      return 'preparing';
  }
}

export interface DesignJobProgressProps {
  designJobId: number;
  executionId: number;
  toolName: string;
  onComplete: (hadWarnings: boolean) => void;
  onCancelView: () => void;
  id?: string;
}

/**
 * components/DesignJobProgress.tsx
 *
 * AIHOME Design Studio V2 - Design Job User Experience. A business-
 * friendly view over the EXISTING Design Job execution lifecycle -
 * reuses workflowService.checkStatus() (the same polling primitive
 * AI Orchestration's own monitoring already uses) rather than
 * introducing any new backend endpoint or a parallel job-processing
 * mechanism. Never exposes WorkflowExecution IDs, workflow templates,
 * agent names, child workflows, or the WACP timeline - those remain
 * AI Orchestration's domain, a separate, developer-facing experience
 * this component deliberately never links to or resembles.
 */
export default function DesignJobProgress({
  designJobId,
  executionId,
  toolName,
  onComplete,
  onCancelView,
  id,
}: DesignJobProgressProps) {
  const [phase, setPhase] = useState<DesignJobPhase>('preparing');
  const completedRef = useRef(false);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        const res = await workflowService.checkStatus(executionId);
        if (cancelled) return;
        const nextPhase = mapStatusToPhase(res.status);
        setPhase(nextPhase);
        if ((nextPhase === 'completed' || nextPhase === 'completed_with_warnings') && !completedRef.current) {
          completedRef.current = true;
          onComplete(nextPhase === 'completed_with_warnings');
        }
      } catch (err) {
        console.error('[Design Job Progress] Failed to check status:', err);
        // A transient polling failure is not itself a Design Job
        // failure - the next tick tries again, same as every other
        // status poller in this codebase.
      }
    };

    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [executionId, onComplete]);

  const steps: { key: DesignJobPhase; label: string }[] = [
    { key: 'preparing', label: 'Preparing Images' },
    { key: 'processing', label: 'AI Processing' },
  ];
  const stepOrder: DesignJobPhase[] = ['preparing', 'processing'];
  const currentIndex = stepOrder.indexOf(phase);

  const isFailed = phase === 'failed' || phase === 'cancelled';

  return (
    <div className={styles.wrapper} id={id || 'design-job-progress'}>
      <h3 className={styles.title}>Design Job</h3>
      <p className={styles.subtitle}>{toolName}</p>

      {isFailed ? (
        <div className={styles.failedBanner}>
          <AlertTriangle className="w-5 h-5" />
          <span>{phase === 'cancelled' ? 'This Design Job was cancelled.' : 'This Design Job could not be completed.'}</span>
        </div>
      ) : (
        <div className={styles.steps}>
          {steps.map((step, idx) => {
            const isDone = idx < currentIndex || phase === 'completed' || phase === 'completed_with_warnings';
            const isActive = idx === currentIndex && phase !== 'completed' && phase !== 'completed_with_warnings';
            return (
              <div key={step.key} className={styles.step}>
                {isDone ? (
                  <CheckCircle2 className={`w-4 h-4 ${styles.stepIconDone}`} />
                ) : isActive ? (
                  <Loader2 className={`w-4 h-4 ${styles.stepIconActive} ${styles.spin}`} />
                ) : (
                  <Circle className={`w-4 h-4 ${styles.stepIconPending}`} />
                )}
                <span className={isDone || isActive ? styles.stepLabelActive : styles.stepLabelPending}>{step.label}</span>
              </div>
            );
          })}
        </div>
      )}

      <p className={styles.estimate}>Estimated time: 1-2 minutes</p>

      <button type="button" className="enterprise-btn enterprise-btn-ghost" onClick={onCancelView} id="design-job-progress-continue-btn">
        Continue Browsing
      </button>
    </div>
  );
}
