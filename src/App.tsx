import { useState, useEffect } from 'react';
import { CreStats } from './types';
import { CreApi } from './lib/api';
import CreSidebar from './components/CreSidebar';
import CreDashboard from './components/CreDashboard';
import CreProjects from './components/CreProjects';
import CreProperties from './components/CreProperties';
import CreWorkflowScheduler from './components/CreWorkflowScheduler';
import CreConceptDesign from './components/CreConceptDesign';
import CreGeneratedAssets from './components/CreGeneratedAssets';
import CreSettings from './components/CreSettings';
import OfflineIndicator from './components/OfflineIndicator';
import { RefreshCw, Menu, X } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

export default function App() {
  const [currentView, setCurrentView] = useState<string>('dashboard');
  const [selectedProjectId, setSelectedProjectId] = useState<string>('PRJ-9021-LA');
  const [stats, setStats] = useState<CreStats | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  // Sync and poll stats
  const fetchStats = async () => {
    try {
      const statsRes = await CreApi.getStats();
      if (statsRes.status === 200) {
        setStats(statsRes.data);
      }
    } catch (err) {
      console.error("Enterprise metrics handshake failure:", err);
    }
  };

  useEffect(() => {
    async function loadInitialData() {
      setIsLoading(true);
      await fetchStats();
      setIsLoading(false);
    }
    loadInitialData();

    // Set up standard 5-second poll sequence to simulate async pipeline updates
    const pollInterval = setInterval(fetchStats, 5000);
    return () => clearInterval(pollInterval);
  }, []);

  const activeWorkflowsCount = stats?.activeWorkflows || 0;

  return (
    <div id="wimlogic-root-container" className="min-h-screen bg-slate-50 text-slate-800 flex font-sans">
      {/* Global connection monitoring */}
      <OfflineIndicator />

      {/* Desktop Sidebar */}
      <div className="hidden lg:block w-64 shrink-0">
        <CreSidebar
          currentView={currentView}
          onViewChange={(view) => {
            setCurrentView(view);
            setMobileMenuOpen(false);
          }}
          activeWorkflows={activeWorkflowsCount}
        />
      </div>

      {/* Mobile Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-slate-900 border-b border-slate-800 text-white z-40 px-6 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded bg-indigo-600 flex items-center justify-center font-bold text-sm text-white">W</div>
          <span className="font-sans font-bold tracking-wider text-xs uppercase text-slate-300">WIMLOGIC CRE v1.0</span>
        </div>
        <button
          id="mobile-menu-toggle"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors focus:outline-none"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Slide-out Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <div className="lg:hidden fixed inset-0 z-40 flex">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileMenuOpen(false)}
              className="absolute inset-0 bg-black"
            ></motion.div>

            {/* Navigation drawer */}
            <motion.div
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 220 }}
              className="relative w-64 h-full bg-slate-900 flex flex-col z-10"
            >
              <CreSidebar
                currentView={currentView}
                onViewChange={(view) => {
                  setCurrentView(view);
                  setMobileMenuOpen(false);
                }}
                activeWorkflows={activeWorkflowsCount}
              />
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Main Workspace Frame */}
      <main className="flex-1 min-w-0 flex flex-col pt-16 lg:pt-0 lg:pl-0">
        <div className="p-6 md:p-8 max-w-7xl mx-auto w-full flex-1">
          {isLoading ? (
            <div id="wimlogic-loading-spinner" className="flex flex-col items-center justify-center py-32 space-y-4">
              <RefreshCw className="w-10 h-10 text-indigo-600 animate-spin" />
              <p className="text-xs font-bold font-mono tracking-widest text-slate-400 uppercase">
                Performing Secure Handshake...
              </p>
            </div>
          ) : (
            <AnimatePresence mode="wait">
              <motion.div
                key={currentView}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="h-full"
              >
                {currentView === 'dashboard' && (
                  <CreDashboard
                    onNavigate={setCurrentView}
                    onSelectProject={setSelectedProjectId}
                  />
                )}
                {currentView === 'projects' && (
                  <CreProjects
                    onSelectProject={setSelectedProjectId}
                    onNavigate={setCurrentView}
                  />
                )}
                {currentView === 'properties' && (
                  <CreProperties
                    selectedProjectId={selectedProjectId}
                    onSelectProject={setSelectedProjectId}
                    onNavigate={setCurrentView}
                  />
                )}
                {currentView === 'scans' && (
                  <CreWorkflowScheduler />
                )}
                {currentView === 'workflows' && (
                  <CreWorkflowScheduler />
                )}
                {currentView === 'concept-designs' && (
                  <CreConceptDesign />
                )}
                {currentView === 'assets' && (
                  <CreGeneratedAssets />
                )}
                {currentView === 'settings' && (
                  <CreSettings />
                )}
              </motion.div>
            </AnimatePresence>
          )}
        </div>
      </main>
    </div>
  );
}
