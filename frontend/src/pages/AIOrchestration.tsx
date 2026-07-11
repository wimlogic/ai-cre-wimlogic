import { useState, useEffect } from 'react';
import { projectService } from '../services/projectService';
import { propertyService } from '../services/propertyService';
import { workflowService } from '../services/workflowService';
import type { Project, Property, WorkflowExecution, WorkflowEvent, EnterpriseJobClientPhase, EnterpriseJobCapabilities } from '../types/index';
import useEnterpriseJobPolling from '../hooks/useEnterpriseJobPolling';
import { isTerminalWorkflowStatus } from '../utils/status';
import EnterpriseCard from '../components/EnterpriseCard';
import EnterpriseJobPanel from '../components/EnterpriseJobPanel';
import StatusBadge from '../components/StatusBadge';
import LoadingState from '../components/LoadingState';
import EmptyState from '../components/EmptyState';
import FormField from '../components/FormField';
import type { EnterpriseJobTimelineEntry } from '../components/EnterpriseJobTimeline';
import { Cpu, Clock, Sparkles, RefreshCw, Activity, Play } from 'lucide-react';
import styles from './AIOrchestration.module.css';

/**
 * pages/AIOrchestration.tsx
 *
 * AI-CRE WIMLOGIC V1.0 - Phase 1A WACP Frontend Integration.
 *
 * This page replaces the previous fire-and-forget "Execute Workflow" UX
 * with Enterprise Job Submission: the same business form as before (project,
 * property, pipeline, priority, schedule, custom notes), now paired with an
 * automatically-polling Enterprise Job monitor built entirely from the
 * Phase 1A component library - useEnterpriseJobPolling (File 3),
 * EnterpriseJobProgress and EnterpriseJobTimeline (Files 4-5, composed
 * inside EnterpriseJobPanel), and EnterpriseJobPanel itself (File 6).
 *
 * This page introduces no new backend endpoints and no new business logic:
 * - Submission still calls workflowService.submit (POST /ai-orchestration/submit).
 * - Monitoring still calls workflowService.checkStatus (GET
 *   /ai-orchestration/status/{execution_id}) - now automatically, via the
 *   polling hook, instead of a manual per-row "Sync Status" button, which
 *   is removed as obsolete execution UI per the approved plan.
 * - History still comes from workflowService.listExecutions.
 * - Timeline entries still come from workflowService.getExecutionEvents,
 *   mapped onto the generic EnterpriseJobTimelineEntry shape the panel
 *   expects.
 *
 * Cancel/Retry (approved decision D1): JOB_CAPABILITIES below is the single
 * place that gates both actions, and both are false until the AI-CRE
 * backend exposes the corresponding endpoints. EnterpriseJobPanel hides the
 * controls entirely while these flags are false - no fake handlers are
 * wired up here.
 *
 * Cross-page refresh of Workflow Results / Generated Assets on job
 * completion (called for in the original master prompt) is intentionally
 * NOT implemented in this file. That behavior depends on the
 * EnterpriseJobContext subscriber pattern approved alongside this phase,
 * which has not yet been built - this page only refreshes what it owns
 * (its own execution history) and tells the user where to look next.
 */

/** Same five pipelines the pre-Phase-1A page offered - preserved exactly, not new business logic. */
const WORKFLOW_CODE_OPTIONS: { value: string; label: string }[] = [
  { value: 'ZONING_ANALYSIS', label: 'Zoning Feasibility Model (SB-9/SB-10)' },
  { value: 'RENOVATION_ESTIMATE', label: 'Commercial Renovation Pro-Forma' },
  { value: 'CONCEPTUAL_DESIGN', label: 'CAD Massing / Architectural Concept Study' },
  { value: 'PROPERTY_SCAN', label: 'Full Digital LiDAR Scanning Simulation' },
  { value: 'AUDIT_REPORT', label: 'Assessor Tax & APN Audit Synthesis' },
];

function workflowLabel(code: string | undefined): string {
  return WORKFLOW_CODE_OPTIONS.find((o) => o.value === code)?.label || code || 'Enterprise Job';
}

/**
 * Cancel/Retry capability gate (approved decision D1). Both remain false
 * until the AI-CRE backend exposes cancel/retry endpoints - at that point
 * this becomes a capability-flag change, not a UI rewrite.
 */
const JOB_CAPABILITIES: EnterpriseJobCapabilities = { canCancel: false, canRetry: false };

