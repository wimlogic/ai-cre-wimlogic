import React, { useState, useEffect } from 'react';
import { projectService } from '../services/projectService';
import { Project } from '../types';
import { 
  Plus, 
  Search, 
  Edit3, 
  Trash2, 
  MapPin, 
  FolderOpen,
  ArrowRight
} from 'lucide-react';
import EnterpriseCard from '../components/EnterpriseCard';
import StatusBadge from '../components/StatusBadge';
import EnterpriseToolbar from '../components/EnterpriseToolbar';
import ConfirmDialog from '../components/ConfirmDialog';
import FormField from '../components/FormField';
import LoadingState from '../components/LoadingState';
import useToast from '../hooks/useToast';

interface ProjectsProps {
  onSelectProject: (id: string) => void;
  onNavigate: (view: string) => void;
}

export default function Projects({ onSelectProject, onNavigate }: ProjectsProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  
  // Custom Toast notification
  const { success, error, warning } = useToast();

  // Form & Dialog States
  const [showFormModal, setShowFormModal] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<number | null>(null);
  
  const [formData, setFormData] = useState({
    project_id: '',
    project_name: '',
    description: '',
    status: 'active',
    default_city: '',
    default_state: '',
    main_street: '',
    beginning_address: '',
    ending_address: '',
    side: 'Both',
    scan_mode: 'High Density'
  });

  const loadProjects = async () => {
    setIsLoading(true);
    try {
      const res = await projectService.list({
        search: searchQuery || undefined,
        status: statusFilter || undefined,
      });
      setProjects(res.items || []);
    } catch (err: any) {
      console.error('Error listing projects:', err);
      error('Failed to fetch projects. Please verify backend state.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      loadProjects();
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, statusFilter]);

  const handleOpenCreate = () => {
    setIsEditing(false);
    setEditingId(null);
    setFormData({
      project_id: `PRJ-${Math.floor(100 + Math.random() * 900)}`,
      project_name: '',
      description: '',
      status: 'active',
      default_city: '',
      default_state: '',
      main_street: '',
      beginning_address: '',
      ending_address: '',
      side: 'Both',
      scan_mode: 'High Density'
    });
    setShowFormModal(true);
  };

  const handleOpenEdit = (proj: Project) => {
    setIsEditing(true);
    setEditingId(proj.id);
    setFormData({
      project_id: proj.project_id || '',
      project_name: proj.project_name || '',
      description: proj.description || '',
      status: proj.status || 'active',
      default_city: proj.default_city || '',
      default_state: proj.default_state || '',
      main_street: proj.main_street || '',
      beginning_address: proj.beginning_address || '',
      ending_address: proj.ending_address || '',
      side: proj.side || 'Both',
      scan_mode: proj.scan_mode || 'High Density'
    });
    setShowFormModal(true);
  };

  const confirmDeleteProject = (id: number) => {
    setProjectToDelete(id);
    setShowDeleteDialog(true);
  };

  const handleDelete = async () => {
    if (projectToDelete === null) return;
    try {
      await projectService.delete(projectToDelete);
      success('Project deleted successfully.');
      loadProjects();
    } catch (err: any) {
      console.error('Failed to delete project:', err);
      error(err.message || 'Failed to delete project.');
    } finally {
      setShowDeleteDialog(false);
      setProjectToDelete(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.project_id.trim()) {
      warning('Project ID code is required.');
      return;
    }
    if (!formData.project_name.trim()) {
      warning('Project Name is required.');
      return;
    }

    try {
      if (isEditing && editingId !== null) {
        await projectService.update(editingId, formData);
        success('Project updated successfully.');
      } else {
        await projectService.create(formData);
        success('Project created successfully.');
      }
      setShowFormModal(false);
      loadProjects();
    } catch (err: any) {
      console.error('Error submitting project form:', err);
      error(err.message || 'Conflict occurred. Verify Project ID code uniqueness.');
    }
  };

  // Custom filter controls for the toolbar
  const toolbarFilters = (
    <select
      value={statusFilter}
      onChange={(e) => setStatusFilter(e.target.value)}
      className="border border-slate-200 rounded-lg text-xs px-3 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
      id="project-status-filter-select"
    >
      <option value="">All Statuses</option>
      <option value="active">Active</option>
      <option value="completed">Completed</option>
      <option value="on-hold">On Hold</option>
    </select>
  );

  const toolbarActions = (
    <div className="flex gap-2">
      <button
        onClick={() => { setSearchQuery(''); setStatusFilter(''); }}
        className="px-3.5 py-1.5 border border-slate-200 text-slate-500 hover:bg-slate-50 rounded-lg text-xs font-semibold transition-colors focus:outline-none"
      >
        Reset Filters
      </button>
      <button
        onClick={handleOpenCreate}
        className="enterprise-btn enterprise-btn-primary"
        id="create-project-toolbar-btn"
      >
        <Plus className="w-3.5 h-3.5" />
        Create Project
      </button>
    </div>
  );

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-sans font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <FolderOpen className="w-5 h-5 text-indigo-600" />
            Project Management
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Create, audit, and organize project folders acting as the parents of all real estate entities.
          </p>
        </div>
      </div>

      {/* Enterprise Toolbar */}
      <EnterpriseToolbar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        searchPlaceholder="Search projects by ID, name, or metadata..."
        filterContent={toolbarFilters}
        actionContent={toolbarActions}
        id="projects-toolbar"
      />

      {/* Grid of Projects */}
      {isLoading ? (
        <LoadingState type="rows" message="Fetching master project repositories..." />
      ) : projects.length === 0 ? (
        <div className="bg-white border border-slate-100 rounded-xl py-24 text-center text-slate-400 flex flex-col items-center justify-center space-y-3">
          <FolderOpen className="w-10 h-10 text-slate-300" />
          <span className="text-xs font-mono uppercase tracking-wider">No Project records found</span>
          <p className="text-xs text-slate-400 max-w-md px-4 leading-relaxed">
            Get started by initializing your very first Project portfolio using the "Create Project" button.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {projects.map((proj) => (
            <EnterpriseCard
              key={proj.id}
              title={
                <div className="flex items-center justify-between w-full">
                  <span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-[10px] font-mono font-bold tracking-wider uppercase">
                    {proj.project_id}
                  </span>
                  <StatusBadge status={proj.status} type="project" />
                </div>
              }
              footer={
                <div className="flex items-center justify-between w-full">
                  <div className="flex gap-1.5">
                    <button
                      onClick={() => handleOpenEdit(proj)}
                      className="p-1.5 hover:bg-slate-100 text-slate-400 hover:text-indigo-600 rounded-lg transition-colors focus:outline-none"
                      title="Edit project"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => confirmDeleteProject(proj.id)}
                      className="p-1.5 hover:bg-slate-100 text-slate-400 hover:text-rose-600 rounded-lg transition-colors focus:outline-none"
                      title="Delete project"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  
                  <button
                    onClick={() => {
                      onSelectProject(proj.project_id);
                      onNavigate('properties');
                    }}
                    className="px-3 py-1.5 bg-indigo-50 hover:bg-indigo-600 text-indigo-700 hover:text-white rounded-lg text-[11px] font-bold transition-all flex items-center gap-1 focus:outline-none"
                  >
                    Properties
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              }
              className="flex flex-col justify-between h-full"
            >
              <div className="space-y-3">
                <h3 className="font-sans font-bold text-slate-800 text-sm group-hover:text-indigo-600 transition-colors">
                  {proj.project_name}
                </h3>
                
                <p className="text-xs text-slate-500 line-clamp-2 min-h-[2rem] leading-relaxed">
                  {proj.description || 'No description provided.'}
                </p>

                {(proj.default_city || proj.main_street) && (
                  <div className="pt-3 border-t border-slate-100 space-y-1.5 text-[11px] text-slate-500">
                    {proj.default_city && (
                      <div className="flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span>{proj.default_city}, {proj.default_state || 'USA'}</span>
                      </div>
                    )}
                    {proj.main_street && (
                      <div className="flex items-center gap-1.5 font-mono text-[10px]">
                        <span className="text-slate-400 font-sans">Street:</span>
                        <span className="text-slate-600 truncate">{proj.main_street}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </EnterpriseCard>
          ))}
        </div>
      )}

      {/* Creation/Edit Dialog Modal */}
      {showFormModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl overflow-hidden border border-slate-100 animate-fade-in flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="px-5 py-4 bg-slate-900 text-white flex justify-between items-center">
              <div>
                <h2 className="text-sm font-sans font-bold uppercase tracking-wider">
                  {isEditing ? 'Modify Project Portfolio' : 'Initialize Project Portfolio'}
                </h2>
                <p className="text-[10px] text-slate-400 font-mono mt-0.5">WIMLOGIC DIRECTIVE HANDSHAKE</p>
              </div>
              <button
                onClick={() => setShowFormModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg focus:outline-none"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={handleSubmit} className="overflow-y-auto p-5 flex-1 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2 sm:col-span-1">
                  <FormField label="Project ID Code" required error="">
                    <input
                      type="text"
                      required
                      disabled={isEditing}
                      placeholder="e.g. PRJ001"
                      value={formData.project_id}
                      onChange={(e) => setFormData({ ...formData, project_id: e.target.value })}
                      className="enterprise-form-input font-mono"
                    />
                  </FormField>
                </div>

                <div className="col-span-2 sm:col-span-1">
                  <FormField label="Project Name" required error="">
                    <input
                      type="text"
                      required
                      placeholder="e.g. Melrose Avenue Corridor"
                      value={formData.project_name}
                      onChange={(e) => setFormData({ ...formData, project_name: e.target.value })}
                      className="enterprise-form-input"
                    />
                  </FormField>
                </div>

                <div className="col-span-2">
                  <FormField label="Description">
                    <textarea
                      rows={2}
                      placeholder="Scope, notes, and strategic directives of the parcel bundle..."
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      className="enterprise-form-input"
                    />
                  </FormField>
                </div>

                <div className="col-span-2 sm:col-span-1">
                  <FormField label="Default City">
                    <input
                      type="text"
                      placeholder="e.g. Los Angeles"
                      value={formData.default_city}
                      onChange={(e) => setFormData({ ...formData, default_city: e.target.value })}
                      className="enterprise-form-input"
                    />
                  </FormField>
                </div>

                <div className="col-span-2 sm:col-span-1">
                  <FormField label="Default State">
                    <input
                      type="text"
                      placeholder="e.g. CA"
                      maxLength={2}
                      value={formData.default_state}
                      onChange={(e) => setFormData({ ...formData, default_state: e.target.value })}
                      className="enterprise-form-input"
                    />
                  </FormField>
                </div>

                <div className="col-span-2 sm:col-span-1">
                  <FormField label="Main Street">
                    <input
                      type="text"
                      placeholder="e.g. Melrose Avenue"
                      value={formData.main_street}
                      onChange={(e) => setFormData({ ...formData, main_street: e.target.value })}
                      className="enterprise-form-input"
                    />
                  </FormField>
                </div>

                <div className="col-span-2 sm:col-span-1">
                  <FormField label="Scan Mode">
                    <select
                      value={formData.scan_mode}
                      onChange={(e) => setFormData({ ...formData, scan_mode: e.target.value })}
                      className="enterprise-form-input"
                    >
                      <option value="High Density">High Density</option>
                      <option value="Rapid Capture">Rapid Capture</option>
                      <option value="Deep Audit">Deep Audit</option>
                    </select>
                  </FormField>
                </div>

                <div className="col-span-2 sm:col-span-1">
                  <FormField label="Beginning Address Range">
                    <input
                      type="text"
                      placeholder="e.g. 7000"
                      value={formData.beginning_address}
                      onChange={(e) => setFormData({ ...formData, beginning_address: e.target.value })}
                      className="enterprise-form-input"
                    />
                  </FormField>
                </div>

                <div className="col-span-2 sm:col-span-1">
                  <FormField label="Ending Address Range">
                    <input
                      type="text"
                      placeholder="e.g. 7800"
                      value={formData.ending_address}
                      onChange={(e) => setFormData({ ...formData, ending_address: e.target.value })}
                      className="enterprise-form-input"
                    />
                  </FormField>
                </div>

                <div className="col-span-2 sm:col-span-1">
                  <FormField label="Street Side">
                    <select
                      value={formData.side}
                      onChange={(e) => setFormData({ ...formData, side: e.target.value })}
                      className="enterprise-form-input"
                    >
                      <option value="Both">Both Sides</option>
                      <option value="North">North Side Only</option>
                      <option value="South">South Side Only</option>
                      <option value="East">East Side Only</option>
                      <option value="West">West Side Only</option>
                    </select>
                  </FormField>
                </div>

                <div className="col-span-2 sm:col-span-1">
                  <FormField label="Project Status">
                    <select
                      value={formData.status}
                      onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                      className="enterprise-form-input"
                    >
                      <option value="active">Active</option>
                      <option value="completed">Completed</option>
                      <option value="on-hold">On Hold</option>
                    </select>
                  </FormField>
                </div>
              </div>

              {/* Modal Actions */}
              <div className="pt-4 border-t border-slate-100 flex justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setShowFormModal(false)}
                  className="px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-500 rounded-lg text-xs font-semibold tracking-wide transition-all focus:outline-none"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold tracking-wide transition-all shadow-md shadow-indigo-600/10 focus:outline-none"
                >
                  {isEditing ? 'Save Changes' : 'Initialize Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showDeleteDialog}
        title="Delete Project Portfolio"
        message="Are you absolutely sure you want to delete this project? This will permanently remove all associated property information and workflow statistics."
        confirmLabel="Permanently Delete"
        cancelLabel="Keep Project"
        isDanger={true}
        onConfirm={handleDelete}
        onCancel={() => {
          setShowDeleteDialog(false);
          setProjectToDelete(null);
        }}
        id="project-delete-confirm-dialog"
      />
    </div>
  );
}

// Small cross icon inline replacement since Lucide has X
function X({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}
