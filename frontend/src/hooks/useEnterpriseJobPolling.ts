import { useCallback, useEffect, useRef, useState } from 'react';
import { workflowService } from '../services/workflowService';
import { isTerminalWorkflowStatus } from '../utils/status';

/**
 * hooks/useEnterpriseJobPolling.ts
 *
 * Single owner of the Enterprise Job polling loop (Phase 1A - WACP frontend
 * integration).
 *
 * This hook polls the existing `GET /ai-orchestration/status/{execution_id}`
 * endpoint via workflowService.checkStatus - the same endpoint the old
 * per-row "Sync Status" button called. That call is not a passive read: on
 * the backend, a terminal remote status triggers `result_sync` and hydrates
 * workflow results / generated assets (see
 * app/services/ai_orchestration_service.py::check_workflow_status). No new
 * endpoint is introduced here; this hook only automates calling the one
 * that already exists.
 *
 * Responsibilities kept entirely inside this hook, per the approved D4
 * decision:
 *   - Escalating poll interval (5s -> 10s -> 20s cap).
 *   - 15 minute polling timeout.
 *   - Automatic pause when the browser tab is hidden or the browser goes
 *     offline, and automatic resume (with an immediate poll) when the tab
 *     becomes visible again or the connection returns.
 *   - Stopping automatically on a terminal backend status (Completed,
 *     Failed, Cancelled), using the shared `isTerminalWorkflowStatus` helper
 *     from utils/status.ts rather than re-declaring a terminal-status list.
 *   - Tolerating a small number of consecutive transient network failures
 *     before surfacing an enterprise-friendly error, instead of aborting on
 *     the first failed request.
 *
 * This hook does not know about UI, workflow results, or generated assets -
 * it only knows how to reach a terminal backend status for one execution.
 * Consumers (the Enterprise Job panel, and eventually EnterpriseJobContext)
 * are responsible for reacting to terminal status via onTerminal.
 */

/** Escalation thresholds for the poll interval, in milliseconds. */
const DEFAULT_INTERVALS_MS: readonly [number, number, number] = [5_000, 10_000, 20_000];

/** Elapsed-time thresholds (from poll start) at which the interval escalates. */
const ESCALATION_THRESHOLDS_MS: readonly [number, number] = [60_000, 180_000]; // 1 min, 3 min

/** Default polling timeout: 15 minutes. */
const DEFAULT_TIMEOUT_MS = 15 * 60 * 1000;

/** Default number of consecutive network failures tolerated before surfacing an error. */
const DEFAULT_MAX_CONSECUTIVE_FAILURES = 3;

export interface UseEnterpriseJobPollingOptions {
  /** Called every time a poll succeeds and returns a (possibly unchanged) status. */
  onStatusChange?: (status: string) => void;
  /** Called exactly once, when a poll returns a terminal backend status. */
  onTerminal?: (finalStatus: string) => void;
  /** Escalation intervals [initial, mid, max] in ms. Defaults to [5000, 10000, 20000]. */
  intervalsMs?: readonly [number, number, number];
  /** Elapsed-time thresholds [toMid, toMax] in ms at which the interval escalates. */
  escalationThresholdsMs?: readonly [number, number];
  /** Total polling timeout in ms. Defaults to 15 minutes. */
  timeoutMs?: number;
  /** Consecutive failed polls tolerated before `error` is set. Defaults to 3. */
  maxConsecutiveFailures?: number;
}

export interface UseEnterpriseJobPollingResult {
  /** Verbatim backend status of the execution currently being polled, or null before the first successful poll. */
  status: string | null;
  /** True while a polling cycle is active (not necessarily mid-request). */
  isPolling: boolean;
  /** True when polling is temporarily paused (tab hidden or browser offline). */
  isPaused: boolean;
  /** True once the 15 minute polling timeout has been reached without a terminal status. */
  timedOut: boolean;
  /** Enterprise-friendly error message after repeated consecutive poll failures, or null. */
  error: string | null;
  /** Begins polling the given execution id. Replaces any execution currently being polled. */
  start: (executionId: number) => void;
  /** Stops polling immediately and resets all state back to idle. */
  stop: () => void;
}

