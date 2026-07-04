import React, { useState, useEffect } from 'react';
import { propertyService } from '../services/propertyService';
import { projectService } from '../services/projectService';
import { Property, Project } from '../types';
import { 
  Building2, 
  Plus, 
  Edit3, 
  Trash2, 
  X,
  MapPin,
  ChevronRight,
  ChevronDown,
  Eye,
  CheckCircle,
  AlertTriangle,
  Info,
  Layers,
  Sparkles,
  ArrowLeft,
  Settings as SettingsIcon,
  Search,
  Check,
  Calendar,
  DollarSign
} from 'lucide-react';
import EnterpriseToolbar from '../components/EnterpriseToolbar';
import EnterpriseTable from '../components/EnterpriseTable';
import ConfirmDialog from '../components/ConfirmDialog';
import FormField from '../components/FormField';
import EnterpriseCard from '../components/EnterpriseCard';
import JsonViewer from '../components/JsonViewer';
import { formatNumber } from '../utils/formatters';
import useToast from '../hooks/useToast';
import styles from './PropertiesView.module.css';

interface PropertiesViewProps {
  selectedProjectId: string;
  onSelectProject: (id: string) => void;
  onNavigate: (view: string) => void;
}

export default function PropertiesView({ selectedProjectId, onSelectProject, onNavigate }: PropertiesViewProps) {
  const [properties, setProperties] = useState<Property[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectFilter, setActiveProjectFilter] = useState<string>(selectedProjectId || '');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const { success, error, warning } = useToast();

  // Active workspace property state (when not null, we render the redesigned Property Workspace View)
  const [activeProperty, setActiveProperty] = useState<Property | null>(null);
  const [isCreatingNew, setIsCreatingNew] = useState(false);

  // Collapsible Advanced section state
  const [advancedOpen, setAdvancedOpen] = useState(false);

  // JSON viewer modal state
  const [showJsonModal, setShowJsonModal] = useState(false);
  const [jsonModalData, setJsonModalData] = useState<any>(null);

  // Missing fields highlight trigger
  const [highlightMissing, setHighlightMissing] = useState(false);

  // Delete state
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [propertyToDelete, setPropertyToDelete] = useState<number | null>(null);

  // Form states inside workspace
  const [formData, setFormData] = useState<Partial<Property>>({
    property_uid: '',
    address: '',
    city: '',
    state: '',
    zip: '',
    apn: '',
    latitude: undefined,
    longitude: undefined,
    lot_sqft: 0,
    building_sqft: 0,
    year_built: 1980,
    zoning_code: '',
    existing_use: '',
    business_name: '',
    land_value: 0,
    improvement_value: 0,
    total_assessed_value: 0,
    data_source: 'County Assessor',
    street_number: '',
    street_name: '',
    side_of_street: '',
    phase2_source: '',
    display_address: '',
    status: 'Active',
    source: 'Manual Entry',
    notes: '',
    confidence_score: 'High',
    raw_api_json: '',
    api_source_url: ''
  });

  // Load all projects for dropdowns and filtering
  const loadProjects = async () => {
    try {
      const res = await projectService.list({ limit: 300 });
      setProjects(res.items || []);
      
      // If we don't have an active project filter and have projects, default to first or selected
      if (!activeProjectFilter && res.items.length > 0) {
        if (selectedProjectId) {
          setActiveProjectFilter(selectedProjectId);
        } else {
          setActiveProjectFilter(res.items[0].project_id);
          onSelectProject(res.items[0].project_id);
        }
      }
    } catch (err) {
      console.error('Failed to load project references:', err);
      error('Failed to load project references.');
    }
  };

  // Load properties based on selected Project Filter
  const loadProperties = async () => {
    if (!activeProjectFilter) {
      setIsLoading(false);
      return;
    }
    
    setIsLoading(true);
    try {
      const props = await propertyService.listByProject(activeProjectFilter);
      
      // Apply client-side search query filter if active
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        setProperties(props.filter(p => 
          (p.address || '').toLowerCase().includes(query) ||
          (p.city || '').toLowerCase().includes(query) ||
          (p.property_uid || '').toLowerCase().includes(query) ||
          (p.apn || '').toLowerCase().includes(query)
        ));
      } else {
        setProperties(props);
      }
    } catch (err: any) {
      console.error('Error fetching properties:', err);
      error('Failed to load properties for this project context.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, [selectedProjectId]);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadProperties();
    }, 150);
    return () => clearTimeout(timer);
  }, [activeProjectFilter, searchQuery]);

  // Calculations for completeness metrics
  const calculateCompletenessMetrics = () => {
    const importantFields = [
      'property_uid', 'address', 'city', 'state', 'zip', 'apn',
      'building_sqft', 'lot_sqft', 'year_built', 'zoning_code',
      'existing_use', 'land_value', 'improvement_value', 'total_assessed_value',
      'street_number', 'street_name', 'side_of_street', 'notes'
    ];
    
    let filledCount = 0;
    importantFields.forEach(field => {
      const val = formData[field as keyof typeof formData];
      if (val !== undefined && val !== null && val !== '' && val !== 0) {
        filledCount++;
      }
    });

    const completenessScore = Math.round((filledCount / importantFields.length) * 100);
    
    // Check specific categories
    const addressFilled = !!(formData.address && formData.city && formData.state && formData.zip);
    const basicsFilled = !!(formData.building_sqft && formData.lot_sqft && formData.year_built);
    
    let financialFields = ['land_value', 'improvement_value', 'total_assessed_value'];
    let financialCount = financialFields.filter(f => formData[f as keyof typeof formData]).length;
    const financialsPercent = Math.round((financialCount / financialFields.length) * 100);

    const siteFilled = !!(formData.apn && formData.zoning_code);
    const zoningPercent = formData.zoning_code ? 100 : 0;
    const marketPercent = (formData.business_name || formData.existing_use) ? 100 : 35;

    return {
      score: completenessScore,
      address: addressFilled,
      basics: basicsFilled,
      financials: financialsPercent,
      site: siteFilled,
      zoning: zoningPercent,
      market: marketPercent,
      workflowReady: completenessScore >= 65
    };
  };

  const metrics = calculateCompletenessMetrics();

  const handleOpenCreate = () => {
    setIsCreatingNew(true);
    const generatedUid = `PROP-${Math.floor(10000000 + Math.random() * 90000000)}`;
    const emptyForm: Partial<Property> = {
      property_uid: generatedUid,
      address: '',
      city: '',
      state: 'CA',
      zip: '',
      apn: '',
      latitude: 34.08185,
      longitude: -118.14872,
      lot_sqft: 15000,
      building_sqft: 8500,
      year_built: 2005,
      zoning_code: 'C2-1',
      existing_use: 'Retail Commercial',
      business_name: '',
      land_value: 3600000,
      improvement_value: 2400000,
      total_assessed_value: 6000000,
      data_source: 'County Assessor',
      street_number: '',
      street_name: '',
      side_of_street: '-',
      phase2_source: 'Google Maps',
      display_address: '',
      status: 'Active',
      source: 'Manual Entry',
      notes: '',
      confidence_score: 'High',
      raw_api_json: JSON.stringify({
        source: "County Assessor API",
        parcel_type: "Commercial",
        tax_year: 2025,
        zoning_limits: {
          max_height_ft: 45,
          far_multiplier: 1.5,
          parking_ratio: "1:250 SQFT"
        }
      }, null, 2),
      api_source_url: 'https://api.cre-handshake.gov/parcels/' + generatedUid
    };
    setFormData(emptyForm);
    setActiveProperty(emptyForm as Property);
    setHighlightMissing(false);
  };

  const handleOpenEdit = (prop: Property) => {
    setIsCreatingNew(false);
    setFormData({ ...prop });
    setActiveProperty(prop);
    setHighlightMissing(false);
  };

  const confirmDeleteProperty = (id: number) => {
    setPropertyToDelete(id);
    setShowDeleteDialog(true);
  };

  const handleDelete = async () => {
    if (propertyToDelete === null) return;
    try {
      const assocRes = await propertyService.listAssociations({ 
          project_id: activeProjectFilter, 
          property_id: propertyToDelete 
      });
      if (assocRes.items && assocRes.items.length > 0) {
        for (const assoc of assocRes.items) {
          await propertyService.deleteAssociation(assoc.id);
        }
      }
      await propertyService.delete(propertyToDelete);
      success('Property removed successfully.');
      setActiveProperty(null);
      loadProperties();
    } catch (err: any) {
      console.error('Failed to delete property:', err);
      error(err.message || 'Error occurred during deletion sequence.');
    } finally {
      setShowDeleteDialog(false);
      setPropertyToDelete(null);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.property_uid?.trim()) {
      warning('Property UID is required');
      return;
    }
    if (!formData.address?.trim()) {
      warning('Street Address is required');
      setHighlightMissing(true);
      return;
    }

    try {
      if (!isCreatingNew && activeProperty && activeProperty.id) {
        // Edit flow
        await propertyService.update(activeProperty.id, formData);
        success('Property parameters saved successfully.');
      } else {
        // Create flow
        const newProp = await propertyService.create(formData);
        await propertyService.assignToProject(newProp.id, activeProjectFilter);
        success('Registered new property parcel.');
      }
      
      setActiveProperty(null);
      loadProperties();
    } catch (err: any) {
      console.error('Error submitting property:', err);
      error(err.message || 'UID duplication or DB validation error.');
    }
  };

  const handleHighlightFields = () => {
    setHighlightMissing(true);
    warning("Missing elements highlighted in soft red.");
    // Smooth scroll to top of form
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleTriggerViewJson = () => {
    try {
      const parsed = formData.raw_api_json ? JSON.parse(formData.raw_api_json) : null;
      setJsonModalData(parsed || { error: "No raw API payload registered" });
      setShowJsonModal(true);
    } catch (e) {
      setJsonModalData({ raw_text: formData.raw_api_json });
      setShowJsonModal(true);
    }
  };

  // Directory filter components
  const toolbarFilters = (
    <div className="flex items-center gap-2">
      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider font-mono">Workspace:</span>
      <select
        value={activeProjectFilter}
        onChange={(e) => {
          setActiveProjectFilter(e.target.value);
          onSelectProject(e.target.value);
        }}
        className="border border-slate-200 rounded-lg text-xs px-3 py-1.5 bg-slate-50 font-bold text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        id="properties-project-select"
      >
        {projects.length === 0 ? (
          <option value="">No Projects Available</option>
        ) : (
          projects.map((p) => (
            <option key={p.id} value={p.project_id}>
              [{p.project_id}] {p.project_name}
            </option>
          ))
        )}
      </select>
    </div>
  );

  const toolbarActions = (
    <button
      onClick={handleOpenCreate}
      disabled={projects.length === 0}
      className="enterprise-btn enterprise-btn-primary disabled:bg-slate-300 disabled:cursor-not-allowed"
      id="add-property-btn"
    >
      <Plus className="w-3.5 h-3.5" />
      Add Property
    </button>
  );

  // Table Column definitions
  const columns = [
    {
      key: 'property_uid',
      header: 'UID / APN',
      render: (prop: Property) => (
        <div>
          <div className="font-mono font-bold text-xs text-indigo-600 cursor-pointer hover:underline" onClick={() => handleOpenEdit(prop)}>
            {prop.property_uid}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-0.5">APN: {prop.apn || 'Unknown'}</div>
        </div>
      )
    },
    {
      key: 'address',
      header: 'Street Address',
      render: (prop: Property) => (
        <span className="font-sans font-semibold text-slate-800 text-xs cursor-pointer hover:text-indigo-600 transition-colors" onClick={() => handleOpenEdit(prop)}>
          {prop.address || 'Unnamed parcel'}
        </span>
      )
    },
    {
      key: 'city',
      header: 'City / State',
      render: (prop: Property) => (
        <div className="text-xs">
          <div>{prop.city || 'N/A'}</div>
          <div className="text-[10px] text-slate-400 mt-0.5">{prop.state || 'N/A'} {prop.zip}</div>
        </div>
      )
    },
    {
      key: 'metrics',
      header: 'Metrics',
      render: (prop: Property) => (
        <div className="font-mono text-[11px] text-slate-500">
          <div>BLDG: {prop.building_sqft ? formatNumber(prop.building_sqft) : '--'} SF</div>
          <div className="text-[10px] text-slate-400 mt-0.5">LOT: {prop.lot_sqft ? formatNumber(prop.lot_sqft) : '--'} SF</div>
        </div>
      )
    },
    {
      key: 'zoning_code',
      header: 'Zoning Code',
      render: (prop: Property) => (
        <span className="px-2 py-0.5 bg-indigo-50 border border-indigo-100 text-indigo-700 rounded text-[10px] font-mono font-semibold">
          {prop.zoning_code || 'N/A'}
        </span>
      )
    },
    {
      key: 'actions',
      header: 'Actions',
      align: 'right' as const,
      render: (prop: Property) => (
        <div className="flex items-center justify-end gap-1.5">
          <button
            onClick={() => handleOpenEdit(prop)}
            className="p-1.5 hover:bg-slate-100 text-slate-400 hover:text-indigo-600 rounded-lg transition-colors focus:outline-none"
            title="Open AI Workspace"
          >
            <Edit3 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => confirmDeleteProperty(prop.id)}
            className="p-1.5 hover:bg-slate-100 text-slate-400 hover:text-rose-600 rounded-lg transition-colors focus:outline-none"
            title="Delete property"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      )
    }
  ];

  // Helper for soft-red highlight on validation empty inputs
  const highlightClass = (fieldValue: any) => {
    if (highlightMissing && (!fieldValue || fieldValue === 0 || fieldValue === '')) {
      return styles.fieldErrorHighlight;
    }
    return '';
  };

  return (
    <div className={styles.workspaceContainer}>
      
      {/* 1. RENDER DETAILED PROPERTY WORKSPACE VIEW */}
      {activeProperty ? (
        <div className="space-y-6 animate-fade-in">
          
          {/* Breadcrumbs & Header bar */}
          <div className={styles.headerArea}>
            <div className={styles.titleArea}>
              <div className={styles.breadcrumbs}>
                <span>AI-CRE WIMLOGIC</span>
                <ChevronRight className="w-3 h-3 text-slate-300" />
                <span className="cursor-pointer hover:text-slate-600" onClick={() => setActiveProperty(null)}>Properties</span>
                <ChevronRight className="w-3 h-3 text-slate-300" />
                <span className={styles.breadcrumbActive}>{formData.address || 'PROP NEW PARCEL'}</span>
              </div>
              <h1 className={styles.pageTitle}>Property Details</h1>
              <p className={styles.pageSubtitle}>Manage property metrics, land assessments, and AI-readiness context</p>
            </div>
            
            <div className={styles.headerActions}>
              <button 
                type="button" 
                onClick={() => setActiveProperty(null)}
                className="enterprise-btn styles.btnCancel"
                id="cancel-details-btn"
              >
                Cancel
              </button>
              
              {!isCreatingNew && activeProperty.id && (
                <button 
                  type="button" 
                  onClick={() => confirmDeleteProperty(activeProperty.id!)}
                  className="enterprise-btn styles.btnDelete"
                  id="delete-details-btn"
                >
                  Delete
                </button>
              )}
              
              <button 
                type="button"
                onClick={handleSave}
                className={styles.btnSaveDropdown}
                id="save-details-btn"
              >
                <span>Save Changes</span>
                <ChevronDown className="w-3 h-3" />
              </button>
            </div>
          </div>

          {/* TWO-COLUMN LAYOUT GRID */}
          <div className={styles.workspaceGrid}>
            
            {/* LEFT COLUMN: Property Detail Form Sections */}
            <div className={styles.leftColumn}>
              
              {/* Card 1: Address & Location */}
              <EnterpriseCard title="Address & Location" subtitle="Geocoding indicators, street parameters, and mapping references.">
                <div className={styles.formGrid}>
                  
                  <div className={styles.col8}>
                    <FormField label="Street Address" required>
                      <input 
                        type="text" 
                        required
                        value={formData.address || ''} 
                        onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                        className={`enterprise-form-input ${highlightClass(formData.address)}`}
                        placeholder="e.g. 1227 W Valley Blvd"
                      />
                    </FormField>
                  </div>

                  <div className={styles.col4}>
                    <FormField label="City" required>
                      <input 
                        type="text" 
                        required
                        value={formData.city || ''} 
                        onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                        className={`enterprise-form-input ${highlightClass(formData.city)}`}
                        placeholder="Alhambra"
                      />
                    </FormField>
                  </div>

                  <div className={styles.col4}>
                    <FormField label="State" required>
                      <select 
                        value={formData.state || ''} 
                        onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                        className={`enterprise-form-input ${highlightClass(formData.state)} font-bold text-slate-700`}
                      >
                        <option value="CA">California (CA)</option>
                        <option value="NY">New York (NY)</option>
                        <option value="TX">Texas (TX)</option>
                        <option value="FL">Florida (FL)</option>
                        <option value="NV">Nevada (NV)</option>
                      </select>
                    </FormField>
                  </div>

                  <div className={styles.col4}>
                    <FormField label="Zip Code" required>
                      <input 
                        type="text" 
                        required
                        value={formData.zip || ''} 
                        onChange={(e) => setFormData({ ...formData, zip: e.target.value })}
                        className={`enterprise-form-input ${highlightClass(formData.zip)}`}
                        placeholder="91803"
                      />
                    </FormField>
                  </div>

                  <div className={styles.col4}>
                    <FormField label="Street Number">
                      <input 
                        type="text" 
                        value={formData.street_number || ''} 
                        onChange={(e) => setFormData({ ...formData, street_number: e.target.value })}
                        className="enterprise-form-input font-mono"
                        placeholder="1227"
                      />
                    </FormField>
                  </div>

                  <div className={styles.col6}>
                    <FormField label="Street Name">
                      <input 
                        type="text" 
                        value={formData.street_name || ''} 
                        onChange={(e) => setFormData({ ...formData, street_name: e.target.value })}
                        className="enterprise-form-input"
                        placeholder="W Valley Blvd"
                      />
                    </FormField>
                  </div>

                  <div className={styles.col6}>
                    <FormField label="Side of Street">
                      <select 
                        value={formData.side_of_street || ''} 
                        onChange={(e) => setFormData({ ...formData, side_of_street: e.target.value })}
                        className="enterprise-form-input text-slate-600"
                      >
                        <option value="-">-</option>
                        <option value="North">North Side</option>
                        <option value="South">South Side</option>
                        <option value="East">East Side</option>
                        <option value="West">West Side</option>
                        <option value="Both">Both Sides</option>
                      </select>
                    </FormField>
                  </div>

                  <div className={styles.col12}>
                    <FormField label="Display Address (Combined)">
                      <input 
                        type="text" 
                        readOnly
                        value={formData.address ? `${formData.address}, ${formData.city || ''}, ${formData.state || ''} ${formData.zip || ''}` : ''}
                        className="enterprise-form-input bg-slate-50 text-slate-500 font-semibold"
                        placeholder="Auto-calculated display representation"
                      />
                    </FormField>
                  </div>

                  <div className={styles.col6}>
                    <FormField label="Latitude (WGS 84)">
                      <input 
                        type="number" 
                        step="any"
                        value={formData.latitude || ''} 
                        onChange={(e) => setFormData({ ...formData, latitude: parseFloat(e.target.value) || undefined })}
                        className="enterprise-form-input font-mono"
                        placeholder="34.08185"
                      />
                    </FormField>
                  </div>

                  <div className={styles.col6}>
                    <FormField label="Longitude (WGS 84)">
                      <input 
                        type="number" 
                        step="any"
                        value={formData.longitude || ''} 
                        onChange={(e) => setFormData({ ...formData, longitude: parseFloat(e.target.value) || undefined })}
                        className="enterprise-form-input font-mono"
                        placeholder="-118.14872"
                      />
                    </FormField>
                  </div>

                </div>
              </EnterpriseCard>

              {/* Card 2: Property Basics */}
              <EnterpriseCard title="Property Basics" subtitle="Structured spatial and regulatory codes for municipal alignment.">
                <div className={styles.formGrid}>
                  
                  <div className={styles.col4}>
                    <FormField label="Lot Area (SQFT)" required>
                      <input 
                        type="number" 
                        required
                        value={formData.lot_sqft || ''} 
                        onChange={(e) => setFormData({ ...formData, lot_sqft: parseInt(e.target.value) || 0 })}
                        className={`enterprise-form-input ${highlightClass(formData.lot_sqft)}`}
                        placeholder="15,000"
                      />
                    </FormField>
                  </div>

                  <div className={styles.col4}>
                    <FormField label="Building Area (SQFT)" required>
                      <input 
                        type="number" 
                        required
                        value={formData.building_sqft || ''} 
                        onChange={(e) => setFormData({ ...formData, building_sqft: parseInt(e.target.value) || 0 })}
                        className={`enterprise-form-input ${highlightClass(formData.building_sqft)}`}
                        placeholder="8,500"
                      />
                    </FormField>
                  </div>

                  <div className={styles.col4}>
                    <FormField label="Year Built" required>
                      <input 
                        type="number" 
                        required
                        value={formData.year_built || ''} 
                        onChange={(e) => setFormData({ ...formData, year_built: parseInt(e.target.value) || 0 })}
                        className={`enterprise-form-input ${highlightClass(formData.year_built)}`}
                        placeholder="2005"
                      />
                    </FormField>
                  </div>

                  <div className={styles.col6}>
                    <FormField label="Existing Use Profile">
                      <select 
                        value={formData.existing_use || ''} 
                        onChange={(e) => setFormData({ ...formData, existing_use: e.target.value })}
                        className="enterprise-form-input text-slate-700"
                      >
                        <option value="Retail Commercial">Retail Commercial</option>
                        <option value="Medical Office">Medical Office</option>
                        <option value="Warehouse / Industrial">Warehouse / Industrial</option>
                        <option value="Multi-Family Residential">Multi-Family Residential</option>
                        <option value="Mixed-Use Redevelopment">Mixed-Use Redevelopment</option>
                      </select>
                    </FormField>
                  </div>

                  <div className={styles.col6}>
                    <FormField label="Zoning Designation Code" required>
                      <input 
                        type="text" 
                        required
                        value={formData.zoning_code || ''} 
                        onChange={(e) => setFormData({ ...formData, zoning_code: e.target.value })}
                        className={`enterprise-form-input font-mono ${highlightClass(formData.zoning_code)}`}
                        placeholder="e.g. C2-1"
                      />
                    </FormField>
                  </div>

                  <div className={styles.col6}>
                    <FormField label="Assessor Parcel Number (APN)" required>
                      <input 
                        type="text" 
                        required
                        value={formData.apn || ''} 
                        onChange={(e) => setFormData({ ...formData, apn: e.target.value })}
                        className={`enterprise-form-input font-mono ${highlightClass(formData.apn)}`}
                        placeholder="e.g. 5342-016-012"
                      />
                    </FormField>
                  </div>

                  <div className={styles.col6}>
                    <FormField label="Business / Entity Name">
                      <input 
                        type="text" 
                        value={formData.business_name || ''} 
                        onChange={(e) => setFormData({ ...formData, business_name: e.target.value })}
                        className="enterprise-form-input"
                        placeholder="e.g. Alhambra Plaza Inc"
                      />
                    </FormField>
                  </div>

                  <div className={styles.col12}>
                    <FormField label="Property UID Code" required>
                      <input 
                        type="text" 
                        required
                        disabled={!isCreatingNew}
                        value={formData.property_uid || ''} 
                        onChange={(e) => setFormData({ ...formData, property_uid: e.target.value })}
                        className="enterprise-form-input font-mono bg-slate-50 text-indigo-700 font-bold"
                        placeholder="PROP-00001227"
                      />
                    </FormField>
                  </div>

                </div>
              </EnterpriseCard>

              {/* Card 3: Land & Value */}
              <EnterpriseCard title="Land & Value" subtitle="Tax assessments, land versus improvements valuations.">
                <div className={styles.formGrid}>
                  
                  <div className={styles.col4}>
                    <FormField label="Land Value ($)">
                      <input 
                        type="number" 
                        value={formData.land_value || ''} 
                        onChange={(e) => setFormData({ ...formData, land_value: parseInt(e.target.value) || 0 })}
                        className={`enterprise-form-input font-mono ${highlightClass(formData.land_value)}`}
                        placeholder="3,600,000"
                      />
                    </FormField>
                  </div>

                  <div className={styles.col4}>
                    <FormField label="Improvement Value ($)">
                      <input 
                        type="number" 
                        value={formData.improvement_value || ''} 
                        onChange={(e) => setFormData({ ...formData, improvement_value: parseInt(e.target.value) || 0 })}
                        className={`enterprise-form-input font-mono ${highlightClass(formData.improvement_value)}`}
                        placeholder="2,400,000"
                      />
                    </FormField>
                  </div>

                  <div className={styles.col4}>
                    <FormField label="Total Assessed Value ($)">
                      <input 
                        type="number" 
                        value={formData.total_assessed_value || ''} 
                        onChange={(e) => setFormData({ ...formData, total_assessed_value: parseInt(e.target.value) || 0 })}
                        className={`enterprise-form-input font-mono ${highlightClass(formData.total_assessed_value)}`}
                        placeholder="6,000,000"
                      />
                    </FormField>
                  </div>

                  <div className={styles.col6}>
                    <FormField label="Calculated Land Value / SQFT">
                      <input 
                        type="text" 
                        readOnly
                        value={formData.land_value && formData.lot_sqft ? `$${(formData.land_value / formData.lot_sqft).toFixed(2)}` : '--'} 
                        className="enterprise-form-input bg-slate-50 text-slate-500 font-mono font-semibold"
                      />
                    </FormField>
                  </div>

                  <div className={styles.col6}>
                    <FormField label="Calculated Improvement Value / SQFT">
                      <input 
                        type="text" 
                        readOnly
                        value={formData.improvement_value && formData.building_sqft ? `$${(formData.improvement_value / formData.building_sqft).toFixed(2)}` : '--'} 
                        className="enterprise-form-input bg-slate-50 text-slate-500 font-mono font-semibold"
                      />
                    </FormField>
                  </div>

                  <div className={styles.col6}>
                    <FormField label="Primary Data Source">
                      <select 
                        value={formData.data_source || 'County Assessor'} 
                        onChange={(e) => setFormData({ ...formData, data_source: e.target.value })}
                        className="enterprise-form-input text-slate-700"
                      >
                        <option value="County Assessor">County Assessor Office</option>
                        <option value="Manual Entry">Manual Desk Review</option>
                        <option value="CoStar Group">CoStar Enterprise API</option>
                        <option value="PropStream">PropStream API Integration</option>
                      </select>
                    </FormField>
                  </div>

                  <div className={styles.col6}>
                    <FormField label="Assessor Data Confidence">
                      <select 
                        value={formData.confidence_score || 'High'} 
                        onChange={(e) => setFormData({ ...formData, confidence_score: e.target.value })}
                        className="enterprise-form-input text-slate-700"
                      >
                        <option value="High">High Confidence (95%+ match)</option>
                        <option value="Medium">Medium Confidence (80%+ match)</option>
                        <option value="Low">Low Confidence (Manual check needed)</option>
                      </select>
                    </FormField>
                  </div>

                </div>
              </EnterpriseCard>

              {/* Card 4: Location & Access */}
              <EnterpriseCard title="Location & Access" subtitle="Detailed entry points, physical notes, and phase 2 references.">
                <div className={styles.formGrid}>
                  
                  <div className={styles.col6}>
                    <FormField label="Phase 2 Source Provider">
                      <select 
                        value={formData.phase2_source || ''} 
                        onChange={(e) => setFormData({ ...formData, phase2_source: e.target.value })}
                        className="enterprise-form-input text-slate-700"
                      >
                        <option value="">No Active Provider</option>
                        <option value="Google Maps">Google Maps API (Roads/Entrances)</option>
                        <option value="Esri ArcGIS">Esri ArcGIS Urban Core</option>
                        <option value="OpenStreetMap">OpenStreetMap Geodata</option>
                      </select>
                    </FormField>
                  </div>

                  <div className={styles.col6}>
                    <FormField label="Integration Status Code">
                      <select 
                        value={formData.status || 'Active'} 
                        onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                        className="enterprise-form-input font-semibold text-slate-700"
                      >
                        <option value="Active">Active (Ready for Workflow)</option>
                        <option value="Draft">Draft (Incomplete data)</option>
                        <option value="Flagged">Flagged (Conflicting tax data)</option>
                        <option value="Archived">Archived (historical reference)</option>
                      </select>
                    </FormField>
                  </div>

                  <div className={styles.col12}>
                    <FormField label="Strategic Descriptors & Property Notes">
                      <textarea 
                        rows={4}
                        value={formData.notes || ''} 
                        onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                        className={`enterprise-form-input ${highlightClass(formData.notes)}`}
                        placeholder="Add annotations about property easements, height limits, access corridors, pedestrian density, or street frontages..."
                      />
                    </FormField>
                  </div>

                </div>
              </EnterpriseCard>

              {/* Card 5: AI & Metadata (Collapsible) */}
              <div className="space-y-3">
                <button 
                  type="button"
                  onClick={() => setAdvancedOpen(!advancedOpen)}
                  className={styles.advancedToggle}
                >
                  <span>Advanced Developer & AI Context</span>
                  <ChevronDown className={`w-4 h-4 transition-transform ${advancedOpen ? 'rotate-180' : ''}`} />
                </button>
                
                {advancedOpen && (
                  <div className={styles.advancedContent}>
                    <div className="space-y-4">
                      <FormField label="Municipal API Source Endpoint">
                        <input 
                          type="text" 
                          value={formData.api_source_url || ''} 
                          onChange={(e) => setFormData({ ...formData, api_source_url: e.target.value })}
                          className="enterprise-form-input font-mono text-[11px] text-slate-500"
                          placeholder="https://api.cre-handshake.gov/parcels/"
                        />
                      </FormField>

                      <FormField label="Raw Database/API JSON Context">
                        <textarea 
                          rows={3}
                          value={formData.raw_api_json || ''} 
                          onChange={(e) => setFormData({ ...formData, raw_api_json: e.target.value })}
                          className="enterprise-form-input font-mono text-[11px] text-emerald-600 bg-slate-950 border-slate-800"
                          placeholder="{}"
                        />
                      </FormField>

                      <div className={styles.jsonTriggerRow}>
                        <span className="text-[10px] font-medium text-slate-400">
                          Verify parsed developer payloads inside Sandbox context.
                        </span>
                        <button 
                          type="button" 
                          onClick={handleTriggerViewJson}
                          className={styles.btnJsonViewer}
                        >
                          <Eye className="w-3.5 h-3.5" />
                          Launch JSON Viewer
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>

            </div>

            {/* RIGHT COLUMN: Workspace Overview and AI Readiness Gauge */}
            <div className={styles.rightColumn}>
              
              {/* Card 1: Property Overview Panel */}
              <EnterpriseCard title="Property Overview" subtitle="Quick indicators representing registry handshake status.">
                <div className={styles.overviewList}>
                  
                  <div className={styles.overviewItem}>
                    <span className={styles.overviewLabel}>Property UID</span>
                    <span className={`${styles.overviewValue} ${styles.valueMono} text-indigo-600 font-bold`}>
                      {formData.property_uid || '--'}
                    </span>
                  </div>

                  <div className={styles.overviewItem}>
                    <span className={styles.overviewLabel}>Status</span>
                    <span className={styles.overviewValue}>
                      <span className={`${styles.stickyDot} ${formData.status !== 'Active' ? 'bg-amber-500' : 'bg-emerald-500'}`}></span>
                      {formData.status || 'Active'}
                    </span>
                  </div>

                  <div className={styles.overviewItem}>
                    <span className={styles.overviewLabel}>Confidence Score</span>
                    <span className={`${styles.overviewValue} text-emerald-600`}>
                      <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
                      {formData.confidence_score || 'High'}
                    </span>
                  </div>

                  <div className={styles.overviewItem}>
                    <span className={styles.overviewLabel}>Data Completeness</span>
                    <span className={`${styles.overviewValue} text-indigo-600 font-bold font-mono`}>
                      {metrics.score}%
                    </span>
                  </div>

                  <div className={styles.overviewItem}>
                    <span className={styles.overviewLabel}>Last Updated</span>
                    <span className={styles.overviewValue}>
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      {formData.updated_at ? new Date(formData.updated_at).toLocaleDateString() : 'Just now'}
                    </span>
                  </div>

                  <div className={styles.overviewItem}>
                    <span className={styles.overviewLabel}>Created At</span>
                    <span className={styles.overviewValue}>
                      {formData.created_at ? new Date(formData.created_at).toLocaleDateString() : 'Just now'}
                    </span>
                  </div>

                  <div className={styles.overviewItem}>
                    <span className={styles.overviewLabel}>Source</span>
                    <span className={styles.overviewValue}>{formData.source || 'Manual Entry'}</span>
                  </div>

                  <div className="pt-2 text-[11px] text-slate-500 italic leading-relaxed">
                    <strong>Lead Note:</strong> {formData.notes ? (formData.notes.length > 80 ? formData.notes.substring(0, 80) + '...' : formData.notes) : 'No strategic notes registered.'}
                  </div>

                </div>
              </EnterpriseCard>

              {/* Card 2: AI Readiness Progress Circle & Checklist */}
              <EnterpriseCard title="AI Readiness" subtitle="Data payload mapping audits for orchestrating WIMLOGIC AI.">
                
                <div className={styles.gaugeContainer}>
                  <div className={styles.gaugeCircleWrapper}>
                    <svg className={styles.gaugeSvg}>
                      <circle className={styles.gaugeBackground} cx="70" cy="70" r="60" />
                      <circle 
                        className={styles.gaugeValueCircle} 
                        cx="70" 
                        cy="70" 
                        r="60" 
                        strokeDasharray={2 * Math.PI * 60}
                        strokeDashoffset={((100 - metrics.score) / 100) * (2 * Math.PI * 60)}
                      />
                    </svg>
                    <div className={styles.gaugeTextContent}>
                      <span className={styles.gaugeValue}>{metrics.score}%</span>
                      <span className={styles.gaugeLabel} style={{ color: metrics.workflowReady ? '#10b981' : '#f59e0b' }}>
                        {metrics.workflowReady ? 'Ready for Workflows' : 'Draft Status'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Audit categories list */}
                <div className={styles.checklist}>
                  
                  <div className={styles.checklistItem}>
                    <div className={styles.checklistLabelWithIcon}>
                      {metrics.address ? (
                        <CheckCircle className={`w-4 h-4 ${styles.checklistCheckedIcon}`} />
                      ) : (
                        <AlertTriangle className={`w-4 h-4 ${styles.checklistWarningIcon}`} />
                      )}
                      <span>Address & Location Info</span>
                    </div>
                    <span className={styles.checklistPercent}>{metrics.address ? '100%' : 'Incomplete'}</span>
                  </div>

                  <div className={styles.checklistItem}>
                    <div className={styles.checklistLabelWithIcon}>
                      {metrics.basics ? (
                        <CheckCircle className={`w-4 h-4 ${styles.checklistCheckedIcon}`} />
                      ) : (
                        <AlertTriangle className={`w-4 h-4 ${styles.checklistWarningIcon}`} />
                      )}
                      <span>Property Basics Block</span>
                    </div>
                    <span className={styles.checklistPercent}>{metrics.basics ? '100%' : 'Incomplete'}</span>
                  </div>

                  <div className={styles.checklistItem}>
                    <div className={styles.checklistLabelWithIcon}>
                      {metrics.financials === 100 ? (
                        <CheckCircle className={`w-4 h-4 ${styles.checklistCheckedIcon}`} />
                      ) : (
                        <AlertTriangle className={`w-4 h-4 ${styles.checklistWarningIcon}`} />
                      )}
                      <span>Financial Information</span>
                    </div>
                    <span className={styles.checklistPercent}>{metrics.financials}%</span>
                  </div>

                  <div className={styles.checklistItem}>
                    <div className={styles.checklistLabelWithIcon}>
                      {metrics.site ? (
                        <CheckCircle className={`w-4 h-4 ${styles.checklistCheckedIcon}`} />
                      ) : (
                        <AlertTriangle className={`w-4 h-4 ${styles.checklistWarningIcon}`} />
                      )}
                      <span>Site & Land Information</span>
                    </div>
                    <span className={styles.checklistPercent}>{metrics.site ? '100%' : 'Incomplete'}</span>
                  </div>

                  <div className={styles.checklistItem}>
                    <div className={styles.checklistLabelWithIcon}>
                      {metrics.zoning === 100 ? (
                        <CheckCircle className={`w-4 h-4 ${styles.checklistCheckedIcon}`} />
                      ) : (
                        <AlertTriangle className={`w-4 h-4 ${styles.checklistWarningIcon}`} />
                      )}
                      <span>Zoning & Entitlements</span>
                    </div>
                    <span className={styles.checklistPercent}>{metrics.zoning}%</span>
                  </div>

                  <div className={styles.checklistItem}>
                    <div className={styles.checklistLabelWithIcon}>
                      {metrics.market === 100 ? (
                        <CheckCircle className={`w-4 h-4 ${styles.checklistCheckedIcon}`} />
                      ) : (
                        <AlertTriangle className={`w-4 h-4 ${styles.checklistWarningIcon}`} />
                      )}
                      <span>Market & Tenancy Context</span>
                    </div>
                    <span className={styles.checklistPercent}>{metrics.market}%</span>
                  </div>

                </div>

                <button 
                  type="button" 
                  onClick={metrics.workflowReady ? handleSave : handleHighlightFields}
                  className={styles.btnActionFull}
                >
                  {metrics.workflowReady ? 'Execute AI Workflow Readiness' : 'View Missing Information'}
                </button>

              </EnterpriseCard>

            </div>

          </div>

          {/* Sticky Quick-Action Bar */}
          <div className={styles.stickyBottomBar}>
            <div className={styles.stickyStatus}>
              <span className={styles.stickyDot}></span>
              <span>Workspace changes are buffered locally</span>
            </div>
            
            <div className={styles.stickyActions}>
              <button 
                type="button" 
                onClick={() => setActiveProperty(null)}
                className="px-4 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-500 rounded-lg text-xs font-semibold tracking-wide transition-all focus:outline-none"
              >
                Cancel
              </button>
              
              <button 
                type="button" 
                onClick={handleSave}
                className="px-5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold tracking-wide transition-all shadow-md shadow-indigo-600/10 focus:outline-none"
              >
                Save Changes
              </button>
            </div>
          </div>

        </div>
      ) : (
        
        // 2. RENDER THE PRIMARY PROPERTY DIRECTORY (LIST VIEW)
        <div className="space-y-6 animate-fade-in">
          
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-xl font-sans font-bold tracking-tight text-slate-900 flex items-center gap-2">
                <Building2 className="w-5 h-5 text-indigo-600" />
                Property Directory
              </h1>
              <p className="text-xs text-slate-500 mt-1">
                Manage parcel metrics, APNs, zoning parameters, and property boundaries assigned to projects.
              </p>
            </div>
          </div>

          <EnterpriseToolbar
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            searchPlaceholder="Filter properties by UID, street address, or city..."
            filterContent={toolbarFilters}
            actionContent={toolbarActions}
            id="properties-directory-toolbar"
          />

          <EnterpriseTable
            columns={columns}
            data={properties}
            rowKeyField="id"
            isLoading={isLoading}
            emptyTitle="No Properties Linked"
            emptyDescription={`No properties have been mapped to project "${activeProjectFilter}" yet. Add one to unlock AI orchestration pipelines.`}
            id="properties-directory-table"
          />

        </div>
      )}

      {/* MODAL WINDOWS */}
      
      {/* 1. Modal JSON Viewer for Advanced section */}
      {showJsonModal && (
        <div className={styles.modalOverlay} onClick={() => setShowJsonModal(false)}>
          <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2 className={styles.modalTitle}>WIMLOGIC Sandbox JSON Handshake</h2>
              <button className={styles.modalCloseBtn} onClick={() => setShowJsonModal(false)}>
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className={styles.modalBody}>
              <p className="text-xs text-slate-500 mb-4">
                Verify the structured payload context extracted from the municipal geocoding assessor integrations.
              </p>
              <JsonViewer data={jsonModalData} title="Structured Assessor Metadata Payload" />
            </div>
            <div className={styles.modalFooter}>
              <button 
                type="button" 
                onClick={() => setShowJsonModal(false)}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold"
              >
                Close Sandbox
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 2. Global Delete Confirm Dialog */}
      <ConfirmDialog
        isOpen={showDeleteDialog}
        title="Delete Property Parcel"
        message="Are you absolutely sure you want to delete this property? This will break its association with the active project, and any registered property images or workflows will be disconnected."
        confirmLabel="Permanently Delete"
        cancelLabel="Keep Property"
        isDanger={true}
        onConfirm={handleDelete}
        onCancel={() => {
          setShowDeleteDialog(false);
          setPropertyToDelete(null);
        }}
        id="property-delete-confirm"
      />

    </div>
  );
}
