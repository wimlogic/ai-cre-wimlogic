import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Layers, 
  Compass, 
  MapPin, 
  FileCheck, 
  ClipboardCheck, 
  AlertCircle, 
  Plus, 
  ExternalLink,
  ChevronRight,
  FlameKindling,
  Cpu,
  RefreshCw,
  Clock,
  ThumbsUp,
  Award
} from 'lucide-react';
import { CreConceptDesign, CreProperty, CreRenovationScenario } from '../types';
import { CreApi } from '../lib/api';

export default function CreConceptDesignComp() {
  const [designs, setDesigns] = useState<CreConceptDesign[]>([]);
  const [scenarios, setScenarios] = useState<CreRenovationScenario[]>([]);
  const [properties, setProperties] = useState<CreProperty[]>([]);
  const [selectedPropertyId, setSelectedPropertyId] = useState<number>(101);
  const [loading, setLoading] = useState(true);

  // Forms
  const [promptText, setPromptText] = useState('');
  const [designTitle, setDesignTitle] = useState('');
  const [designNotes, setDesignNotes] = useState('');
  
  const [scenarioName, setScenarioName] = useState('');
  const [rationale, setRationale] = useState('');
  const [risk, setRisk] = useState<'low' | 'medium' | 'high'>('medium');
  const [complexity, setComplexity] = useState<'low' | 'medium' | 'high'>('medium');

  const [isDesignModalOpen, setIsDesignModalOpen] = useState(false);
  const [isScenarioModalOpen, setIsScenarioModalOpen] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [propRes, designRes, scenRes] = await Promise.all([
        CreApi.getProperties(),
        CreApi.getConceptDesigns({ property_id: selectedPropertyId }),
        CreApi.getScenarios({ property_id: selectedPropertyId })
      ]);
      setProperties(propRes.items);
      setDesigns(designRes.items);
      setScenarios(scenRes.items);
    } catch (err) {
      console.error("Failed to load concept parameters:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedPropertyId]);

  const handleCreateDesign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!promptText.trim()) return;

    try {
      await CreApi.createConceptDesign({
        property_id: selectedPropertyId,
        title: designTitle || "Draft Architectural Concept Elevation",
        concept_prompt: promptText,
        concept_notes: designNotes
      });

      setPromptText('');
      setDesignTitle('');
      setDesignNotes('');
      setIsDesignModalOpen(false);
      await loadData();
    } catch (err) {
      console.error("Failed to post concept design:", err);
    }
  };

  const handleCreateScenario = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scenarioName.trim()) return;

    try {
      await CreApi.createScenario({
        property_id: selectedPropertyId,
        renovation_type: scenarioName,
        rationale,
        risk_level: risk,
        estimated_complexity: complexity
      });

      setScenarioName('');
      setRationale('');
      setIsScenarioModalOpen(false);
      await loadData();
    } catch (err) {
      console.error("Failed to save scenario planner:", err);
    }
  };

  const handleUpdateDesignStatus = async (id: number, status: 'draft' | 'under_review' | 'approved') => {
    try {
      await CreApi.updateConceptDesignStatus(id, status);
      await loadData();
    } catch (err) {
      console.error("Failed to lock status change:", err);
    }
  };

  const handleUpdateScenarioStatus = async (id: number, status: 'draft' | 'approved' | 'rejected') => {
    try {
      await CreApi.updateScenarioStatus(id, status);
      await loadData();
    } catch (err) {
      console.error("Failed to change scenario approval state:", err);
    }
  };

  const selectedProperty = properties.find(p => p.id === selectedPropertyId);

  return (
    <div className="space-y-8">
      {/* Upper section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="font-sans text-2xl font-semibold tracking-tight text-slate-900">Designs & Scenarios</h2>
          <p className="text-slate-500 text-xs mt-1">
            Specify structural prompt elevations, review visual drafts, approve renovation scenarios, and organize versions.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="font-sans text-[10px] font-bold text-slate-400 uppercase tracking-wider">TARGET PARCEL:</label>
          <select
            value={selectedPropertyId}
            onChange={(e) => setSelectedPropertyId(Number(e.target.value))}
            className="px-3 py-1.5 bg-white border border-slate-200/80 rounded-lg text-xs font-semibold text-slate-700 focus:outline-none"
          >
            {properties.map(p => (
              <option key={p.id} value={p.id}>{p.display_address} ({p.property_uid})</option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 space-y-4">
          <div className="w-6 h-6 rounded-full border-2 border-slate-200 border-t-indigo-600 animate-spin"></div>
          <span className="font-mono text-[9px] tracking-wider text-slate-400 uppercase">Synchronizing visual blueprints...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
          {/* Renovation Scenarios Planner */}
          <div className="bg-white border border-slate-100 p-6 rounded-xl shadow-sm space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Compass className="w-4.5 h-4.5 text-indigo-500" />
                <h3 className="font-sans text-sm font-semibold text-slate-800">Redevelopment Scenarios</h3>
              </div>
              <button
                onClick={() => setIsScenarioModalOpen(true)}
                className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1 focus:outline-none"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Plan Scenario</span>
              </button>
            </div>

            {scenarios.length === 0 ? (
              <div className="py-12 text-center text-slate-400 text-xs">
                No active renovation scenarios planned for this parcel yet. Plan an adaptive-reuse scenario to begin.
              </div>
            ) : (
              <div className="space-y-4">
                {scenarios.map((scen) => (
                  <div 
                    key={scen.id}
                    className="border border-slate-100 p-4 rounded-xl space-y-3 hover:shadow-sm/5 transition-all bg-slate-50/20"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h4 className="text-xs font-bold text-slate-800 leading-tight">{scen.renovation_type}</h4>
                        <span className="text-[10px] text-slate-400 font-mono mt-1 block uppercase">SOURCE: {scen.source}</span>
                      </div>
                      <span className={`px-2 py-0.5 rounded-full font-sans text-[9px] font-bold shrink-0 ${
                        scen.status === 'approved' 
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' 
                          : scen.status === 'rejected'
                          ? 'bg-rose-50 text-rose-700 border border-rose-100'
                          : 'bg-slate-50 text-slate-700 border border-slate-100'
                      }`}>
                        {scen.status}
                      </span>
                    </div>

                    <p className="text-slate-500 text-[11px] leading-relaxed">{scen.rationale}</p>

                    <div className="grid grid-cols-2 gap-3 font-mono text-[9px] text-slate-400 border-t border-slate-100/60 pt-3">
                      <div>
                        <span>RISK PROFILE</span>
                        <span className="font-bold text-slate-700 block uppercase mt-0.5">{scen.risk_level}</span>
                      </div>
                      <div>
                        <span>COMPLEXITY</span>
                        <span className="font-bold text-slate-700 block uppercase mt-0.5">{scen.estimated_complexity}</span>
                      </div>
                    </div>

                    {scen.status === 'draft' && (
                      <div className="flex gap-2 justify-end border-t border-slate-100/50 pt-3">
                        <button
                          onClick={() => handleUpdateScenarioStatus(scen.id, 'rejected')}
                          className="px-2.5 py-1 text-[10px] bg-white border border-slate-200 text-rose-600 font-bold rounded hover:bg-rose-50 transition-colors"
                        >
                          Reject
                        </button>
                        <button
                          onClick={() => handleUpdateScenarioStatus(scen.id, 'approved')}
                          className="px-2.5 py-1 text-[10px] bg-indigo-600 text-white font-bold rounded hover:bg-indigo-700 transition-colors"
                        >
                          Approve
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Concept Designs Elevation */}
          <div className="bg-white border border-slate-100 p-6 rounded-xl shadow-sm space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4.5 h-4.5 text-indigo-500 animate-pulse" />
                <h3 className="font-sans text-sm font-semibold text-slate-800">Visual Conceptual Designs</h3>
              </div>
              <button
                onClick={() => setIsDesignModalOpen(true)}
                className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1 focus:outline-none"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Elevation Prompt</span>
              </button>
            </div>

            {designs.length === 0 ? (
              <div className="py-12 text-center text-slate-400 text-xs">
                No active mock concepts found. Specify a visual elevation prompt to dispatch rendering parameters.
              </div>
            ) : (
              <div className="space-y-4">
                {designs.map((design) => (
                  <div 
                    key={design.id}
                    className="border border-slate-100 p-4 rounded-xl space-y-3 hover:shadow-sm/5 transition-all bg-slate-50/20"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h4 className="text-xs font-bold text-slate-800 leading-tight">{design.title}</h4>
                        <span className="text-[10px] text-slate-400 font-mono mt-1 block uppercase">VERSION: {design.design_version}</span>
                      </div>
                      <span className={`px-2 py-0.5 rounded-full font-sans text-[9px] font-bold shrink-0 ${
                        design.status === 'approved' 
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' 
                          : 'bg-slate-50 text-slate-700 border border-slate-100'
                      }`}>
                        {design.status}
                      </span>
                    </div>

                    <div className="bg-slate-950 text-slate-300 font-mono text-[10px] p-3 rounded-lg border border-slate-800">
                      <span className="text-[8px] font-bold text-slate-500 block uppercase mb-1">PROMPT SEED</span>
                      <p className="leading-relaxed">"{design.concept_prompt}"</p>
                    </div>

                    <p className="text-slate-500 text-[11px] leading-relaxed">{design.concept_notes}</p>

                    <div className="flex gap-2 justify-end border-t border-slate-100/50 pt-3.5">
                      {design.status !== 'approved' && (
                        <button
                          onClick={() => handleUpdateDesignStatus(design.id, 'approved')}
                          className="flex items-center gap-1 px-3 py-1.5 text-[10px] bg-indigo-50 border border-indigo-100 text-indigo-700 font-bold rounded-md hover:bg-indigo-100 transition-colors"
                        >
                          <ThumbsUp className="w-3 h-3 fill-current" />
                          <span>Approve Design Elevation</span>
                        </button>
                      )}
                      {design.status === 'approved' && (
                        <span className="text-[10px] font-sans font-bold text-emerald-600 flex items-center gap-1">
                          <Award className="w-3.5 h-3.5" />
                          <span>Locked and Approved by Marcus Vance</span>
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Plan Scenario Modal */}
      {isScenarioModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white border border-slate-100 rounded-xl max-w-md w-full shadow-2xl overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-sans font-bold text-slate-800 text-sm flex items-center gap-2">
                <Compass className="w-4 h-4 text-indigo-500" />
                <span>Draft Redevelopment Scenario</span>
              </h3>
              <button
                onClick={() => setIsScenarioModalOpen(false)}
                className="p-1 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-600 font-bold transition-colors"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateScenario} className="p-6 space-y-4">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Scenario Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Micro-retail cluster or loft adaptive-reuse"
                  value={scenarioName}
                  onChange={(e) => setScenarioName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Investment Rationale</label>
                <textarea
                  rows={3}
                  placeholder="Provide supporting business drivers, demographics, or municipal triggers..."
                  value={rationale}
                  onChange={(e) => setRationale(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none resize-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Risk Profile</label>
                  <select
                    value={risk}
                    onChange={(e) => setRisk(e.target.value as any)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs text-slate-800 focus:outline-none"
                  >
                    <option value="low">Low Risk</option>
                    <option value="medium">Medium Risk</option>
                    <option value="high">High Entitlement Risk</option>
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Complexity</label>
                  <select
                    value={complexity}
                    onChange={(e) => setComplexity(e.target.value as any)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs text-slate-800 focus:outline-none"
                  >
                    <option value="low">Low Complexity</option>
                    <option value="medium">Medium Structural</option>
                    <option value="high">Heavy Civil Engineering</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 border-t border-slate-100 pt-4 mt-4">
                <button
                  type="button"
                  onClick={() => setIsScenarioModalOpen(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors focus:outline-none"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  id="submit-create-scenario-btn"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg transition-colors focus:outline-none"
                >
                  Save Scenario
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Visual Design Modal */}
      {isDesignModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white border border-slate-100 rounded-xl max-w-md w-full shadow-2xl overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-sans font-bold text-slate-800 text-sm flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-500" />
                <span>Specify Visual Prompt Elevation</span>
              </h3>
              <button
                onClick={() => setIsDesignModalOpen(false)}
                className="p-1 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-600 font-bold transition-colors"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateDesign} className="p-6 space-y-4">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Concept Elevation Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Modern Glass facade over vintage brick frame"
                  value={designTitle}
                  onChange={(e) => setDesignTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Architectural prompt parameters</label>
                <textarea
                  rows={3}
                  required
                  placeholder="e.g. Sunset golden-hour lighting, bustling street-level walkway, historic facade integration, detailed architectural render..."
                  value={promptText}
                  onChange={(e) => setPromptText(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none resize-none font-mono"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Refinement notes</label>
                <input
                  type="text"
                  placeholder="Add custom notes about material scopes or building profiles..."
                  value={designNotes}
                  onChange={(e) => setDesignNotes(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 border-t border-slate-100 pt-4 mt-4">
                <button
                  type="button"
                  onClick={() => setIsDesignModalOpen(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors focus:outline-none"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  id="submit-create-design-btn"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg transition-colors focus:outline-none"
                >
                  Post Prompt Blueprint
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
