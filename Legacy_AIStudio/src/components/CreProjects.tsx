import React, { useState, useEffect } from 'react';
import { 
  Plus, 
  Layers, 
  MapPin, 
  Scan, 
  TrendingUp, 
  AlertCircle, 
  Trash2, 
  Search, 
  FolderGit2, 
  ChevronRight,
  ArrowRight
} from 'lucide-react';
import { CreProject } from '../types';
import { CreApi } from '../lib/api';

interface CreProjectsProps {
  onSelectProject: (projectId: string) => void;
  onNavigate: (view: string) => void;
}

export default function CreProjects({ onSelectProject, onNavigate }: CreProjectsProps) {
  const [projects, setProjects] = useState<CreProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Form states
  const [projectName, setProjectName] = useState('');
  const [description, setDescription] = useState('');
  const [city, setCity] = useState('Los Angeles');
  const [state, setState] = useState('CA');
  const [street, setStreet] = useState('');
  const [startAddr, setStartAddr] = useState('');
  const [endAddr, setEndAddr] = useState('');
  const [side, setSide] = useState('both');
  const [scanMode, setScanMode] = useState('quick');

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const res = await CreApi.getProjects({ search: searchQuery });
      setProjects(res.items);
    } catch (err) {
      console.error("Failed to load projects:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, [searchQuery]);

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this project workspace? All mapped properties will remain in portfolio registry.")) return;
    try {
      const res = await CreApi.deleteProject(id);
      if (res.success) {
        fetchProjects();
      }
    } catch (err) {
      console.error("Failed to delete project:", err);
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');

    if (!projectName.trim()) {
      setErrorMsg("Project name is a required field.");
      return;
    }

    try {
      const payload: Partial<CreProject> = {
        project_name: projectName,
        description: description,
        default_city: city,
        default_state: state,
        main_street: street || undefined,
        beginning_address: startAddr || undefined,
        ending_address: endAddr || undefined,
        side,
        scan_mode: scanMode
      };

      await CreApi.createProject(payload);
      
      // Reset form & close
      setProjectName('');
      setDescription('');
      setStreet('');
      setStartAddr('');
      setEndAddr('');
      setIsModalOpen(false);
      
      // Reload projects list
      fetchProjects();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to create project.");
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-sans text-2xl font-semibold tracking-tight text-slate-900">Projects & Workspaces</h2>
          <p className="text-slate-500 text-xs mt-1">
            Organize real estate portfolios, map LIDAR scan zones, and group properties into target research envelopes.
          </p>
        </div>
        <button
          id="open-create-project-modal"
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-sans font-medium text-xs rounded-lg transition-colors focus:outline-none shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>Add Workspace</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white border border-slate-100 p-4 rounded-xl shadow-sm flex flex-col sm:flex-row gap-4 items-center">
        <div className="relative w-full sm:flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            id="project-search-input"
            type="text"
            placeholder="Search projects by name, code, or description..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none focus:border-indigo-500/50 transition-colors"
          />
        </div>
        <div className="flex items-center gap-2 font-mono text-[10px] text-slate-400 tracking-wider">
          <span>PORTFOLIOS IN WORKSPACE:</span>
          <span className="font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200/40">
            {projects.length} ACTIVE
          </span>
        </div>
      </div>

      {/* Project Grid */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 space-y-4">
          <div className="w-6 h-6 rounded-full border-2 border-slate-200 border-t-indigo-600 animate-spin"></div>
          <span className="font-mono text-[9px] tracking-wider text-slate-400 uppercase">Indexing workspaces...</span>
        </div>
      ) : projects.length === 0 ? (
        <div className="bg-white border border-slate-100 p-12 text-center rounded-xl shadow-sm flex flex-col items-center justify-center space-y-4">
          <FolderGit2 className="w-10 h-10 text-slate-300" />
          <div>
            <h4 className="text-slate-800 font-sans font-semibold text-sm">No Projects Found</h4>
            <p className="text-slate-400 text-xs mt-1">Modify your search query or create a new workspace corridor to get started.</p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200/80 text-slate-700 text-xs font-semibold rounded-lg transition-colors focus:outline-none"
          >
            Create First Workspace
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((proj) => (
            <div
              key={proj.id}
              id={`project-card-${proj.project_id}`}
              onClick={() => {
                onSelectProject(proj.project_id);
                onNavigate('properties');
              }}
              className="group bg-white border border-slate-100 hover:border-slate-200 hover:shadow-md/5 rounded-xl p-5 shadow-sm transition-all cursor-pointer flex flex-col justify-between space-y-5"
            >
              {/* Top Row */}
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="bg-indigo-50 border border-indigo-100/60 font-mono text-[9px] text-indigo-600 px-1.5 py-0.5 rounded font-bold uppercase">
                      {proj.project_id}
                    </span>
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      proj.status === 'active' ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'
                    }`}></span>
                  </div>
                  <button
                    id={`delete-project-${proj.id}`}
                    onClick={(e) => handleDelete(proj.id, e)}
                    className="p-1.5 text-slate-400 hover:text-rose-500 rounded hover:bg-slate-50 transition-all opacity-0 group-hover:opacity-100"
                    title="Archive/Delete Workspace"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="space-y-1">
                  <h3 className="font-sans font-bold text-slate-800 group-hover:text-indigo-600 transition-colors text-sm truncate">
                    {proj.project_name}
                  </h3>
                  <p className="text-slate-400 font-mono text-[10px] flex items-center gap-1 leading-none uppercase">
                    <MapPin className="w-3 h-3 text-slate-300" />
                    <span>{proj.default_city}, {proj.default_state}</span>
                  </p>
                </div>

                <p className="text-slate-500 text-[11px] leading-relaxed line-clamp-3">
                  {proj.description}
                </p>
              </div>

              {/* Bottom Row Mapping details */}
              <div className="border-t border-slate-100/80 pt-4 flex items-center justify-between font-mono text-[10px] text-slate-500">
                <div className="space-y-0.5">
                  <span className="text-slate-400 block text-[9px] uppercase">LIDAR TARGETS</span>
                  <span className="font-medium text-slate-700 block max-w-[140px] truncate">
                    {proj.main_street ? `${proj.beginning_address}-${proj.ending_address} ${proj.main_street}` : 'Assessor Direct Lookup'}
                  </span>
                </div>
                <div className="flex items-center gap-1 text-indigo-600 font-sans text-xs font-semibold group-hover:translate-x-1 transition-transform">
                  <span>Enter</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white border border-slate-100 rounded-xl max-w-xl w-full shadow-2xl overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-sans font-bold text-slate-800 text-sm flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-500" />
                <span>Establish Regional Research Corridor</span>
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-600 font-bold transition-colors"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateProject} className="p-6 space-y-4">
              {errorMsg && (
                <div className="p-3 bg-rose-50 border border-rose-100 text-rose-700 rounded-lg text-[11px] flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5 sm:col-span-2">
                  <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block">Project Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Broadway Mixed-Use Redevelopment"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="space-y-1.5 sm:col-span-2">
                  <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block">Workspace Description</label>
                  <textarea
                    rows={2}
                    placeholder="Provide scope guidelines and investment parameters..."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none focus:border-indigo-500 resize-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block">Default City</label>
                  <input
                    type="text"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs text-slate-800 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block">Default State</label>
                  <input
                    type="text"
                    maxLength={2}
                    value={state}
                    onChange={(e) => setState(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs text-slate-800 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="border-t border-dashed border-slate-100 sm:col-span-2 my-2"></div>

                <div className="sm:col-span-2">
                  <div className="flex items-center gap-1.5 mb-2.5">
                    <Scan className="w-3.5 h-3.5 text-indigo-500 animate-pulse" />
                    <h4 className="text-[10px] font-bold text-slate-600 uppercase tracking-wider">
                      LIDAR Scan & Assessor Boundaries (Optional)
                    </h4>
                  </div>
                  <p className="text-[10px] text-slate-400 mb-3">
                    Input street parameters to queue automated street-level imagery parsing and County GIS synchronization.
                  </p>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block">Main Street Corridor</label>
                  <input
                    type="text"
                    placeholder="e.g. S Broadway"
                    value={street}
                    onChange={(e) => setStreet(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block">Start Addr</label>
                    <input
                      type="text"
                      placeholder="e.g. 800"
                      value={startAddr}
                      onChange={(e) => setStartAddr(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block">End Addr</label>
                    <input
                      type="text"
                      placeholder="e.g. 1000"
                      value={endAddr}
                      onChange={(e) => setEndAddr(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block">Side of Street</label>
                  <select
                    value={side}
                    onChange={(e) => setSide(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs text-slate-800 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="both">Both Sides</option>
                    <option value="north">North Side Only</option>
                    <option value="south">South Side Only</option>
                    <option value="east">East Side Only</option>
                    <option value="west">West Side Only</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block">Scan Accuracy Mode</label>
                  <select
                    value={scanMode}
                    onChange={(e) => setScanMode(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs text-slate-800 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="quick">Quick Sweep (Static Imagery)</option>
                    <option value="full">Comprehensive Sweep (Imagery + LIDAR)</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 border-t border-slate-100 pt-5 mt-4">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors focus:outline-none"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  id="submit-create-project-btn"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg transition-colors focus:outline-none shadow-sm"
                >
                  Provision Corridor
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
