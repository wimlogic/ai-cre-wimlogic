import React, { useEffect, useState } from 'react';
import { 
  Cpu, 
  Clock, 
  CheckCircle2, 
  AlertCircle, 
  ChevronRight, 
  Activity, 
  Compass, 
  ListTodo, 
  RefreshCw, 
  ArrowRight,
  TrendingUp,
  ScanEye,
  Zap,
  DollarSign
} from 'lucide-react';
import { CreWorkflowExecution, CreWorkflowEvent, CreWorkflowResult, CreScan } from '../types';
import { CreApi } from '../lib/api';

export default function CreWorkflowScheduler() {
  const [executions, setExecutions] = useState<CreWorkflowExecution[]>([]);
  const [scans, setScans] = useState<CreScan[]>([]);
  const [selectedExecution, setSelectedExecution] = useState<(CreWorkflowExecution & { events: CreWorkflowEvent[]; result?: CreWorkflowResult }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadWorkflowData = async () => {
    try {
      setLoading(true);
      const [wfRes, scanRes] = await Promise.all([
        CreApi.getWorkflows(),
        CreApi.getScans()
      ]);
      setExecutions(wfRes.items);
      setScans(scanRes.items);

      // If an execution is selected, update its detailed info
      if (selectedExecution) {
        const details = await CreApi.getWorkflowDetails(selectedExecution.execution_id);
        setSelectedExecution(details);
      } else if (wfRes.items.length > 0) {
        // Default to select first execution
        const details = await CreApi.getWorkflowDetails(wfRes.items[0].execution_id);
        setSelectedExecution(details);
      }
    } catch (err) {
      console.error("Failed to load workflow scheduler elements:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWorkflowData();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadWorkflowData();
    setRefreshing(false);
  };

  const handleSelectExecution = async (exec: CreWorkflowExecution) => {
    try {
      const details = await CreApi.getWorkflowDetails(exec.execution_id);
      setSelectedExecution(details);
    } catch (err) {
      console.error("Failed to fetch detailed workflow logs:", err);
    }
  };

  const handleTriggerScan = async (scanId: number) => {
    try {
      const res = await CreApi.executeScan(scanId);
      if (res.success) {
        // Refresh list
        await loadWorkflowData();
      }
    } catch (err) {
      console.error("Failed to simulate street sweep execution:", err);
    }
  };

  // Decode JSON outputs
  const renderResultData = (result: CreWorkflowResult) => {
    try {
      const parsed = JSON.parse(result.response_json || '{}');
      return (
        <div className="space-y-4 font-sans text-xs text-slate-700">
          <div className="grid grid-cols-2 gap-4">
            <div className="border border-slate-100 p-3.5 rounded-xl bg-slate-50/50 space-y-1">
              <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-slate-400 block">Feasibility Score</span>
              <div className="flex items-center gap-1.5">
                <TrendingUp className="w-4.5 h-4.5 text-indigo-500" />
                <span className="text-sm font-bold text-slate-800">{parsed.score || 85}/100</span>
              </div>
            </div>
            <div className="border border-slate-100 p-3.5 rounded-xl bg-slate-50/50 space-y-1">
              <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-slate-400 block">Estimated IRR %</span>
              <div className="flex items-center gap-1.5">
                <DollarSign className="w-4.5 h-4.5 text-emerald-500" />
                <span className="text-sm font-bold text-slate-800">{parsed.financial?.irr || '20.4%'}</span>
              </div>
            </div>
          </div>

          <div className="border border-slate-100 p-4 rounded-xl bg-slate-50/20 space-y-2">
            <span className="text-[10px] font-bold text-indigo-600 font-mono tracking-wider block uppercase">zoning & overlay notes</span>
            <p className="leading-relaxed">{parsed.zoning || 'Zoning ordinances allow high-density residential adaptive reuse.'}</p>
          </div>

          <div className="border border-slate-100 p-4 rounded-xl bg-indigo-50/20 space-y-2">
            <span className="text-[10px] font-bold text-indigo-600 font-mono tracking-wider block uppercase">investor recommendation</span>
            <p className="leading-relaxed">{parsed.recommendation || 'Proceed with Schematic designs.'}</p>
          </div>
        </div>
      );
    } catch (e) {
      return <pre className="font-mono text-[10px] bg-slate-50 p-4 rounded-lg overflow-x-auto">{result.response_json}</pre>;
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-sans text-2xl font-semibold tracking-tight text-slate-900">DEV-TOOLS Orchestration Center</h2>
          <p className="text-slate-500 text-xs mt-1">
            Schedule future sweeps, monitor live agent handshake logs, and review completed Feasibility summaries.
          </p>
        </div>
        <button
          id="refresh-scheduler-btn"
          onClick={handleRefresh}
          className="flex items-center gap-2 px-3.5 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-sans font-medium text-xs rounded-lg transition-colors focus:outline-none"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${refreshing ? 'animate-spin' : ''}`} />
          <span>Refresh Queue</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Executions Left Hand column */}
        <div className="lg:col-span-1 space-y-6">
          {/* Active GIS / LIDAR Sweeper Section */}
          <div className="bg-white border border-slate-100 rounded-xl shadow-sm overflow-hidden p-5 space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-100 pb-2.5">
              <ScanEye className="w-4.5 h-4.5 text-amber-500 animate-pulse" />
              <h3 className="font-sans text-xs font-bold text-slate-800 uppercase tracking-wider">LIDAR Street-Sweeps</h3>
            </div>

            <div className="space-y-3">
              {scans.map((scan) => (
                <div 
                  key={scan.id}
                  className="border border-slate-100 p-3.5 rounded-lg space-y-3.5 bg-slate-50/30"
                >
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="bg-amber-50 text-amber-700 border border-amber-100 font-mono text-[8px] font-bold px-1.5 py-0.2 rounded uppercase">
                        {scan.scan_uid}
                      </span>
                      <span className={`px-2 py-0.2 rounded-full font-mono text-[9px] font-bold ${
                        scan.status === 'complete' 
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' 
                          : 'bg-amber-50 text-amber-700 border border-amber-100 animate-pulse'
                      }`}>
                        {scan.status}
                      </span>
                    </div>
                    <span className="text-xs font-bold text-slate-800 block">
                      {scan.start_address}-{scan.end_address} {scan.main_street}
                    </span>
                    <span className="text-[9px] text-slate-400 font-mono block">City: {scan.city}, {scan.state}</span>
                  </div>

                  {scan.status !== 'complete' && (
                    <button
                      id={`simulate-sweep-${scan.id}`}
                      onClick={() => handleTriggerScan(scan.id)}
                      className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 hover:text-indigo-600 border border-slate-200 font-sans font-medium text-[11px] rounded transition-all focus:outline-none"
                    >
                      <Zap className="w-3.5 h-3.5 text-amber-500" />
                      <span>Execute Mobile Sweeper Unit</span>
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Workflow Queue */}
          <div className="bg-white border border-slate-100 rounded-xl shadow-sm overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-100 bg-slate-50/50">
              <h3 className="text-xs font-bold font-sans text-slate-400 uppercase tracking-wider">Agent Pipelines Queue ({executions.length})</h3>
            </div>
            <div className="divide-y divide-slate-100 max-h-[400px] overflow-y-auto">
              {executions.map((exec) => {
                const isSelected = selectedExecution?.execution_id === exec.execution_id;
                return (
                  <div
                    key={exec.execution_id}
                    id={`execution-row-${exec.execution_id}`}
                    onClick={() => handleSelectExecution(exec)}
                    className={`p-4 cursor-pointer transition-all flex items-start justify-between gap-3 relative ${
                      isSelected ? 'bg-indigo-50/40 border-l-2 border-indigo-600' : 'hover:bg-slate-50/40'
                    }`}
                  >
                    <div className="space-y-1.5 min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="bg-slate-100 font-mono text-[8px] font-bold text-slate-500 px-1 py-0.2 rounded uppercase border border-slate-200/50">
                          {exec.execution_number}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">PRIORITY: {exec.priority}</span>
                      </div>
                      <h4 className="font-sans text-xs font-bold text-slate-800 truncate">{exec.workflow_code}</h4>
                      <p className="text-[9px] text-slate-400 font-mono leading-none">Submitted: {exec.submitted_at}</p>
                    </div>
                    <div className="shrink-0 self-center">
                      <span className={`px-2 py-0.5 rounded-full font-sans text-[9px] font-bold ${
                        exec.status === 'Completed' 
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' 
                          : exec.status === 'Running'
                          ? 'bg-indigo-50 text-indigo-700 border border-indigo-100 animate-pulse'
                          : 'bg-slate-50 text-slate-700 border border-slate-100'
                      }`}>
                        {exec.status}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Selected Execution Logs / Outputs Panel */}
        <div className="lg:col-span-2 space-y-6">
          {selectedExecution ? (
            <>
              {/* Summary Block */}
              <div className="bg-white border border-slate-100 rounded-xl shadow-sm p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="bg-indigo-600 font-mono text-[9px] text-white font-bold px-2 py-0.5 rounded uppercase">
                        {selectedExecution.execution_number}
                      </span>
                      <span className="text-slate-400 font-mono text-xs">DEV-ID: {selectedExecution.devtools_execution_id}</span>
                    </div>
                    <h3 className="font-sans text-base font-bold text-slate-900 leading-tight">
                      {selectedExecution.workflow_code}
                    </h3>
                  </div>

                  <span className={`px-3 py-1 rounded-full font-sans text-xs font-bold ${
                    selectedExecution.status === 'Completed' 
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' 
                      : 'bg-indigo-50 text-indigo-700 border border-indigo-100 animate-pulse'
                  }`}>
                    {selectedExecution.status}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-4 font-mono text-[10px] text-slate-500 border-b border-slate-100 pb-4">
                  <div>
                    <span className="text-slate-400 block text-[9px] uppercase">PIPELINE VERSION</span>
                    <span className="font-bold text-slate-800 block mt-0.5">{selectedExecution.workflow_version}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[9px] uppercase">SUBMITTED TIME</span>
                    <span className="font-bold text-slate-800 block mt-0.5">{selectedExecution.submitted_at}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[9px] uppercase">COMPLETED TIME</span>
                    <span className="font-bold text-slate-800 block mt-0.5">{selectedExecution.completed_at || 'In-queue'}</span>
                  </div>
                </div>

                {/* Structured Outputs Block */}
                <div className="space-y-3">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block font-sans">Structured Output Payload</span>
                  {selectedExecution.result ? (
                    renderResultData(selectedExecution.result)
                  ) : (
                    <div className="py-12 text-center text-slate-400 text-xs border border-dashed border-slate-200 rounded-xl bg-slate-50/50 flex flex-col items-center justify-center space-y-2">
                      <Clock className="w-5 h-5 text-indigo-500 animate-spin" />
                      <div>
                        <span className="font-sans font-bold text-slate-700 block">Agent Pipeline Executing...</span>
                        <span className="text-[10px] mt-0.5 block">Waiting for response payload from separate DEV-TOOLS orchestrator.</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Handshake Events Timber logs */}
              <div className="bg-white border border-slate-100 rounded-xl shadow-sm p-6 space-y-4">
                <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                  <Activity className="w-4.5 h-4.5 text-indigo-500 animate-pulse" />
                  <h3 className="font-sans text-sm font-semibold text-slate-800">Agent Handshake Handover Logs</h3>
                </div>

                <div className="space-y-4 relative before:absolute before:left-[17px] before:top-2 before:bottom-2 before:w-[1px] before:bg-slate-100">
                  {selectedExecution.events.map((ev) => (
                    <div key={ev.event_id} className="flex gap-4 items-start relative">
                      <div className="w-9 h-9 rounded-full bg-slate-50 border border-slate-100 flex items-center justify-center text-indigo-600 font-bold text-xs shrink-0 z-10 shadow-sm">
                        {ev.event_type.slice(0, 2).toUpperCase()}
                      </div>
                      <div className="space-y-1 min-w-0 flex-1">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-slate-800">{ev.event_type}</span>
                          <span className="font-mono text-[9px] text-slate-400">{ev.created_at}</span>
                        </div>
                        <p className="text-slate-500 text-xs leading-relaxed">{ev.message}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="bg-white border border-slate-100 rounded-xl shadow-sm p-12 text-center text-slate-400 text-xs flex flex-col items-center justify-center space-y-3">
              <Cpu className="w-8 h-8 text-slate-300" />
              <span>Select an active execution to browse live agent handshakes and response metrics.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
