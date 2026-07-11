import React, { useState, useEffect } from 'react';
import { projectService } from '../services/projectService';
import { propertyService } from '../services/propertyService';
import { workflowService } from '../services/workflowService';
import { generatedAssetService } from '../services/generatedAssetService';
import { 
  Building2, 
  FolderGit2, 
  Activity, 
  FileCheck, 
  ArrowRight, 
  Plus, 
  Cpu, 
  Sparkles 
} from 'lucide-react';
import EnterpriseCard from '../components/EnterpriseCard';
import StatusBadge from '../components/StatusBadge';
import LoadingState from '../components/LoadingState';

interface DashboardProps {
  onNavigate: (view: string) => void;
  onSelectProject: (id: string) => void;
}

export default function Dashboard({ onNavigate, onSelectProject }: DashboardProps) {
  const [stats, setStats] = useState({
    projectsCount: 0,
    propertiesCount: 0,
    activeWorkflows: 0,
    assetsCount: 0,
  });
  const [recentProjects, setRecentProjects] = useState<any[]>([]);
  const [runningExecutions, setRunningExecutions] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const [projRes, propRes, execRes, assetRes] = await Promise.all([
          projectService.list({ limit: 5 }),
          propertyService.list({ limit: 1 }),
          workflowService.listExecutions({ limit: 100 }),
          generatedAssetService.list({ limit: 1 })
        ]);

        const activeCount = execRes.items.filter(
          (ex) => ex.status === 'Running' || ex.status === 'Pending' || ex.status === 'Submitted'
        ).length;

        setStats({
          projectsCount: projRes.count,
          propertiesCount: propRes.count,
          activeWorkflows: activeCount,
          assetsCount: assetRes.count,
        });

        setRecentProjects(projRes.items.slice(0, 3));
        setRunningExecutions(
          execRes.items
            .filter((ex) => ex.status === 'Running' || ex.status === 'Pending' || ex.status === 'Submitted')
            .slice(0, 4)
        );
      } catch (err) {
        console.error('Failed to load dashboard statistics:', err);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-2xl p-6 md:p-8 text-white shadow-xl relative overflow-hidden border border-slate-800">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-[radial-gradient(circle_at_right_top,rgba(99,102,241,0.15),transparent_60%)]"></div>
        <div className="relative z-10 max-w-3xl">
          <div className="flex items-center gap-2 mb-3">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              Enterprise Suite v1.0
            </span>
          </div>
          <h1 className="font-sans font-bold text-2xl md:text-3xl tracking-tight leading-tight mb-2 text-slate-100">
            WIMLOGIC CRE AI Orchestration Hub
          </h1>
          <p className="text-sm text-slate-300 leading-relaxed max-w-2xl">
            Streamline your commercial real estate workflow. Submit physical property profiles to our devtools cloud, queue intelligence jobs, and analyze automated architectural and zoning models with complete audit trails.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              onClick={() => onNavigate('AI Orchestration')}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold tracking-wide transition-all shadow-md shadow-indigo-600/10 flex items-center gap-2 focus:outline-none cursor-pointer"
            >
              <Cpu className="w-4 h-4" />
              Generate Analysis
            </button>
            <button
              onClick={() => onNavigate('Projects')}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold tracking-wide transition-all border border-slate-700 flex items-center gap-2 focus:outline-none cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              New Project
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <EnterpriseCard className="hover:shadow-md">
          <div className="flex items-center gap-4">
            <div className="p-3.5 rounded-xl bg-indigo-50 text-indigo-600">
              <FolderGit2 className="w-6 h-6" />
            </div>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-mono">Total Projects</p>
              <h3 className="text-2xl font-bold text-slate-800 mt-0.5">{stats.projectsCount}</h3>
            </div>
          </div>
        </EnterpriseCard>

        <EnterpriseCard className="hover:shadow-md">
          <div className="flex items-center gap-4">
            <div className="p-3.5 rounded-xl bg-emerald-50 text-emerald-600">
              <Building2 className="w-6 h-6" />
            </div>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-mono">Managed Properties</p>
              <h3 className="text-2xl font-bold text-slate-800 mt-0.5">{stats.propertiesCount}</h3>
            </div>
          </div>
        </EnterpriseCard>

        <EnterpriseCard className="hover:shadow-md">
          <div className="flex items-center gap-4">
            <div className="p-3.5 rounded-xl bg-amber-50 text-amber-600">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-mono">Running Jobs</p>
              <h3 className="text-2xl font-bold text-slate-800 mt-0.5">{stats.activeWorkflows}</h3>
            </div>
          </div>
        </EnterpriseCard>

        <EnterpriseCard className="hover:shadow-md">
          <div className="flex items-center gap-4">
            <div className="p-3.5 rounded-xl bg-blue-50 text-blue-600">
              <FileCheck className="w-6 h-6" />
            </div>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-mono">Generated Assets</p>
              <h3 className="text-2xl font-bold text-slate-800 mt-0.5">{stats.assetsCount}</h3>
            </div>
          </div>
        </EnterpriseCard>
      </div>

      {/* Main Panel Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Projects list */}
        <div className="lg:col-span-2">
          <EnterpriseCard
            title="Recent Projects"
            headerAction={
              <button
                onClick={() => onNavigate('Projects')}
                className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold flex items-center gap-1.5 focus:outline-none"
              >
                View All <ArrowRight className="w-3.5 h-3.5" />
              </button>
            }
          >
            {isLoading ? (
              <LoadingState type="rows" rowsCount={3} />
            ) : recentProjects.length === 0 ? (
              <div className="py-12 text-center text-slate-400 text-xs font-mono">NO PROJECTS CREATED YET</div>
            ) : (
              <div className="space-y-4">
                {recentProjects.map((proj) => (
                  <div
                    key={proj.id}
                    className="group border border-slate-100 hover:border-slate-200 rounded-lg p-4 hover:bg-slate-50 transition-all flex justify-between items-center"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 bg-slate-100 rounded text-[10px] font-mono font-bold text-slate-500 uppercase">
                          {proj.project_id}
                        </span>
                        <h4 className="font-sans font-bold text-slate-800 text-sm group-hover:text-indigo-600 transition-colors">
                          {proj.project_name}
                        </h4>
                      </div>
                      <p className="text-xs text-slate-400 line-clamp-1 max-w-md leading-relaxed">
                        {proj.description || 'No description provided.'}
                      </p>
                    </div>
                    <button
                      onClick={() => {
                        onSelectProject(proj.project_id);
                        onNavigate('Properties');
                      }}
                      className="p-1.5 bg-slate-50 group-hover:bg-indigo-600 group-hover:text-white rounded-lg text-slate-400 transition-all focus:outline-none cursor-pointer animate-fade-in"
                    >
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </EnterpriseCard>
        </div>

        {/* Workflow monitor queue */}
        <div>
          <EnterpriseCard
            title="Active Job Queue"
            headerAction={
              <button
                onClick={() => onNavigate('Workflow Results')}
                className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold flex items-center gap-1.5 focus:outline-none"
              >
                Monitor <ArrowRight className="w-3.5 h-3.5" />
              </button>
            }
          >
            {isLoading ? (
              <LoadingState message="Loading job queue..." />
            ) : runningExecutions.length === 0 ? (
              <div className="py-16 text-center text-slate-400 flex flex-col items-center justify-center space-y-3">
                <Sparkles className="w-8 h-8 text-indigo-200" />
                <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Queue is idle</span>
              </div>
            ) : (
              <div className="space-y-4">
                {runningExecutions.map((exec) => (
                  <div
                    key={exec.execution_id}
                    className="border-l-2 border-indigo-500 bg-slate-50/50 p-3.5 rounded-r-lg space-y-2 border border-slate-100"
                  >
                    <div className="flex justify-between items-center">
                      <span className="font-mono text-xs font-bold text-slate-700">
                        {exec.execution_number}
                      </span>
                      <StatusBadge status={exec.status} type="workflow" />
                    </div>
                    <div className="text-xs text-slate-600 font-sans">
                      Pipeline: <span className="font-mono font-bold text-indigo-600">{exec.workflow_code}</span>
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono">
                      Started: {new Date(exec.submitted_at || exec.created_at).toLocaleTimeString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </EnterpriseCard>
        </div>
      </div>
    </div>
  );
}
