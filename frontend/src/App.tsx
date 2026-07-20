import React, { useState } from 'react';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import Properties from './pages/Properties';
import PropertyImages from './pages/PropertyImages';
import HomeStudio from './pages/HomeStudio';
import AIOrchestration from './pages/AIOrchestration';
import WorkflowResults from './pages/WorkflowResults';
import GeneratedAssets from './pages/GeneratedAssets';
import Settings from './pages/Settings';
import EnterpriseLayout from './layouts/EnterpriseLayout';

type ViewType = 'Dashboard' | 'Projects' | 'Properties' | 'Property Images' | 'Home Studio' | 'AI Orchestration' | 'Workflow Results' | 'Generated Assets' | 'Settings';

export default function App() {
  const [currentView, setCurrentView] = useState<ViewType>('Dashboard');
  const [selectedProjectId, setSelectedProjectId] = useState<string>(''); // Holds selected project code like PRJ001
  // Mirrors the selectedProjectId pattern above - lifted to App level so
  // Dashboard's Recent Properties can hand off the clicked Property's
  // identity into Home Studio, rather than Home Studio only ever
  // starting with no Property selected. Home Studio remains free to
  // change this via its own Property selector; that change is lifted
  // back up here so the two stay in sync (Checkpoint 2B correction pass).
  const [selectedPropertyId, setSelectedPropertyId] = useState<number | null>(null);

  const handleNavigate = (view: string) => {
    setCurrentView(view as ViewType);
  };

  const renderActiveView = () => {
    switch (currentView) {
      case 'Dashboard':
        return (
          <Dashboard
            onNavigate={handleNavigate}
            onSelectProject={setSelectedProjectId}
            onSelectProperty={setSelectedPropertyId}
          />
        );
      case 'Projects':
        return <Projects onSelectProject={setSelectedProjectId} onNavigate={handleNavigate} />;
      case 'Properties':
        return (
          <Properties 
            selectedProjectId={selectedProjectId} 
            onSelectProject={setSelectedProjectId} 
            onNavigate={handleNavigate} 
          />
        );
      case 'Property Images':
        return <PropertyImages />;
      case 'Home Studio':
        return (
          <HomeStudio
            selectedPropertyId={selectedPropertyId}
            onSelectProperty={setSelectedPropertyId}
          />
        );
      case 'AI Orchestration':
        return <AIOrchestration />;
      case 'Workflow Results':
        return <WorkflowResults />;
      case 'Generated Assets':
        return <GeneratedAssets />;
      case 'Settings':
        return <Settings />;
      default:
        return (
          <Dashboard
            onNavigate={handleNavigate}
            onSelectProject={setSelectedProjectId}
            onSelectProperty={setSelectedPropertyId}
          />
        );
    }
  };

  return (
    <EnterpriseLayout
      currentView={currentView}
      onNavigate={handleNavigate}
      selectedProjectId={selectedProjectId}
      id="app-enterprise-layout"
    >
      {renderActiveView()}
    </EnterpriseLayout>
  );
}