export default function useEnterpriseJobPolling(
  options: UseEnterpriseJobPollingOptions = {}
): UseEnterpriseJobPollingResult {
  const {
    onStatusChange,
    onTerminal,
    intervalsMs = DEFAULT_INTERVALS_MS,
    escalationThresholdsMs = ESCALATION_THRESHOLDS_MS,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    maxConsecutiveFailures = DEFAULT_MAX_CONSECUTIVE_FAILURES,
  } = options;

  const [status, setStatus] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [timedOut, setTimedOut] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Mutable polling state that must not trigger re-renders on its own.
  const executionIdRef = useRef<number | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const startedAtRef = useRef<number>(0);
  const consecutiveFailuresRef = useRef<number>(0);
  const pausedRef = useRef<boolean>(false);
  const activeRef = useRef<boolean>(false);

  // Kept in refs (not just options) so the latest callbacks/config are used
  // even though the polling loop below is only ever set up via `start`.
  const onStatusChangeRef = useRef(onStatusChange);
  const onTerminalRef = useRef(onTerminal);
  onStatusChangeRef.current = onStatusChange;
  onTerminalRef.current = onTerminal;

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  /** Picks the escalation-appropriate interval for the current elapsed time. */
  const getCurrentInterval = useCallback((): number => {
    const elapsed = Date.now() - startedAtRef.current;
    const [initial, mid, max] = intervalsMs;
    const [toMid, toMax] = escalationThresholdsMs;
    if (elapsed < toMid) return initial;
    if (elapsed < toMax) return mid;
    return max;
  }, [intervalsMs, escalationThresholdsMs]);

  const stop = useCallback(() => {
    clearTimer();
    activeRef.current = false;
    executionIdRef.current = null;
    consecutiveFailuresRef.current = 0;
    pausedRef.current = false;
    setIsPolling(false);
    setIsPaused(false);
    setTimedOut(false);
    setError(null);
    setStatus(null);
  }, [clearTimer]);

  const scheduleNext = useCallback(() => {
    if (!activeRef.current || pausedRef.current) {
      return;
    }

    const elapsed = Date.now() - startedAtRef.current;
    if (elapsed >= timeoutMs) {
      setTimedOut(true);
      activeRef.current = false;
      setIsPolling(false);
      clearTimer();
      return;
    }

    clearTimer();
    timerRef.current = setTimeout(() => {
      void poll();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, getCurrentInterval());
    // poll is defined below via useCallback and stable across renders;
    // referenced here through closure rather than a dependency to avoid a
    // circular useCallback declaration order.
  }, [clearTimer, getCurrentInterval, timeoutMs]);

  const poll = useCallback(async () => {
    const executionId = executionIdRef.current;
    if (executionId === null || !activeRef.current || pausedRef.current) {
      return;
    }

    try {
      const response = await workflowService.checkStatus(executionId);
      consecutiveFailuresRef.current = 0;
      setError(null);
      setStatus(response.status);
      onStatusChangeRef.current?.(response.status);

      if (isTerminalWorkflowStatus(response.status)) {
        activeRef.current = false;
        setIsPolling(false);
        clearTimer();
        onTerminalRef.current?.(response.status);
        return;
      }

      scheduleNext();
    } catch (err: any) {
      consecutiveFailuresRef.current += 1;
      console.error(
        `Enterprise Job polling error for execution_id=${executionId} (consecutive failure ${consecutiveFailuresRef.current}):`,
        err
      );

      if (consecutiveFailuresRef.current >= maxConsecutiveFailures) {
        setError(
          err?.message ||
            'Unable to reach the WIMLOGIC backend to check job status. Monitoring will keep retrying.'
        );
      }

      // Transient failures never stop the loop outright - only the terminal
      // status, an explicit stop(), or the overall timeout does.
      scheduleNext();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clearTimer, maxConsecutiveFailures, scheduleNext]);

  const start = useCallback(
    (executionId: number) => {
      clearTimer();
      executionIdRef.current = executionId;
      startedAtRef.current = Date.now();
      consecutiveFailuresRef.current = 0;
      pausedRef.current = false;
      activeRef.current = true;
      setStatus(null);
      setError(null);
      setTimedOut(false);
      setIsPaused(false);
      setIsPolling(true);
      void poll();
    },
    [clearTimer, poll]
  );

  // Pause on hidden tab / offline, resume (with an immediate poll) on
  // visible tab / online, per the approved D4 enhancement.
  useEffect(() => {
    const pause = () => {
      if (!activeRef.current || pausedRef.current) return;
      pausedRef.current = true;
      clearTimer();
      setIsPaused(true);
    };

    const resume = () => {
      if (!activeRef.current || !pausedRef.current) return;
      pausedRef.current = false;
      setIsPaused(false);
      void poll();
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        pause();
      } else {
        resume();
      }
    };

    const handleOffline = () => pause();
    const handleOnline = () => resume();

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('offline', handleOffline);
    window.addEventListener('online', handleOnline);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('online', handleOnline);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [poll]);

  // Ensure the loop and any pending timer are torn down on unmount.
  useEffect(() => {
    return () => {
      activeRef.current = false;
      clearTimer();
    };
  }, [clearTimer]);

  return {
    status,
    isPolling,
    isPaused,
    timedOut,
    error,
    start,
    stop,
  };
}
