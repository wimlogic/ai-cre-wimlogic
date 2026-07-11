import { Check, Loader2, X, Ban } from 'lucide-react';
import styles from './EnterpriseJobProgress.module.css';

/**
 * components/EnterpriseJobProgress.tsx
 *
 * Enterprise Job Progress - a WIMLOGIC Enterprise Component (Phase 1A).
 *
 * Renders the lifecycle of a WACP Enterprise Job as a horizontal step
 * sequence: preparation -> submission -> backend execution -> completion,
 * with a distinct terminal presentation for failure and cancellation.
 *
 * This component is intentionally generic and carries no AI-CRE-specific
 * concepts (no execution id, no workflow code, no project/property
 * context). It only knows about step keys and labels, a "current key" to
 * match against them, and two terminal flags. Any WIMLOGIC Business
 * Application that submits jobs through the WACP Client SDK - AI-ECOM,
 * AI-HR, AI-ERP, AI-CRM, and future products - can reuse this exact
 * component simply by supplying its own step labels (or accepting the
 * defaults) and passing whatever key its own job state currently holds,
 * whether that is a client-side phase (e.g. "Preparing") or a verbatim
 * backend status (e.g. "Running", "Completed").
 *
 * Per the approved D3 decision, this component never renames or
 * reinterprets a backend status - the default step keys deliberately use
 * "Pending" rather than "Queued" because that is the AI-CRE backend's
 * actual vocabulary, and a consuming application with a different backend
 * vocabulary is expected to override `steps` rather than have this
 * component silently translate one vocabulary into another.
 *
 * Styling is CSS Modules backed entirely by tokens.css and the existing
 * `enterprise-*` global primitives (no Tailwind, no component-specific
 * color values), matching every other component in this library.
 */

export interface EnterpriseJobProgressStep {
  /** Matched case-insensitively against `currentKey`. Either a client-side phase or a verbatim backend status string. */
  key: string;
  /** Business-friendly label shown under the step marker. */
  label: string;
}

/**
 * Standard Enterprise Job flow: client-side preparation and submission,
 * followed by the AI-CRE backend's own execution statuses, ending in a
 * brief client-side phase while results/assets are refetched after a
 * terminal backend status. Consumers may pass their own `steps` to reflect
 * a different backend vocabulary or a different job flow entirely.
 */
const DEFAULT_STEPS: EnterpriseJobProgressStep[] = [
  { key: 'Preparing', label: 'Preparing Request' },
  { key: 'Submitting', label: 'Submitting' },
  { key: 'Pending', label: 'Pending' },
  { key: 'Running', label: 'Running' },
  { key: 'ProcessingResults', label: 'Processing Results' },
  { key: 'Completed', label: 'Completed' },
];

export interface EnterpriseJobProgressProps {
  /** Ordered, non-terminal steps of the job lifecycle. Defaults to DEFAULT_STEPS. */
  steps?: EnterpriseJobProgressStep[];
  /** The current step key. Matched case-insensitively against each step's `key`. A key with no match renders every step as upcoming. */
  currentKey: string;
  /** Renders the terminal failure presentation instead of an upcoming step. */
  isFailed?: boolean;
  /** Renders the terminal cancellation presentation instead of an upcoming step. */
  isCancelled?: boolean;
  /** Optional detail shown beneath the terminal failure/cancellation marker (e.g. the backend's error_message). */
  terminalMessage?: string;
  id?: string;
}

type StepVisualState = 'complete' | 'current' | 'upcoming';

export default function EnterpriseJobProgress({
  steps = DEFAULT_STEPS,
  currentKey,
  isFailed = false,
  isCancelled = false,
  terminalMessage,
  id,
}: EnterpriseJobProgressProps) {
  const currentIndex = steps.findIndex(
    (step) => step.key.toLowerCase() === currentKey.trim().toLowerCase()
  );

  const isTerminalBranch = isFailed || isCancelled;

  const getStepState = (index: number): StepVisualState => {
    if (currentIndex === -1) return 'upcoming';
    if (index < currentIndex) return 'complete';
    if (index === currentIndex) return 'current';
    return 'upcoming';
  };

  return (
    <div id={id || 'enterprise-job-progress'} className={styles.wrap}>
      <ol className={styles.steps}>
        {steps.map((step, index) => {
          const isLast = index === steps.length - 1;
          const state = getStepState(index);
          const isCurrentTerminal = state === 'current' && isTerminalBranch;

          const markerClass = [
            styles.marker,
            state === 'complete' && styles.markerComplete,
            state === 'current' && !isTerminalBranch && styles.markerCurrent,
            isCurrentTerminal && isFailed && styles.markerFailed,
            isCurrentTerminal && isCancelled && styles.markerCancelled,
          ]
            .filter(Boolean)
            .join(' ');

          const labelClass = [
            styles.label,
            (state === 'complete' || state === 'current') && styles.labelActive,
          ]
            .filter(Boolean)
            .join(' ');

          return (
            <li key={step.key} className={styles.step}>
              <div className={styles.stepHeader}>
                <span className={markerClass} aria-current={state === 'current' ? 'step' : undefined}>
                  {state === 'complete' && <Check className={styles.markerIcon} />}
                  {isCurrentTerminal && isFailed && <X className={styles.markerIcon} />}
                  {isCurrentTerminal && isCancelled && <Ban className={styles.markerIcon} />}
                  {state === 'current' && !isTerminalBranch && (
                    <Loader2 className={`${styles.markerIcon} ${styles.markerIconSpin}`} />
                  )}
                </span>
                {!isLast && (
                  <span
                    className={`${styles.connector} ${state === 'complete' ? styles.connectorComplete : ''}`}
                  />
                )}
              </div>
              <span className={labelClass}>{step.label}</span>
            </li>
          );
        })}
      </ol>

      {isTerminalBranch && (
        <div
          className={`${styles.terminalBanner} ${isFailed ? styles.terminalFailed : styles.terminalCancelled}`}
        >
          <span className={styles.terminalTitle}>{isFailed ? 'Failed' : 'Cancelled'}</span>
          {terminalMessage && <span className={styles.terminalMessage}>{terminalMessage}</span>}
        </div>
      )}
    </div>
  );
}
