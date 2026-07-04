import React, { useState, useEffect } from 'react';
import { 
  Building2, 
  MapPin, 
  Layers, 
  Plus, 
  ChevronRight, 
  FileImage, 
  Cpu, 
  Trash2, 
  Image as ImageIcon, 
  Activity, 
  Play, 
  ClipboardCheck, 
  FlameKindling, 
  History,
  FileDown,
  Sparkles,
  RefreshCw,
  FolderOpen
} from 'lucide-react';
import { CreProperty, CreProject, CrePropertyImage, CreWorkflowExecution } from '../types';
import { CreApi } from '../lib/api';

interface CrePropertiesProps {
  selectedProjectId: string;
  onSelectProject: (projectId: string) => void;
  onNavigate: (view: string) => void;
}

export default function CreProperties({ selectedProjectId, onSelectProject, onNavigate }: CrePropertiesProps) {
  const [properties, setProperties] = useState<CreProperty[]>([]);
  const [projects, setProjects] = useState<CreProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedProperty, setSelectedProperty] = useState<CreProperty | null>(null);
  const [images, setImages] = useState<CrePropertyImage[]>([]);
  const [workflows, setWorkflows] = useState<CreWorkflowExecution[]>([]);
  
  // Modal / form states
  const [isPropertyModalOpen, setIsPropertyModalOpen] = useState(false);
  const [isImageModalOpen, setIsImageModalOpen] = useState(false);
  const [isWorkflowModalOpen, setIsWorkflowModalOpen] = useState(false);

  // New property form
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('CA');
  const [zip, setZip] = useState('');
  const [apn, setApn] = useState('');
  const [lotSqft, setLotSqft] = useState('');
  const [buildingSqft, setBuildingSqft] = useState('');
  const [yearBuilt, setYearBuilt] = useState('');
  const [zoning, setZoning] = useState('LA-C5');
  const [existingUse, setExistingUse] = useState('');
  const [businessName, setBusinessName] = useState('');
  const [landVal, setLandVal] = useState('');
  const [impVal, setImpVal] = useState('');
  const [notes, setNotes] = useState('');

  // New image form
  const [imgUrl, setImgUrl] = useState('');
  const [imgType, setImgType] = useState<'uploaded' | 'street_view' | 'satellite' | 'parcel_map'>('uploaded');
  const [imgNotes, setImgNotes] = useState('');

  // Workflow dispatch form
  const [workflowCode, setWorkflowCode] = useState('CRE_COMPREHENSIVE_ANALYZE');
  const [priority, setPriority] = useState('Normal');
  const [dispatching, setDispatching] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const projRes = await CreApi.getProjects();
      setProjects(projRes.items);

      const propRes = await CreApi.getProperties({ 
        project_id: selectedProjectId || undefined 
      });
      setProperties(propRes.items);

      if (propRes.items.length > 0) {
        // Default to select first property if none selected yet
        if (!selectedProperty) {
          handleSelectProperty(propRes.items[0]);
        } else {
          // Keep selection updated
          const updated = propRes.items.find(p => p.id === selectedProperty.id);
          if (updated) handleSelectProperty(updated);
        }
      } else {
        setSelectedProperty(null);
        setImages([]);
        setWorkflows([]);
      }
    } catch (err) {
      console.error("Failed to load properties:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedProjectId]);

  const handleSelectProperty = async (prop: CreProperty) => {
    setSelectedProperty(prop);
    try {
      const [imgRes, wfRes] = await Promise.all([
        CreApi.getPropertyImages(prop.id),
        CreApi.getWorkflows({ property_id: prop.id })
      ]);
      setImages(imgRes.items);
      setWorkflows(wfRes.items);
    } catch (err) {
      console.error("Failed to load sub-property metadata:", err);
    }
  };

  const handleDeleteProperty = async (id: number) => {
    if (!window.confirm("Are you sure you want to delete this property? All local images and analysis models will be purged.")) return;
    try {
      const res = await CreApi.deleteProperty(id);
      if (res.success) {
        setSelectedProperty(null);
        loadData();
      }
    } catch (err) {
      console.error("Failed to delete property:", err);
    }
  };

  const handleAddProperty = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address) return;

    try {
      const payload = {
        project_id: selectedProjectId || undefined,
        address,
        city,
        state,
        zip,
        apn,
        lot_sqft: Number(lotSqft) || undefined,
        building_sqft: Number(buildingSqft) || undefined,
        year_built: Number(yearBuilt) || undefined,
        zoning_code: zoning,
        existing_use: existingUse,
        business_name: businessName,
        land_value: Number(landVal) || undefined,
        improvement_value: Number(impVal) || undefined,
        notes
      };

      const res = await CreApi.createProperty(payload);
      setIsPropertyModalOpen(false);
      
      // Clear form
      setAddress('');
      setCity('');
      setZip('');
      setApn('');
      setLotSqft('');
      setBuildingSqft('');
      setYearBuilt('');
      setExistingUse('');
      setBusinessName('');
      setLandVal('');
      setImpVal('');
      setNotes('');

      // Reload
      await loadData();
      // Auto-select newly created property
      handleSelectProperty(res);
    } catch (err) {
      console.error("Failed to create property:", err);
    }
  };

  const handleAddImage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProperty || !imgUrl) return;

    try {
      await CreApi.uploadPropertyImage(selectedProperty.id, {
        image_url: imgUrl,
        image_type: imgType,
        notes: imgNotes,
        original_file_name: `user_${Date.now()}_img.jpg`
      });

      setImgUrl('');
      setImgNotes('');
      setIsImageModalOpen(false);

      // Refresh selection
      handleSelectProperty(selectedProperty);
    } catch (err) {
      console.error("Failed to append image:", err);
    }
  };

  const handleDeleteImage = async (imgId: number) => {
    if (!window.confirm("Are you sure you want to remove this property image?")) return;
    try {
      await CreApi.deletePropertyImage(imgId);
      if (selectedProperty) handleSelectProperty(selectedProperty);
    } catch (err) {
      console.error("Failed to delete image:", err);
    }
  };

  const handleDispatchWorkflow = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProperty) return;

    try {
      setDispatching(true);
      const activeProj = projects.find(p => p.project_id === selectedProjectId);
      await CreApi.dispatchWorkflow({
        project_id: activeProj?.id || 1,
        property_id: selectedProperty.id,
        workflow_code: workflowCode,
        priority
      });

      setIsWorkflowModalOpen(false);
      // Refresh workflows after dispatch
      handleSelectProperty(selectedProperty);
    } catch (err) {
      console.error("Failed to dispatch workflow:", err);
    } finally {
      setDispatching(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="font-sans text-2xl font-semibold tracking-tight text-slate-900">Property Portfolios</h2>
          <p className="text-slate-500 text-xs mt-1">
            Browse corporate real estate portfolios, inspect physical/financial boundaries, and queue DEV-TOOLS AI analytical routines.
          </p>
        </div>
        <div className="flex items-center gap-3 self-start md:self-auto">
          {/* Project Selector dropdown */}
          <div className="flex items-center gap-2">
            <label className="font-sans text-[10px] font-bold text-slate-400 uppercase tracking-wider">WORKSPACE:</label>
            <select
              value={selectedProjectId || ''}
              onChange={(e) => onSelectProject(e.target.value)}
              className="px-3 py-1.5 bg-white border border-slate-200/80 rounded-lg text-xs font-semibold text-slate-700 focus:outline-none"
            >
              <option value="">-- All Projects --</option>
              {projects.map(p => (
                <option key={p.id} value={p.project_id}>{p.project_name}</option>
              ))}
            </select>
          </div>

          <button
            id="register-property-btn"
            onClick={() => setIsPropertyModalOpen(true)}
            className="flex items-center gap-2 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-sans font-medium text-xs rounded-lg transition-colors focus:outline-none shadow-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Register Property</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 space-y-4">
          <div className="w-6 h-6 rounded-full border-2 border-slate-200 border-t-indigo-600 animate-spin"></div>
          <span className="font-mono text-[9px] tracking-wider text-slate-400 uppercase">Synchronizing portfolio register...</span>
        </div>
      ) : properties.length === 0 ? (
        <div className="bg-white border border-slate-100 p-12 text-center rounded-xl shadow-sm flex flex-col items-center justify-center space-y-4">
          <Building2 className="w-10 h-10 text-slate-300" />
          <div>
            <h4 className="text-slate-800 font-sans font-semibold text-sm">No Properties Mapped</h4>
            <p className="text-slate-400 text-xs mt-1">There are no properties linked to this workspace corridor yet.</p>
          </div>
          <button
            onClick={() => setIsPropertyModalOpen(true)}
            className="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200/80 text-slate-700 text-xs font-semibold rounded-lg transition-colors focus:outline-none"
          >
            Register First Property
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          {/* Properties Left Hand List */}
          <div className="lg:col-span-1 bg-white border border-slate-100 rounded-xl shadow-sm overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-100 bg-slate-50/50">
              <h3 className="text-xs font-bold font-sans text-slate-400 uppercase tracking-wider">Corridor Inventory ({properties.length})</h3>
            </div>
            <div className="divide-y divide-slate-100 max-h-[600px] overflow-y-auto">
              {properties.map((prop) => {
                const isSelected = selectedProperty?.id === prop.id;
                return (
                  <div
                    key={prop.id}
                    id={`property-row-${prop.id}`}
                    onClick={() => handleSelectProperty(prop)}
                    className={`p-4 cursor-pointer transition-all flex items-start gap-3.5 justify-between relative ${
                      isSelected ? 'bg-indigo-50/40 border-l-2 border-indigo-600' : 'hover:bg-slate-50/40'
                    }`}
                  >
                    <div className="space-y-1.5 min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="bg-slate-100 font-mono text-[8px] font-bold text-slate-500 px-1 py-0.2 rounded uppercase">
                          {prop.property_uid}
                        </span>
                        <span className="font-mono text-[9px] text-slate-400 uppercase">Zoning: {prop.zoning_code}</span>
                      </div>
                      <h4 className="font-sans text-xs font-bold text-slate-800 truncate">{prop.display_address}</h4>
                      <p className="text-[10px] text-slate-500 truncate leading-none">{prop.city}, {prop.state}</p>
                    </div>
                    <ChevronRight className={`w-4 h-4 text-slate-400 shrink-0 self-center ${isSelected ? 'translate-x-1 text-indigo-500' : ''}`} />
                  </div>
                );
              })}
            </div>
          </div>

          {/* Property Detailed Inspector Panel */}
          {selectedProperty && (
            <div className="lg:col-span-2 space-y-6">
              {/* Primary Header Card */}
              <div className="bg-white border border-slate-100 rounded-xl shadow-sm p-6 space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-slate-100 pb-5">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="bg-indigo-600 font-mono text-[9px] text-white font-bold px-2 py-0.5 rounded uppercase">
                        {selectedProperty.property_uid}
                      </span>
                      <span className="text-slate-400 font-mono text-xs">APN: {selectedProperty.apn}</span>
                    </div>
                    <h3 className="font-sans text-lg font-bold text-slate-900 leading-tight">{selectedProperty.address}</h3>
                    {selectedProperty.business_name && (
                      <p className="text-xs text-indigo-600 font-medium font-sans flex items-center gap-1.5">
                        <Building2 className="w-3.5 h-3.5" />
                        <span>Occupant: {selectedProperty.business_name}</span>
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      id={`delete-property-btn-${selectedProperty.id}`}
                      onClick={() => handleDeleteProperty(selectedProperty.id)}
                      className="p-2 text-slate-400 hover:text-rose-500 rounded-lg hover:bg-slate-50 border border-slate-200/50 transition-all"
                      title="De-register Property"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>

                    <button
                      id={`trigger-workflow-btn-${selectedProperty.id}`}
                      onClick={() => setIsWorkflowModalOpen(true)}
                      className="flex items-center gap-1.5 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-sans font-medium text-xs rounded-lg transition-colors focus:outline-none shadow-sm shadow-indigo-600/10"
                    >
                      <Cpu className="w-4 h-4" />
                      <span>Launch AI Pipeline</span>
                    </button>
                  </div>
                </div>

                {/* Assessor Metrics Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 bg-slate-50/60 p-4 rounded-xl border border-slate-100">
                  <div className="space-y-0.5">
                    <span className="text-slate-400 font-mono text-[9px] uppercase tracking-wider">Lot SQFT</span>
                    <span className="text-sm font-sans font-bold text-slate-800 block">
                      {selectedProperty.lot_sqft ? selectedProperty.lot_sqft.toLocaleString() : 'N/A'}
                    </span>
                  </div>
                  <div className="space-y-0.5">
                    <span className="text-slate-400 font-mono text-[9px] uppercase tracking-wider">Building SQFT</span>
                    <span className="text-sm font-sans font-bold text-slate-800 block">
                      {selectedProperty.building_sqft ? selectedProperty.building_sqft.toLocaleString() : 'N/A'}
                    </span>
                  </div>
                  <div className="space-y-0.5">
                    <span className="text-slate-400 font-mono text-[9px] uppercase tracking-wider">Year Built</span>
                    <span className="text-sm font-sans font-bold text-slate-800 block">
                      {selectedProperty.year_built || 'N/A'}
                    </span>
                  </div>
                  <div className="space-y-0.5">
                    <span className="text-slate-400 font-mono text-[9px] uppercase tracking-wider">Assessed Value</span>
                    <span className="text-sm font-sans font-bold text-slate-800 block">
                      {selectedProperty.total_assessed_value ? `$${selectedProperty.total_assessed_value.toLocaleString()}` : 'N/A'}
                    </span>
                  </div>
                </div>

                <div className="text-slate-600 text-xs leading-relaxed space-y-1 bg-indigo-50/20 border border-indigo-100/50 p-4 rounded-lg">
                  <span className="text-[10px] font-bold text-indigo-600 block uppercase font-mono tracking-wider">Workspace Memo Notes</span>
                  <p>{selectedProperty.notes || 'No custom notes logged for this parcel registry.'}</p>
                </div>
              </div>

              {/* Property Imagery Submodule */}
              <div className="bg-white border border-slate-100 rounded-xl shadow-sm p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2">
                    <ImageIcon className="w-4.5 h-4.5 text-indigo-500" />
                    <h3 className="font-sans text-sm font-semibold text-slate-800">Imagery Portfolio</h3>
                  </div>
                  <button
                    id="open-upload-img-modal"
                    onClick={() => setIsImageModalOpen(true)}
                    className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1.5 focus:outline-none"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Attach Image</span>
                  </button>
                </div>

                {images.length === 0 ? (
                  <div className="py-8 text-center text-slate-400 text-xs">
                    No active photographs associated with this parcel. Upload a street-view screenshot or satellite layout.
                  </div>
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                    {images.map((img) => (
                      <div 
                        key={img.id} 
                        className="group relative border border-slate-150 rounded-lg overflow-hidden bg-slate-50 h-28 hover:shadow-md/5 transition-all"
                      >
                        <img 
                          src={img.image_url} 
                          alt={img.image_type}
                          referrerPolicy="no-referrer"
                          className="w-full h-full object-cover"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-transparent p-2.5 flex flex-col justify-between opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            id={`delete-image-${img.id}`}
                            onClick={() => handleDeleteImage(img.id)}
                            className="p-1 bg-rose-600 text-white hover:bg-rose-700 rounded transition-colors self-end"
                            title="Remove Photo"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                          <div>
                            <span className="font-mono text-[8px] font-bold text-indigo-300 uppercase block">{img.image_type}</span>
                            <span className="text-[9px] text-white block truncate">{img.notes || 'No description'}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Workflows Pipelines Log */}
              <div className="bg-white border border-slate-100 rounded-xl shadow-sm p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2">
                    <Activity className="w-4.5 h-4.5 text-indigo-500 animate-pulse" />
                    <h3 className="font-sans text-sm font-semibold text-slate-800">Orchestration Executions</h3>
                  </div>
                  <button
                    onClick={() => {
                      onNavigate('workflows');
                    }}
                    className="text-xs text-slate-500 hover:text-slate-800 font-medium flex items-center gap-1 focus:outline-none"
                  >
                    <span>Pipeline Center</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>

                {workflows.length === 0 ? (
                  <div className="py-8 text-center text-slate-400 text-xs">
                    No pipelines have been triggered for this property. Click 'Launch AI Pipeline' above to execute.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {workflows.map((wf) => (
                      <div 
                        key={wf.execution_id}
                        className="border border-slate-100 p-3.5 rounded-lg flex items-center justify-between gap-4 hover:bg-slate-50/40 transition-colors cursor-pointer"
                        onClick={() => {
                          onNavigate('workflows');
                        }}
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="bg-slate-100 border border-slate-200 text-slate-600 font-mono text-[8px] font-bold px-1.5 py-0.2 rounded uppercase">
                              {wf.execution_number}
                            </span>
                            <span className="text-xs font-bold text-slate-800">{wf.workflow_code}</span>
                          </div>
                          <span className="font-mono text-[9px] text-slate-400 block">Submitted: {wf.submitted_at}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`px-2 py-0.5 rounded-full font-sans text-[9px] font-bold ${
                            wf.status === 'Completed' 
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' 
                              : wf.status === 'Running'
                              ? 'bg-indigo-50 text-indigo-700 border border-indigo-100 animate-pulse'
                              : 'bg-slate-50 text-slate-700 border border-slate-100'
                          }`}>
                            {wf.status}
                          </span>
                          <ChevronRight className="w-4 h-4 text-slate-400" />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Register Property Modal */}
      {isPropertyModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs overflow-y-auto">
          <div className="bg-white border border-slate-100 rounded-xl max-w-2xl w-full shadow-2xl my-8">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-sans font-bold text-slate-800 text-sm flex items-center gap-2">
                <Building2 className="w-4 h-4 text-indigo-500" />
                <span>Register Mapped Assessor Parcel</span>
              </h3>
              <button
                onClick={() => setIsPropertyModalOpen(false)}
                className="p-1 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-600 font-bold transition-colors"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddProperty} className="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5 sm:col-span-2">
                  <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Assessor Address *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 812 S Broadway, Los Angeles, CA 90014"
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">City</label>
                  <input
                    type="text"
                    placeholder="e.g. Los Angeles"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">State</label>
                    <input
                      type="text"
                      maxLength={2}
                      value={state}
                      onChange={(e) => setState(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs text-slate-800 focus:outline-none"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Zip Code</label>
                    <input
                      type="text"
                      placeholder="90014"
                      value={zip}
                      onChange={(e) => setZip(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">County Parcel No. (APN)</label>
                  <input
                    type="text"
                    placeholder="5144-012-024"
                    value={apn}
                    onChange={(e) => setApn(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Zoning Municipal Code</label>
                  <input
                    type="text"
                    placeholder="e.g. LA-C5"
                    value={zoning}
                    onChange={(e) => setZoning(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none"
                  />
                </div>

                <div className="grid grid-cols-3 gap-2 sm:col-span-2">
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Lot SQFT</label>
                    <input
                      type="number"
                      placeholder="15000"
                      value={lotSqft}
                      onChange={(e) => setLotSqft(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Building SQFT</label>
                    <input
                      type="number"
                      placeholder="30000"
                      value={buildingSqft}
                      onChange={(e) => setBuildingSqft(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Year Built</label>
                    <input
                      type="number"
                      placeholder="1923"
                      value={yearBuilt}
                      onChange={(e) => setYearBuilt(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Current Existing Use</label>
                  <input
                    type="text"
                    placeholder="e.g. Unused Theater"
                    value={existingUse}
                    onChange={(e) => setExistingUse(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Business Tenant Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Former Rialto"
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2 sm:col-span-2">
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Assessed Land Value ($)</label>
                    <input
                      type="number"
                      placeholder="4000000"
                      value={landVal}
                      onChange={(e) => setLandVal(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Assessed Improvements ($)</label>
                    <input
                      type="number"
                      placeholder="2000000"
                      value={impVal}
                      onChange={(e) => setImpVal(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none"
                    />
                  </div>
                </div>

                <div className="space-y-1.5 sm:col-span-2">
                  <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Executive Corridor Memos / Notes</label>
                  <textarea
                    rows={2}
                    placeholder="Input municipal notes or structural highlights..."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none resize-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 border-t border-slate-100 pt-5 mt-4">
                <button
                  type="button"
                  onClick={() => setIsPropertyModalOpen(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors focus:outline-none"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  id="submit-register-property-btn"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg transition-colors focus:outline-none shadow-sm"
                >
                  Confirm Registry
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Attach Image Modal */}
      {isImageModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white border border-slate-100 rounded-xl max-w-md w-full shadow-2xl overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-sans font-bold text-slate-800 text-sm flex items-center gap-2">
                <FileImage className="w-4 h-4 text-indigo-500" />
                <span>Link Parcel Photo</span>
              </h3>
              <button
                onClick={() => setIsImageModalOpen(false)}
                className="p-1 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-600 font-bold transition-colors"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddImage} className="p-6 space-y-4">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Image URL *</label>
                <input
                  type="url"
                  required
                  placeholder="Paste direct Unsplash or static image link..."
                  value={imgUrl}
                  onChange={(e) => setImgUrl(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Image Type Category</label>
                <select
                  value={imgType}
                  onChange={(e) => setImgType(e.target.value as any)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs text-slate-800 focus:outline-none"
                >
                  <option value="uploaded">Uploaded Photograph</option>
                  <option value="street_view">Street Elevation</option>
                  <option value="satellite">Aerial Satellite</option>
                  <option value="uploaded">Parcel Zoning Layout</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Description / Notes</label>
                <input
                  type="text"
                  placeholder="e.g. Ground level storefront view showing timber pillars"
                  value={imgNotes}
                  onChange={(e) => setImgNotes(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 border-t border-slate-100 pt-4 mt-4">
                <button
                  type="button"
                  onClick={() => setIsImageModalOpen(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors focus:outline-none"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  id="submit-add-image-btn"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg transition-colors focus:outline-none"
                >
                  Attach Photo
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Launch AI Pipeline Modal */}
      {isWorkflowModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white border border-slate-100 rounded-xl max-w-md w-full shadow-2xl overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-sans font-bold text-slate-800 text-sm flex items-center gap-2">
                <Cpu className="w-4 h-4 text-indigo-500 animate-pulse" />
                <span>Launch Separate DEV-TOOLS AI Agent</span>
              </h3>
              <button
                onClick={() => setIsWorkflowModalOpen(false)}
                className="p-1 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-600 font-bold transition-colors"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleDispatchWorkflow} className="p-6 space-y-4">
              <div className="p-3 bg-indigo-50 border border-indigo-100 text-indigo-800 rounded-lg text-[11px] leading-relaxed">
                This triggers a multi-agent orchestrated process on the separate <strong>DEV-TOOLS WIMLOGIC</strong> backend. Workflows compile structured reports, financial pro-formas, and conceptual redevelopment options.
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Agent Target Directive</label>
                <select
                  value={workflowCode}
                  onChange={(e) => setWorkflowCode(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs text-slate-800 focus:outline-none"
                >
                  <option value="CRE_COMPREHENSIVE_ANALYZE">Full Feasibility Report & Financial Model</option>
                  <option value="CRE_ZONING_CHECK">Municipal Zoning & Setback Analysis</option>
                  <option value="CRE_CONCEPTUAL_DESIGN">3D Structural Concept Visualization Elevation</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase block font-mono">Priority Execution Queue</label>
                <select
                  value={priority}
                  onChange={(e) => setPriority(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs text-slate-800 focus:outline-none"
                >
                  <option value="Normal">Normal Queue</option>
                  <option value="High">High-Priority Direct (SLA)</option>
                  <option value="Critical">Immediate Resource Preemption</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 border-t border-slate-100 pt-4 mt-4">
                <button
                  type="button"
                  onClick={() => setIsWorkflowModalOpen(false)}
                  disabled={dispatching}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors focus:outline-none"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  id="submit-workflow-btn"
                  disabled={dispatching}
                  className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg transition-colors focus:outline-none shadow-sm shadow-indigo-650/15"
                >
                  {dispatching ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Dispatching...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5 fill-current" />
                      <span>Execute Handshake</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
