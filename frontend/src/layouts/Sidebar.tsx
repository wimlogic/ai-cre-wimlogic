import React from 'react';
import { 
  LayoutDashboard, 
  FolderOpen, 
  Building2, 
  Camera, 
  Cpu, 
  ClipboardList, 
  FileCheck, 
  Settings as SettingsIcon,
  ChevronRight,
  X
} from 'lucide-react';
import { AppConfig } from '../config/app';

// Customized high-fidelity SVG icon for the WIMLOGIC brand logo (recreated from the uploaded design)
export function WimLogicLogo({ className = 'w-8 h-8' }: { className?: string }) {
  return (
    <svg 
      viewBox="0 0 100 100" 
      className={className} 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      id="wimlogic-brand-logo"
    >
      <defs>
        {/* Teal ribbon gradient */}
        <linearGradient id="wimTealGrad" x1="0" y1="0" x2="100" y2="100">
          <stop offset="0%" stopColor="#81b29a" />
          <stop offset="50%" stopColor="#3d5a80" />
          <stop offset="100%" stopColor="#293241" />
        </linearGradient>
        {/* Shimmer gradient for 3D ribbon look */}
        <linearGradient id="wimTealShine" x1="0" y1="0" x2="0" y2="100">
          <stop offset="0%" stopColor="#80ced7" />
          <stop offset="60%" stopColor="#4895ef" />
          <stop offset="100%" stopColor="#3f37c9" />
        </linearGradient>
        {/* Central orange pillar gradient */}
        <linearGradient id="wimOrangeGrad" x1="0" y1="0" x2="0" y2="100">
          <stop offset="0%" stopColor="#ffb703" />
          <stop offset="100%" stopColor="#fb8500" />
        </linearGradient>
      </defs>

      {/* Left wave/ribbon (representing 'W') */}
      <path 
        d="M 12 55 C 8 38, 22 36, 26 50 C 31 66, 38 82, 44 86 C 41 72, 28 42, 24 44 C 18 47, 10 50, 10 54" 
        fill="url(#wimTealShine)" 
        opacity="0.9"
      />
      <path 
        d="M 10 52 C 10 40, 20 40, 26 55 C 32 70, 42 75, 46 80 L 46 86 C 36 84, 25 65, 18 58 C 14 54, 10 53, 10 52 Z" 
        fill="url(#wimTealGrad)" 
      />

      {/* Central Orange Pillar (representing 'I' / Person) */}
      {/* Pillar body */}
      <rect 
        x="43" 
        y="23" 
        width="10" 
        height="64" 
        rx="5" 
        fill="url(#wimOrangeGrad)" 
      />
      {/* Pillar top circular dot/head */}
      <circle 
        cx="48" 
        cy="13" 
        r="5.5" 
        fill="url(#wimOrangeGrad)" 
      />

      {/* Right wave/ribbon (representing 'M') */}
      <path 
        d="M 52 28 C 54 36, 62 60, 68 76 C 74 60, 84 32, 90 32 C 94 32, 92 46, 88 56 C 82 72, 74 78, 66 78 C 58 78, 54 50, 52 28 Z" 
        fill="url(#wimTealGrad)" 
      />
      <path 
        d="M 52 28 C 53 45, 62 76, 67 78 C 65 72, 59 40, 53 30 C 52 29, 52 28, 52 28 Z" 
        fill="url(#wimTealShine)" 
        opacity="0.8"
      />

      {/* Trademark "tm" text symbol */}
      <text 
        x="90" 
        y="12" 
        fill="#3d5a80" 
        fontSize="8" 
        fontWeight="bold" 
        fontFamily="sans-serif"
      >
        tm
      </text>
    </svg>
  );
}

export interface SidebarProps {
  currentView: string;
  onNavigate: (view: string) => void;
  selectedProjectId?: string;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

export default function Sidebar({
  currentView,
  onNavigate,
  selectedProjectId,
  isMobileOpen,
  onCloseMobile,
}: SidebarProps) {
  const navigationItems = [
    { id: 'Dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'Projects', label: 'Projects', icon: FolderOpen },
    { id: 'Properties', label: 'Properties', icon: Building2 },
    { id: 'Property Images', label: 'Property Images', icon: Camera },
    { id: 'AI Orchestration', label: 'AI Orchestration', icon: Cpu },
    { id: 'Workflow Results', label: 'Workflow Results', icon: ClipboardList },
    { id: 'Generated Assets', label: 'Generated Assets', icon: FileCheck },
    { id: 'Settings', label: 'Settings', icon: SettingsIcon },
  ];

  return (
    <>
      <aside
        id="enterprise-sidebar-panel"
        className={`
          fixed lg:static inset-y-0 left-0 z-40 bg-slate-900 text-white w-64 p-5 flex flex-col justify-between border-r border-slate-800 shadow-xl lg:shadow-none transition-transform duration-300 shrink-0
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        <div className="space-y-6">
          {/* Logo & Header */}
          <div className="flex items-center justify-between pb-4 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-slate-800 flex items-center justify-center shadow-inner">
                <WimLogicLogo className="w-7 h-7" />
              </div>
              <div>
                <span className="block font-sans font-black tracking-widest text-xs uppercase text-slate-100">
                  WIMLOGIC
                </span>
                <span className="block text-[9px] font-mono font-bold text-indigo-400 tracking-wider mt-0.5">
                  AI-CRE PLATFORM
                </span>
              </div>
            </div>
            <button
              onClick={onCloseMobile}
              className="lg:hidden p-1 text-slate-400 hover:text-white rounded-lg focus:outline-none"
              id="close-sidebar-mobile-btn"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1.5" id="sidebar-navigation">
            {navigationItems.map((item) => {
              const isActive = currentView === item.id;
              const IconComponent = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    onNavigate(item.id);
                    onCloseMobile();
                  }}
                  id={`sidebar-nav-${item.id.toLowerCase().replace(/\s+/g, '-')}`}
                  className={`
                    w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-semibold tracking-wide transition-all focus:outline-none group
                    ${isActive 
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/10' 
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/65'}
                  `}
                >
                  <div className="flex items-center gap-3">
                    <IconComponent
                      className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-slate-400 group-hover:text-slate-200'}`}
                    />
                    <span>{item.label}</span>
                  </div>
                  {isActive && <ChevronRight className="w-3.5 h-3.5 text-white animate-fade-in" />}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Sidebar Footer Context */}
        <div className="pt-4 border-t border-slate-800 space-y-2">
          {selectedProjectId && (
            <div className="bg-slate-800/40 border border-slate-800 rounded-lg p-2.5">
              <span className="block text-[8px] font-bold uppercase tracking-widest text-slate-500 font-mono">
                ACTIVE PROJECT
              </span>
              <span className="block font-mono text-[10px] font-bold text-indigo-400 mt-0.5">
                {selectedProjectId}
              </span>
            </div>
          )}
          <div className="text-[9px] font-mono text-slate-500 text-center uppercase tracking-widest">
            v{AppConfig.version || '1.0.0'} • CLIENT HANDSHAKE
          </div>
        </div>
      </aside>

      {/* Backdrop for Mobile Drawer */}
      {isMobileOpen && (
        <div
          id="sidebar-mobile-backdrop"
          onClick={onCloseMobile}
          className="fixed inset-0 bg-black/60 z-30 lg:hidden backdrop-blur-xs transition-opacity duration-200"
        ></div>
      )}
    </>
  );
}
