import { useEffect, useState } from 'react';
import { 
  Building2, 
  Layers, 
  Cpu, 
  CircleDollarSign, 
  ArrowRight, 
  Activity, 
  TrendingUp, 
  Clock, 
  CheckCircle2, 
  AlertCircle 
} from 'lucide-react';
import { CreStats, CreProject, CreProperty, ApiUsageLog } from '../types';
import { CreApi } from '../lib/api';

interface CreDashboardProps {
  onNavigate: (view: string) => void;
  onSelectProject: (projectId: string) => void;
}

export default function CreDashboard({ onNavigate, onSelectProject }: CreDashboardProps) {
  const [stats, setStats] = useState<CreStats | null>(null);
  const [projects, setProjects] = useState<CreProject[]>([]);
  const [properties, setProperties] = useState<CreProperty[]>([]);
  const [apiLogs, setApiLogs] = useState<ApiUsageLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboardData() {
      try {
        setLoading(true);
        const [statsRes, projRes, propRes, logsRes] = await Promise.all([
          CreApi.getStats(),
          CreApi.getProjects(),
          CreApi.getProperties(),
          CreApi.getApiLogs()
        ]);
        
        if (statsRes.status === 200) setStats(statsRes.data);
        setProjects(projRes.items.slice(0, 3));
        setProperties(propRes.items.slice(0, 4));
        setApiLogs(logsRes.items.slice(0, 5));
      } catch (err) {
        console.error("Failed to load dashboard parameters:", err);
      } finally {
        setLoading(false);
      }
    }
    loadDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <div className="w-8 h-8 rounded-full border-2 border-slate-200 border-t-indigo-600 animate-spin"></div>
        <p className="font-mono text-[10px] tracking-widest text-slate-400 uppercase">Synchronizing Executive Core...</p>
      </div>
    );
  }

  const cards = [
    {
      id: 'stat-projects',
      title: 'Active Workspaces',
      value: stats?.totalProjects || 0,
      description: 'Regional research corridors',
      icon: Layers,
      color: 'from-blue-500/10 to-indigo-500/5',
      iconColor: 'text-blue-500'
    },
    {
      id: 'stat-properties',
      title: 'Registered Properties',
      value: stats?.totalProperties || 0,
      description: 'Assessor parcel registry',
      icon: Building2,
      color: 'from-emerald-500/10 to-teal-500/5',
      iconColor: 'text-emerald-500'
    },
    {
      id: 'stat-workflows',
      title: 'Active Pipelines',
      value: stats?.activeWorkflows || 0,
      description: 'DEV-TOOLS orchestrations',
      icon: Cpu,
      color: 'from-indigo-500/10 to-purple-500/5',
      iconColor: 'text-indigo-500',
      pulse: (stats?.activeWorkflows || 0) > 0
    },
    {
      id: 'stat-api-cost',
      title: 'Cumulative API Expenses',
      value: `$${(stats?.apiUsageCost || 0).toFixed(2)}`,
      description: 'MLS & Google Maps tokens',
      icon: CircleDollarSign,
      color: 'from-amber-500/10 to-orange-500/5',
      iconColor: 'text-amber-500'
    }
  ];

  return (
    <div className="space-y-8">
      {/* Upper Title Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="font-sans text-2xl font-semibold tracking-tight text-slate-900">Executive Intelligence Dashboard</h2>
          <p className="text-slate-500 text-xs mt-1">
            Real-time Commercial Real Estate (CRE) analysis portfolio and DEV-TOOLS agent orchestration metrics.
          </p>
        </div>
        <div className="flex items-center gap-2 font-mono text-[11px] text-slate-500 bg-slate-100 border border-slate-200/60 rounded-full px-3 py-1.5 self-start md:self-auto shadow-sm">
          <Activity className="w-3.5 h-3.5 text-indigo-500 animate-pulse" />
          <span>PORTAL: SECURED</span>
        </div>
      </div>

      {/* Bento Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <div 
              key={card.id} 
              id={card.id}
              className={`bg-white border border-slate-100 p-5 rounded-xl shadow-sm hover:shadow-md/5 transition-all flex items-start justify-between relative overflow-hidden`}
            >
              <div className="space-y-2">
                <span className="text-[10px] font-bold font-sans text-slate-400 tracking-wider uppercase block">{card.title}</span>
                <span className="text-2xl font-sans font-semibold tracking-tight text-slate-800 block">{card.value}</span>
                <span className="text-[11px] text-slate-500 block">{card.description}</span>
              </div>
              <div className={`p-2.5 rounded-lg bg-slate-50 ${card.iconColor}`}>
                <Icon className={`w-5 h-5 ${card.pulse ? 'animate-bounce' : ''}`} />
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Projects Corridors */}
        <div className="lg:col-span-2 bg-white border border-slate-100 rounded-xl shadow-sm p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <Layers className="w-4.5 h-4.5 text-indigo-500" />
              <h3 className="font-sans text-sm font-semibold text-slate-800">Active Strategic Workspaces</h3>
            </div>
            <button 
              id="goto-projects-btn"
              onClick={() => onNavigate('projects')}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1 transition-colors"
            >
              <span>View All</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="space-y-3.5">
            {projects.map((proj) => (
              <div 
                key={proj.id}
                className="border border-slate-100 p-4 rounded-lg hover:border-slate-200 hover:bg-slate-50/40 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="bg-slate-100 border border-slate-200/60 font-mono text-[9px] text-slate-600 px-1.5 py-0.5 rounded uppercase font-bold">
                      {proj.project_id}
                    </span>
                    <h4 className="font-sans text-xs font-bold text-slate-800 truncate">{proj.project_name}</h4>
                  </div>
                  <p className="text-slate-500 text-[11px] truncate">{proj.description}</p>
                </div>
                <div className="flex items-center gap-3.5 shrink-0 self-end md:self-auto">
                  <div className="text-right">
                    <span className="text-[10px] text-slate-400 block font-mono">BOUNDS</span>
                    <span className="text-[11px] font-medium text-slate-700 block">
                      {proj.main_street ? `${proj.beginning_address}-${proj.ending_address} ${proj.main_street}` : 'Unbounded'}
                    </span>
                  </div>
                  <button
                    id={`select-project-${proj.project_id}`}
                    onClick={() => {
                      onSelectProject(proj.project_id);
                      onNavigate('properties');
                    }}
                    className="p-1.5 bg-slate-50 hover:bg-indigo-50 border border-slate-100 text-slate-600 hover:text-indigo-600 rounded transition-colors"
                  >
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* API Usage & Cost Logger */}
        <div className="bg-white border border-slate-100 rounded-xl shadow-sm p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4.5 h-4.5 text-amber-500" />
              <h3 className="font-sans text-sm font-semibold text-slate-800">Dynamic API Token Log</h3>
            </div>
          </div>

          <div className="space-y-3">
            {apiLogs.map((log) => (
              <div 
                key={log.id}
                className="flex items-center justify-between border-b border-slate-100/60 last:border-0 pb-2.5 last:pb-0"
              >
                <div>
                  <span className="text-xs font-semibold text-slate-800 block leading-tight">{log.api_name}</span>
                  <span className="text-[10px] text-slate-400 font-mono block leading-none mt-1 uppercase">{log.provider}</span>
                </div>
                <div className="text-right">
                  <span className="text-xs font-bold text-slate-700 block">${log.estimated_cost?.toFixed(3)}</span>
                  <span className="text-[9px] text-slate-400 block font-mono mt-0.5">{log.request_count} reqs</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Row Portfolio Targets */}
      <div className="bg-white border border-slate-100 rounded-xl shadow-sm p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Building2 className="w-4.5 h-4.5 text-emerald-500" />
            <h3 className="font-sans text-sm font-semibold text-slate-800">High-Yield Portfolio Pipeline</h3>
          </div>
          <button 
            id="goto-properties-btn"
            onClick={() => onNavigate('properties')}
            className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1 transition-colors"
          >
            <span>Manage Registry</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {properties.map((prop) => (
            <div 
              key={prop.id}
              className="border border-slate-100 p-4 rounded-xl hover:bg-slate-50/40 transition-all space-y-3"
            >
              <div className="space-y-1">
                <span className="text-[9px] font-mono font-bold tracking-wider text-indigo-500 uppercase block">
                  {prop.property_uid}
                </span>
                <h4 className="text-xs font-bold text-slate-800 truncate leading-tight">{prop.display_address}</h4>
                <p className="text-[10px] text-slate-400 truncate leading-none">{prop.city}, {prop.state}</p>
              </div>

              <div className="grid grid-cols-2 gap-2 border-t border-b border-slate-100/80 py-2.5 font-mono text-[10px] text-slate-500">
                <div>
                  <span className="text-slate-400 block text-[9px] leading-none uppercase">Assessed</span>
                  <span className="font-semibold text-slate-700 block mt-0.5">
                    ${((prop.total_assessed_value || 0) / 1000000).toFixed(2)}M
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[9px] leading-none uppercase">Zoning</span>
                  <span className="font-semibold text-slate-700 block mt-0.5">{prop.zoning_code}</span>
                </div>
              </div>

              <div className="flex items-center justify-between text-[11px]">
                <span className={`px-2 py-0.5 rounded-full font-medium ${
                  prop.status === 'approved' 
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' 
                    : 'bg-amber-50 text-amber-700 border border-amber-100'
                }`}>
                  {prop.status === 'approved' ? 'Ready' : 'Under Review'}
                </span>
                <span className="font-mono font-medium text-slate-400 text-[10px]">APN: {prop.apn?.split('-')[0]}...</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
