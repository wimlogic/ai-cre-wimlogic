import React, { useState } from 'react';
import Sidebar from './Sidebar';
import Header from './Header';

export interface EnterpriseLayoutProps {
  children: React.ReactNode;
  currentView: string;
  onNavigate: (view: string) => void;
  selectedProjectId?: string;
  id?: string;
}

export default function EnterpriseLayout({
  children,
  currentView,
  onNavigate,
  selectedProjectId,
  id,
}: EnterpriseLayoutProps) {
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <div
      id={id || 'enterprise-layout-root'}
      className="min-h-screen flex flex-col bg-slate-50/50 text-slate-800 antialiased font-sans"
    >
      <div className="flex-1 flex overflow-hidden relative">
        {/* Navigation Sidebar */}
        <Sidebar
          currentView={currentView}
          onNavigate={onNavigate}
          selectedProjectId={selectedProjectId}
          isMobileOpen={isMobileOpen}
          onCloseMobile={() => setIsMobileOpen(false)}
        />

        {/* Content Panel Frame */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Main Top Header */}
          <Header
            currentView={currentView}
            onOpenMobile={() => setIsMobileOpen(true)}
          />

          {/* Scrolling Content viewport */}
          <main className="flex-1 overflow-y-auto bg-slate-50/30 p-4 sm:p-6 md:p-8">
            <div className="max-w-7xl mx-auto w-full animate-fade-in">
              {children}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