export default function AIOrchestration() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);
  const [executions, setExecutions] = useState<WorkflowExecution[]>([]);
  const [isLoadingExecutions, setIsLoadingExecutions] = useState(true);

  // Selection state
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [selectedPropertyId, setSelectedPropertyId] = useState<string>('');

  // Workflow config (unchanged business fields)
  const [workflowCode, setWorkflowCode] = useState('ZONING_ANALYSIS');
  const [priority, setPriority] = useState('Normal');
  const [isScheduled, setIsScheduled] = useState(false);
  const [scheduleTime, setScheduleTime] = useState('');
  const [customPrompt, setCustomPrompt] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');

  // Enterprise Job monitor state - the job currently shown in EnterpriseJobPanel
  const [activeExecutionId, setActiveExecutionId] = useState<number | null>(null);
  const [activeExecutionNumber, setActiveExecutionNumber] = useState<string | undefined>(undefined);
  const [activeWorkflowCode, setActiveWorkflowCode] = useState<string | undefined>(undefined);
  const [clientPhase, setClientPhase] = useState<EnterpriseJobClientPhase>('Idle');
  const [activeErrorMessage, setActiveErrorMessage] = useState<string | null>(null);
  const [timelineEntries, setTimelineEntries] = useState<EnterpriseJobTimelineEntry[]>([]);
  const [isTimelineLoading, setIsTimelineLoading] = useState(false);

  const loadExecutions = async (): Promise<WorkflowExecution[]> => {
    setIsLoadingExecutions(true);
    try {
      const res = await workflowService.listExecutions({ limit: 50 });
      const items = res.items || [];
      setExecutions(items);
      return items;
    } catch (err) {
      console.error('Failed to list executions:', err);
      return [];
    } finally {
      setIsLoadingExecutions(false);
    }
  };

  const refreshTimeline = async (executionId: number) => {
    setIsTimelineLoading(true);
    try {
      const res = await workflowService.getExecutionEvents(executionId);
      const mapped: EnterpriseJobTimelineEntry[] = (res.items || []).map((evt: WorkflowEvent) => ({
        id: evt.event_id,
        eventType: evt.event_type,
        status: evt.status,
        message: evt.message,
        timestamp: evt.created_at,
      }));
      setTimelineEntries(mapped);
    } catch (err) {
      console.error('Failed to load job timeline:', err);
    } finally {
      setIsTimelineLoading(false);
    }
  };

  const handleJobStatusChange = (_newStatus: string) => {
    setClientPhase('Polling');
    if (activeExecutionId !== null) {
      void refreshTimeline(activeExecutionId);
    }
  };

  const handleJobTerminal = async (finalStatus: string) => {
    setClientPhase('ProcessingResults');

    if (activeExecutionId !== null) {
      try {
        const exec = await workflowService.getExecution(activeExecutionId);
        setActiveErrorMessage(exec.error_message || null);
      } catch (err) {
        console.error('Failed to refresh execution detail after terminal status:', err);
      }
      await refreshTimeline(activeExecutionId);
    }

    // Refresh only what this page owns - the history table. Refreshing
    // Workflow Results / Generated Assets on other pages requires the
    // EnterpriseJobContext subscriber pattern, not yet built (see header
    // comment).
    await loadExecutions();

    setClientPhase('Done');

    if (finalStatus.trim().toLowerCase() === 'completed') {
      setFormSuccess(
        'Analysis completed. Results and generated assets are ready to review in Workflow Results and Generated Assets.'
      );
    }
  };

  const {
    status: pollStatus,
    isPolling,
    isPaused,
    timedOut,
    error: pollError,
    start: startPolling,
  } = useEnterpriseJobPolling({
    onStatusChange: handleJobStatusChange,
    onTerminal: handleJobTerminal,
  });

  // Initial load: projects + execution history, then resume monitoring any
  // job that was left in a non-terminal state (e.g. the page was refreshed
  // mid-job) - per the approved refresh-survival behavior.
  useEffect(() => {
    async function bootstrap() {
      try {
        const res = await projectService.list({ limit: 300 });
        setProjects(res.items || []);
        if (res.items.length > 0) {
          setSelectedProjectId(res.items[0].project_id);
        }
      } catch (err) {
        console.error('Failed to load projects:', err);
      }

      const items = await loadExecutions();
      const inFlight = items.find((exec) => !isTerminalWorkflowStatus(exec.status));
      if (inFlight) {
        setActiveExecutionId(inFlight.execution_id);
        setActiveExecutionNumber(inFlight.execution_number);
        setActiveWorkflowCode(inFlight.workflow_code);
        setClientPhase('Polling');
        startPolling(inFlight.execution_id);
        void refreshTimeline(inFlight.execution_id);
      }
    }
    void bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Dynamically load properties when Project changes (unchanged)
  useEffect(() => {
    async function loadProperties() {
      if (!selectedProjectId) {
        setProperties([]);
        setSelectedPropertyId('');
        return;
      }
      try {
        const props = await propertyService.listByProject(selectedProjectId);
        setProperties(props);
        setSelectedPropertyId(props.length > 0 ? String(props[0].id) : '');
      } catch (err) {
        console.error('Failed to load properties for project:', err);
      }
    }
    loadProperties();
  }, [selectedProjectId]);

  const handleGenerateAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');

    if (!selectedProjectId) {
      setFormError('A project must be selected to proceed.');
      return;
    }
    if (!selectedPropertyId) {
      setFormError('A property parcel must be selected to proceed.');
      return;
    }

    const projObj = projects.find((p) => p.project_id === selectedProjectId);
    const propObj = properties.find((p) => p.id === Number(selectedPropertyId));
    if (!projObj || !propObj) {
      setFormError('Mismatched database context.');
      return;
    }

    setClientPhase('Preparing');
    setIsSubmitting(true);
    try {
      const metadata_json: Record<string, any> = {
        submitted_via: 'WIMLOGIC CRE AI-Client',
        custom_instructions: customPrompt || undefined,
      };
      if (isScheduled && scheduleTime) {
        metadata_json.is_scheduled = true;
        metadata_json.schedule_timestamp = scheduleTime;
      }

      setClientPhase('Submitting');
      const res = await workflowService.submit({
        project_id: projObj.id,
        property_id: propObj.id,
        workflow_code: workflowCode,
        priority,
        metadata_json,
      });

      setActiveExecutionId(res.execution_id);
      setActiveExecutionNumber(res.execution_number);
      setActiveWorkflowCode(res.workflow_code);
      setActiveErrorMessage(null);
      setTimelineEntries([]);
      setClientPhase('Polling');
      startPolling(res.execution_id);
      void refreshTimeline(res.execution_id);

      setFormSuccess(`Job submitted to DEV-TOOLS. Execution Number: ${res.execution_number}`);
      setCustomPrompt('');
      setIsScheduled(false);
      setScheduleTime('');

      await loadExecutions();
    } catch (err: any) {
      console.error('Error submitting job to DEV-TOOLS:', err);
      setClientPhase('Idle');
      setFormError(err?.message || 'Error submitting job to the WIMLOGIC DEV-TOOLS orchestrator.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.page}>
      {/* Page Header */}
      <div className={styles.headerArea}>
        <Cpu className={styles.headerIcon} />
        <div>
          <h1 className={styles.pageTitle}>AI Orchestration</h1>
          <p className={styles.pageSubtitle}>
            Generate Analysis by submitting property profiles to DEV-TOOLS for automated
            architectural, zoning, and estimation pipelines - with live enterprise job monitoring
            and full audit history.
          </p>
        </div>
      </div>

      <div className={styles.grid}>
        {/* Left: Submission form */}
        <EnterpriseCard id="ai-orchestration-form-card" className={styles.formCard}>
          <form onSubmit={handleGenerateAnalysis} className={styles.form}>
            <div className={styles.formSectionHeader}>
              <Sparkles className={styles.formSectionIcon} />
              Configure Analysis
            </div>

            <FormField label="Project Folder Context" required>
              <select
                required
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                className="enterprise-form-input"
              >
                <option value="">-- Select Project --</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.project_id}>
                    [{p.project_id}] {p.project_name}
                  </option>
                ))}
              </select>
            </FormField>

            <FormField label="Target Property Parcel" required>
              <select
                required
                disabled={!selectedProjectId}
                value={selectedPropertyId}
                onChange={(e) => setSelectedPropertyId(e.target.value)}
                className="enterprise-form-input"
              >
                <option value="">-- Choose Property --</option>
                {properties.map((p) => (
                  <option key={p.id} value={p.id}>
                    [{p.property_uid}] {p.address}
                  </option>
                ))}
              </select>
            </FormField>

            <FormField label="Automation Pipeline" required>
              <select
                required
                value={workflowCode}
                onChange={(e) => setWorkflowCode(e.target.value)}
                className="enterprise-form-input"
              >
                {WORKFLOW_CODE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </FormField>

            <FormField label="Execution Priority">
              <div className={styles.priorityGroup}>
                {['Low', 'Normal', 'High'].map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => setPriority(p)}
                    className={`enterprise-btn ${priority === p ? 'enterprise-btn-primary' : 'enterprise-btn-secondary'}`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </FormField>

            <div className={styles.scheduleRow}>
              <label className={styles.scheduleLabel}>
                <Clock className={styles.scheduleIcon} />
                Schedule Job Execution
              </label>
              <input
                type="checkbox"
                checked={isScheduled}
                onChange={(e) => setIsScheduled(e.target.checked)}
                className="enterprise-form-checkbox"
              />
            </div>
            {isScheduled && (
              <input
                type="datetime-local"
                required
                value={scheduleTime}
                onChange={(e) => setScheduleTime(e.target.value)}
                className="enterprise-form-input"
              />
            )}

            <FormField label="Custom Orchestration Notes (Optional)">
              <textarea
                rows={2}
                placeholder="Specific zoning regulations to override or custom directives..."
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                className="enterprise-form-input"
              />
            </FormField>

            {formError && <div className={`${styles.notice} ${styles.noticeError}`}>{formError}</div>}
            {formSuccess && (
              <div className={`${styles.notice} ${styles.noticeSuccess}`}>{formSuccess}</div>
            )}

            <button
              type="submit"
              disabled={isSubmitting || properties.length === 0}
              className={`enterprise-btn enterprise-btn-primary enterprise-btn-lg ${styles.submitBtn} ${isSubmitting ? 'enterprise-btn-loading' : ''}`}
            >
              <Play className={styles.submitIcon} />
              {isScheduled ? 'Schedule Analysis' : 'Generate Analysis'}
            </button>
          </form>
        </EnterpriseCard>

        {/* Right: Enterprise Job monitor + history */}
        <div className={styles.rightColumn}>
          <EnterpriseJobPanel
            id="ai-orchestration-job-panel"
            executionId={activeExecutionId}
            executionNumber={activeExecutionNumber}
            jobLabel={workflowLabel(activeWorkflowCode)}
            status={pollStatus}
            clientPhase={clientPhase}
            isPolling={isPolling}
            isPaused={isPaused}
            timedOut={timedOut}
            pollError={pollError}
            errorMessage={activeErrorMessage}
            timelineEntries={timelineEntries}
            isTimelineLoading={isTimelineLoading}
            capabilities={JOB_CAPABILITIES}
          />

          <EnterpriseCard
            id="ai-orchestration-history-card"
            title="Execution Queue & History"
            headerAction={
              <button
                onClick={() => void loadExecutions()}
                className={styles.refreshBtn}
                title="Refresh Queue Status"
              >
                <RefreshCw className={styles.refreshIcon} />
              </button>
            }
          >
            {isLoadingExecutions ? (
              <LoadingState type="rows" rowsCount={4} />
            ) : executions.length === 0 ? (
              <EmptyState
                icon={Activity}
                title="No Job Executions Logged"
                description="Enterprise jobs submitted to DEV-TOOLS will be displayed here in real-time."
              />
            ) : (
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Execution No.</th>
                      <th>Pipeline</th>
                      <th>Priority</th>
                      <th>Status</th>
                      <th>Submitted At</th>
                    </tr>
                  </thead>
                  <tbody>
                    {executions.map((exec) => (
                      <tr key={exec.execution_id}>
                        <td className={styles.execNumber}>
                          {exec.execution_number}
                          {exec.execution_id === activeExecutionId && (
                            <span className={styles.monitoringTag}>Monitoring</span>
                          )}
                        </td>
                        <td>
                          <span className={styles.codePill}>{exec.workflow_code}</span>
                        </td>
                        <td>
                          <span
                            className={`${styles.priorityPill} ${
                              exec.priority === 'High' ? styles.priorityHigh : styles.priorityNormal
                            }`}
                          >
                            {exec.priority}
                          </span>
                        </td>
                        <td>
                          <StatusBadge status={exec.status} type="workflow" />
                        </td>
                        <td className={styles.timestampCell}>
                          {new Date(exec.submitted_at || exec.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </EnterpriseCard>
        </div>
      </div>
    </div>
  );
}
