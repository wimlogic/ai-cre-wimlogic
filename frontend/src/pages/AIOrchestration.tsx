import React, { useState, useEffect } from 'react';
import { projectService } from '../services/projectService';
import { propertyService } from '../services/propertyService';
import { workflowService } from '../services/workflowService';
import { Project, Property, WorkflowExecution } from '../types';
import { 
  Cpu, 
  Clock, 
  Play, 
  RefreshCw, 
  CheckCircle, 
  AlertTriangle, 
  Layers, 
  Sparkles,
  Search,
  Calendar,
  Settings as SettingsIcon,
  HelpCircle,
  Activity
} from 'lucide-react';

export default function AIOrchestration() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);
  const [executions, setExecutions] = useState<WorkflowExecution[]>([]);

  // Selection state
  const [selectedProjectId, setSelectedProjectId] = useState<string>(''); // string code e.g. PRJ001
  const [selectedPropertyId, setSelectedPropertyId] = useState<string>(''); // db id string

  // Workflow Config
  const [workflowCode, setWorkflowCode] = useState('ZONING_ANALYSIS');
  const [priority, setPriority] = useState('Normal');
  const [isScheduled, setIsScheduled] = useState(false);
  const [scheduleTime, setScheduleTime] = useState('');
  const [customPrompt, setCustomPrompt] = useState('');
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingExecutions, setIsLoadingExecutions] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Initial load
  useEffect(() => {
    async function loadProjects() {
      try {
        const res = await projectService.list({ limit: 300 });
        setProjects(res.items || []);
        if (res.items.length > 0) {
          setSelectedProjectId(res.items[0].project_id);
        }
      } catch (err) {
        console.error('Failed to load projects:', err);
      }
    }
    loadProjects();
    loadExecutions();
  }, []);

  // Dynamically load properties when Project changes
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
        if (props.length > 0) {
          setSelectedPropertyId(String(props[0].id));
        } else {
          setSelectedPropertyId('');
        }
      } catch (err) {
        console.error('Failed to load properties for project:', err);
      }
    }
    loadProperties();
  }, [selectedProjectId]);

  const loadExecutions = async () => {
    setIsLoadingExecutions(true);
    try {
      const res = await workflowService.listExecutions({ limit: 50 });
      setExecutions(res.items || []);
    } catch (err) {
      console.error('Failed to list executions:', err);
    } finally {
      setIsLoadingExecutions(false);
    }
  };

  const handleLaunchWorkflow = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    if (!selectedProjectId) {
      setErrorMsg('A project must be selected to proceed.');
      return;
    }
    if (!selectedPropertyId) {
      setErrorMsg('A property parcel must be selected to proceed.');
      return;
    }

    // Find full objects to obtain the integer DB IDs
    const projObj = projects.find(p => p.project_id === selectedProjectId);
    const propObj = properties.find(p => p.id === Number(selectedPropertyId));

    if (!projObj || !propObj) {
      setErrorMsg('Mismatched database context.');
      return;
    }

    setIsSubmitting(true);
    try {
      const metadata_json: Record<string, any> = {
        submitted_via: 'WIMLOGIC CRE AI-Client',
        custom_instructions: customPrompt || undefined
      };

      if (isScheduled && scheduleTime) {
        metadata_json.is_scheduled = true;
        metadata_json.schedule_timestamp = scheduleTime;
      }

      const payload = {
        project_id: projObj.id, // Must submit integer database ID
        property_id: propObj.id, // Must submit integer database ID
        workflow_code: workflowCode,
        priority: priority,
        metadata_json: metadata_json
      };

      const res = await workflowService.submit(payload);
      
      setSuccessMsg(`Workflow successfully queued! Execution Number: ${res.execution_number}`);
      setCustomPrompt('');
      setIsScheduled(false);
      setScheduleTime('');
      
      // Refresh execution list
      await loadExecutions();
    } catch (err: any) {
      console.error('Error submitting workflow:', err);
      setErrorMsg(err.message || 'Error executing WIMLOGIC orchestration submit handshake.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSyncStatus = async (id: number) => {
    try {
      await workflowService.checkStatus(id);
      loadExecutions();
    } catch (err) {
      console.error('Failed to sync status:', err);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div>
        <h1 className="text-xl font-sans font-bold tracking-tight text-slate-900 flex items-center gap-2">
          <Cpu className="w-5 h-5 text-indigo-600" />
          AI Orchestration
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Queue cloud-native real estate analysis pipelines. WIMLOGIC sends jobs directly to devtools for automated processing and assets delivery.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Form: Submit Job */}
        <div className="lg:col-span-1 bg-white border border-slate-100 rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <form onSubmit={handleLaunchWorkflow} className="space-y-4">
            <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-700 border-b border-slate-100 pb-2 mb-4 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-500" />
              Configure Pipeline
            </h2>

            {/* Project dropdown (Strict hierarchy) */}
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                Project Folder Context *
              </label>
              <select
                required
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 bg-white font-bold text-slate-700"
              >
                <option value="">-- Select Project --</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.project_id}>
                    [{p.project_id}] {p.project_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Dynamic Property dropdown (Strict hierarchy) */}
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                Target Property Parcel *
              </label>
              <select
                required
                disabled={!selectedProjectId}
                value={selectedPropertyId}
                onChange={(e) => setSelectedPropertyId(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 bg-white text-slate-700 disabled:bg-slate-50"
              >
                <option value="">-- Choose Property --</option>
                {properties.map((p) => (
                  <option key={p.id} value={p.id}>
                    [{p.property_uid}] {p.address}
                  </option>
                ))}
              </select>
            </div>

            {/* Workflow Code Selector */}
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                Automation Pipeline *
              </label>
              <select
                required
                value={workflowCode}
                onChange={(e) => setWorkflowCode(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 bg-white text-slate-700"
              >
                <option value="ZONING_ANALYSIS">Zoning Feasibility Model (SB-9/SB-10)</option>
                <option value="RENOVATION_ESTIMATE">Commercial Renovation Pro-Forma</option>
                <option value="CONCEPTUAL_DESIGN">CAD massing / Architectural Concept Study</option>
                <option value="PROPERTY_SCAN">Full Digital LiDAR Scanning Simulation</option>
                <option value="AUDIT_REPORT">Assessor Tax & APN Audit Synthesis</option>
              </select>
            </div>

            {/* Priority Selector */}
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                Execution Priority
              </label>
              <div className="grid grid-cols-3 gap-2">
                {['Low', 'Normal', 'High'].map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => setPriority(p)}
                    className={`py-1.5 rounded-lg border text-xs font-semibold tracking-wide transition-all focus:outline-none ${
                      priority === p 
                        ? 'bg-indigo-600 border-indigo-600 text-white shadow-sm' 
                        : 'border-slate-200 hover:bg-slate-50 text-slate-600 bg-white'
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            {/* Scheduling Config */}
            <div className="pt-2 border-t border-slate-100">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  Schedule Job Execution
                </span>
                <input
                  type="checkbox"
                  checked={isScheduled}
                  onChange={(e) => setIsScheduled(e.target.checked)}
                  className="w-4 h-4 text-indigo-600 border-slate-300 rounded focus:ring-indigo-500 cursor-pointer"
                />
              </div>

              {isScheduled && (
                <div className="mt-3 animate-fade-in">
                  <input
                    type="datetime-local"
                    required
                    value={scheduleTime}
                    onChange={(e) => setScheduleTime(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 bg-white"
                  />
                </div>
              )}
            </div>

            {/* Custom AI Guidelines */}
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                Custom Orchestration Notes (Optional)
              </label>
              <textarea
                rows={2}
                placeholder="Specific zoning regulations to override or custom directives..."
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 bg-slate-50"
              />
            </div>

            {errorMsg && (
              <div className="bg-rose-50 border-l-2 border-rose-500 text-rose-800 text-[11px] p-3 rounded font-semibold">
                {errorMsg}
              </div>
            )}

            {successMsg && (
              <div className="bg-emerald-50 border-l-2 border-emerald-500 text-emerald-800 text-[11px] p-3 rounded font-semibold">
                {successMsg}
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting || properties.length === 0}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-300 text-white rounded-lg text-xs font-semibold tracking-wider uppercase transition-all shadow-md shadow-indigo-600/15 flex items-center justify-center gap-1.5 focus:outline-none"
            >
              {isSubmitting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  SUBMITTING JOB...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  {isScheduled ? 'SCHEDULE PIPELINE' : 'LAUNCH PIPELINE'}
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right 2 columns: Queue & History Monitor */}
        <div className="lg:col-span-2 bg-white border border-slate-100 rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-center mb-5 pb-3 border-b border-slate-100">
              <h2 className="font-sans font-bold text-slate-800 text-sm tracking-wide uppercase flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-indigo-600" />
                Execution Queue & History
              </h2>
              <button
                onClick={loadExecutions}
                className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-slate-50 rounded-lg transition-all focus:outline-none"
                title="Refresh Queue Status"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>

            {isLoadingExecutions ? (
              <div className="py-24 flex justify-center items-center text-slate-400 text-xs font-mono uppercase tracking-widest">
                Syncing execution status...
              </div>
            ) : executions.length === 0 ? (
              <div className="py-24 text-center text-slate-400 flex flex-col items-center justify-center space-y-3">
                <Cpu className="w-10 h-10 text-slate-200" />
                <span className="text-xs font-mono uppercase tracking-wider">No job executions logged</span>
                <p className="text-xs text-slate-400 max-w-sm">
                  Active pipelines submitted to backend orchestrators will be displayed here in real-time.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50/70 border-b border-slate-100">
                      <th className="px-4 py-2.5 text-[9px] font-bold uppercase font-mono tracking-wider text-slate-400">Execution No.</th>
                      <th className="px-4 py-2.5 text-[9px] font-bold uppercase font-mono tracking-wider text-slate-400">Pipeline</th>
                      <th className="px-4 py-2.5 text-[9px] font-bold uppercase font-mono tracking-wider text-slate-400">Priority</th>
                      <th className="px-4 py-2.5 text-[9px] font-bold uppercase font-mono tracking-wider text-slate-400">Status</th>
                      <th className="px-4 py-2.5 text-[9px] font-bold uppercase font-mono tracking-wider text-slate-400">Submitted At</th>
                      <th className="px-4 py-2.5 text-[9px] font-bold uppercase font-mono tracking-wider text-slate-400 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {executions.map((exec) => (
                      <tr key={exec.execution_id} className="hover:bg-slate-50/50 transition-colors">
                        <td className="px-4 py-3.5 font-mono text-xs font-bold text-slate-800">
                          {exec.execution_number}
                        </td>
                        <td className="px-4 py-3.5">
                          <span className="px-2 py-0.5 bg-slate-100 rounded text-[10px] font-mono font-bold text-slate-600">
                            {exec.workflow_code}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 text-xs text-slate-600">
                          <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                            exec.priority === 'High' ? 'bg-rose-50 text-rose-700' : 'bg-slate-100 text-slate-600'
                          }`}>
                            {exec.priority}
                          </span>
                        </td>
                        <td className="px-4 py-3.5">
                          <span className={`px-2 py-0.5 rounded-full text-[9px] font-mono font-bold uppercase ${
                            exec.status === 'Completed' ? 'bg-emerald-100 text-emerald-800' :
                            exec.status === 'Failed' ? 'bg-rose-100 text-rose-800' :
                            'bg-amber-100 text-amber-800 animate-pulse'
                          }`}>
                            {exec.status}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 text-[10px] font-mono text-slate-400">
                          {new Date(exec.submitted_at || exec.created_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-3.5 text-right">
                          <button
                            onClick={() => handleSyncStatus(exec.execution_id)}
                            className="p-1 text-indigo-600 hover:bg-indigo-50 rounded transition-colors focus:outline-none"
                            title="Sync Status"
                          >
                            <RefreshCw className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
