import { 
  Building2, 
  Layers, 
  Map, 
  Cpu, 
  FileText, 
  Sparkles, 
  Download, 
  Settings as SettingsIcon,
  LogOut,
  ScanEye
} from 'lucide-react';
import { motion } from 'motion/react';

interface CreSidebarProps {
  currentView: string;
  onViewChange: (view: string) => void;
  activeWorkflows: number;
}

export default function CreSidebar({ currentView, onViewChange, activeWorkflows }: CreSidebarProps) {
  const menuItems = [
    { id: 'dashboard', label: 'Executive Dashboard', icon: Building2 },
    { id: 'projects', label: 'Projects & Workspaces', icon: Layers },
    { id: 'properties', label: 'Property Portfolios', icon: Map },
    { id: 'scans', label: 'LIDAR & Street Scans', icon: ScanEye },
    { id: 'workflows', label: 'DEV-TOOLS Orchestration', icon: Cpu, badge: activeWorkflows > 0 ? activeWorkflows : undefined },
    { id: 'concept-designs', label: 'Conceptual Designs', icon: Sparkles },
    { id: 'assets', label: 'Generated Assets', icon: Download },
    { id: 'settings', label: 'Enterprise Settings', icon: SettingsIcon },
  ];

  const currentUser = {
    name: 'Marcus Vance',
    role: 'Principal CRE Analyst',
    email: 'm.vance@wimlogic-cre.com'
  };

  return (
    <div id="cre-sidebar" className="h-full bg-slate-900 border-r border-slate-800 text-slate-300 flex flex-col justify-between select-none">
      {/* Branding Header */}
      <div>
        <div className="p-6 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-sans font-black tracking-tighter text-xl shadow-lg shadow-indigo-900/30">
              W
            </div>
            <div>
              <h1 className="font-sans font-bold tracking-tight text-white text-base leading-none">AI-CRE</h1>
              <p className="font-mono text-[9px] tracking-widest text-slate-500 uppercase mt-1">WIMLOGIC V1.0</p>
            </div>
          </div>
        </div>

        {/* Sidebar Menu Items */}
        <nav className="p-4 space-y-1.5 flex-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentView === item.id;

            return (
              <button
                key={item.id}
                id={`sidebar-item-${item.id}`}
                onClick={() => onViewChange(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-medium tracking-wide transition-all focus:outline-none relative ${
                  isActive 
                    ? 'text-white bg-slate-800/80 shadow-sm border border-slate-700/50' 
                    : 'hover:text-white hover:bg-slate-800/40 text-slate-400 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 transition-colors ${isActive ? 'text-indigo-400' : 'text-slate-500'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge !== undefined && (
                  <span className="bg-indigo-600 text-white font-mono font-bold text-[9px] px-1.5 py-0.5 rounded-full animate-pulse">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* User Block */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/40">
        <div className="flex items-center gap-3 p-2 rounded-lg">
          <div className="w-9 h-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-xs text-indigo-400 font-sans shadow-inner">
            MV
          </div>
          <div className="min-w-0 flex-1">
            <h4 className="text-xs font-bold text-white truncate leading-snug">{currentUser.name}</h4>
            <p className="text-[10px] text-slate-500 truncate leading-snug">{currentUser.role}</p>
          </div>
          <button 
            id="user-logout-btn"
            title="Disconnect Workspace"
            className="p-1.5 rounded-md hover:bg-slate-800 text-slate-500 hover:text-rose-400 transition-colors focus:outline-none"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
