import { useState, useCallback, useEffect } from 'react';
import { workflowService } from '../services/workflowService';
import { additionalService } from '../services/additional';
import { WorkflowExecution } from '../types/index';
import { CrePropertyAnalysisReport } from '../types';

/**
 * hooks/usePropertyAnalysisState.ts
 *
 * Phase 2A - the single, reusable data-access layer behind Current
 * Analysis, Execution History, and Reports on a Property. Deliberately
 * three SEPARATE fetches into three separate arrays, per the required
 * correction: PropertyAnalysisReport rows only ever exist for
 * successfully-synchronized completions (confirmed directly against
 * result_sync.py - _sync_failed_job() never creates one), so Failed/
 * Rejected/Cancelled executions must never be represented as report
 * records. Execution History and Reports are two different data
 * sources with two different backend queries, not one list filtered
 * two ways client-side.
 *
 * Zero new endpoints: both queries already exist and are already
 * correctly filtered/ordered server-side -
 *   GET /workflow-executions/?property_id=X            (execution history)
 *   GET /workflow-executions/?property_id=X&limit=1     (current analysis)
 *   GET /property-analysis-reports/?property_id=X       (reports)
 */

export interface PropertyAnalysisState {
  currentExecution: WorkflowExecution | null;
  executionHistory: WorkflowExecution[];
  reports: CrePropertyAnalysisReport[];
  /** Set of WorkflowExecution.execution_id values that have a
   * successfully-synced report - the ONLY correct way to tell whether
   * a Completed execution's row should offer "View Report" vs
   * "Retry Sync" (a Completed execution with result_sync_error set,
   * and therefore absent from this set, never got a report row at all). */
  executionIdsWithReports: Set<number>;
  isLoading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

export function usePropertyAnalysisState(propertyId: number | null): PropertyAnalysisState {
  const [currentExecution, setCurrentExecution] = useState<WorkflowExecution | null>(null);
  const [executionHistory, setExecutionHistory] = useState<WorkflowExecution[]>([]);
  const [reports, setReports] = useState<CrePropertyAnalysisReport[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (propertyId === null) {
      setCurrentExecution(null);
      setExecutionHistory([]);
      setReports([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const [historyRes, reportsRes] = await Promise.all([
        workflowService.listExecutions({ property_id: propertyId, limit: 100 }),
        additionalService.listReports({ property_id: propertyId }),
      ]);

      // Server already orders both by created_at DESC - re-sorting
      // client-side defensively rather than trusting array order alone,
      // consistent with this project's established "never rely on
      // insertion order" discipline.
      const history = [...(historyRes.items || [])].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      const reportList = [...(reportsRes.items || [])].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );

      setExecutionHistory(history);
      setReports(reportList);
      setCurrentExecution(history[0] ?? null);
    } catch (err) {
      console.error('[usePropertyAnalysisState] Failed to load property analysis state:', err);
      setError('Unable to load analysis history for this property.');
    } finally {
      setIsLoading(false);
    }
  }, [propertyId]);

  useEffect(() => {
    load();
  }, [load]);

  const executionIdsWithReports = new Set(
    reports.map((r) => r.workflow_execution_id).filter((id): id is number => id !== undefined)
  );

  return {
    currentExecution,
    executionHistory,
    reports,
    executionIdsWithReports,
    isLoading,
    error,
    reload: load,
  };
}
