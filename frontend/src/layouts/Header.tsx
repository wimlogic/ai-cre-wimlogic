import React from 'react';
import { Menu, User, Bell } from 'lucide-react';
import { WimLogicLogo } from './Sidebar';

export interface HeaderProps {
  currentView: string;
  onOpenMobile: () => void;
  id?: string;
}

export default function Header({ currentView, onOpenMobile, id }: HeaderProps) {
  // Personalized email from system context
  const userEmail = 'timg@kshoesusa.com';

  return (
    <header
      id={id || 'enterprise-header-panel'}
      className="bg-white border-b border-slate-200/80 h-16 flex items-center justify-between px-4 sm:px-6 md:px-8 shrink-0 select-none z-20 shadow-xs"
    >
      <div className="flex items-center gap-3">
        {/* Mobile menu toggle */}
        <button
          onClick={onOpenMobile}
          className="lg:hidden p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-50 rounded-lg transition-colors focus:outline-none"
          id="open-sidebar-mobile-btn"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Small branding for mobile */}
        <div className="flex lg:hidden items-center gap-2">
          <WimLogicLogo className="w-5 h-5" />
          <span className="font-sans font-black tracking-widest text-[10px] text-slate-900 uppercase">
            WIMLOGIC
          </span>
        </div>

        {/* Active Page Title - Desktop only */}
        <div className="hidden lg:block space-y-0.5">
          <h1 className="text-sm font-bold text-slate-900 tracking-tight uppercase font-mono">
            {currentView}
          </h1>
          <p className="text-[10px] text-slate-400 font-mono tracking-wider">
            AI-CRE ORCHESTRATION CLIENT
          </p>
        </div>
      </div>

      {/* User profile and system icons */}
      <div className="flex items-center gap-4">
        {/* Active view name on mobile */}
        <span className="lg:hidden text-xs font-bold text-slate-800 font-mono tracking-wide uppercase">
          {currentView}
        </span>

        <div className="flex items-center gap-3">
          {/* Notifications Placeholder */}
          <button className="hidden sm:flex p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-50 transition-colors relative">
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-indigo-500 rounded-full" />
          </button>

          {/* User badge */}
          <div className="flex items-center gap-2 border-l border-slate-100 pl-3">
            <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 border border-slate-200 shrink-0">
              <User className="w-4 h-4" />
            </div>
            <div className="hidden sm:block text-left">
              <span className="block text-[10px] font-bold text-slate-700 tracking-wide">
                Tim G.
              </span>
              <span className="block text-[9px] font-mono text-slate-400">
                {userEmail}
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
