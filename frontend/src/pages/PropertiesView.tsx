import React, { useState, useEffect } from 'react';
import { propertyService } from '../services/propertyService';
import { projectService } from '../services/projectService';
import { propertyImageService } from '../services/propertyImageService';
import { workflowService } from '../services/workflowService';
import { Property, Project } from '../types/index';
import {
  Building2,
  Plus,
  Edit3,
  Trash2,
  X,
  ChevronRight,
  Eye,
  CheckCircle,
  AlertTriangle,
  Sparkles,
  Calendar,
  Image as ImageIcon,
  GitBranch,
  Users,
  FileText,
  LayoutGrid,
  MapPin,
  Layers,
  DollarSign,
  RefreshCw,
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

type TabKey =
  | 'overview'
  | 'address'
  | 'details'
  | 'parcel'
  | 'financial'
  | 'ownership'
  | 'images'
  | 'workflow'
  | 'ai'
  | 'notes';

const TABS: { key: TabKey; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { key: 'overview', label: 'Overview', icon: LayoutGrid },
  { key: 'address', label: 'Address & Location', icon: MapPin },
  { key: 'details', label: 'Property Details', icon: Building2 },
  { key: 'parcel', label: 'Parcel & Zoning', icon: Layers },
  { key: 'financial', label: 'Financial', icon: DollarSign },
  { key: 'ownership', label: 'Ownership', icon: Users },
  { key: 'images', label: 'Images', icon: ImageIcon },
  { key: 'workflow', label: 'Workflow', icon: GitBranch },
  { key: 'ai', label: 'AI Analysis', icon: Sparkles },
  { key: 'notes', label: 'Notes', icon: FileText },
];

export default function PropertiesView({ selectedProjectId, onSelectProject, onNavigate }: PropertiesViewProps) {
  const [properties, setProperties] = useState<Property[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectFilter, setActiveProjectFilter] = useState<string>(selectedProjectId || '');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const { success, error, warning } = useToast();

  const [activeProperty, setActiveProperty] = useState<Property | null>(null);
  const [isCreatingNew, setIsCreatingNew] = useState(false);
  const [activeTab, setActiveTab] = useState<TabKey>('overview');

  const [showJsonModal, setShowJsonModal] = useState(false);
  const [jsonModalData, setJsonModalData] = useState<any>(null);

  const [highlightMissing, setHighlightMissing] = useState(false);

  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [propertyToDelete, setPropertyToDelete] = useState<number | null>(null);

  const [imageCount, setImageCount] = useState<number | null>(null);
  const [workflowCount, setWorkflowCount] = useState<number | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

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

  const loadProjects = async () => {
    try {
      const res = await projectService.list({ limit: 300 });
      setProjects(res.items || []);

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

  const loadProperties = async () => {
    if (!activeProjectFilter) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const props = await propertyService.listByProject(activeProjectFilter);

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

  // Fetch real image/workflow counts for the Property Summary panel whenever
  // an existing (already-saved) property is opened in the workspace.
  useEffect(() => {
    async function loadCounts() {
      if (!activeProperty || !activeProperty.id || isCreatingNew) {
        setImageCount(null);
        setWorkflowCount(null);
        return;
      }
      try {
        const [imgRes, wfRes] = await Promise.all([
          propertyImageService.list({ property_id: activeProperty.id, include_deleted: false, limit: 1 }),
          workflowService.listExecutions({ property_id: activeProperty.id, limit: 1 }),
        ]);
        setImageCount(imgRes.count ?? 0);
        setWorkflowCount(wfRes.count ?? 0);
      } catch (err) {
        console.error('Failed to load property summary counts:', err);
        setImageCount(0);
        setWorkflowCount(0);
      }
    }
    loadCounts();
  }, [activeProperty?.id, isCreatingNew]);

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

    const addressFilled = !!(formData.address && formData.city && formData.state && formData.zip);
    const basicsFilled = !!(formData.building_sqft && formData.lot_sqft && formData.year_built);

    let financialFields = ['land_value', 'improvement_value', 'total_assessed_value'];
    let financialCount = financialFields.filter(f => formData[f as keyof typeof formData]).length;
    const financialsPercent = Math.round((financialCount / financialFields.length) * 100);

    const siteFilled = !!(formData.apn && formData.zoning_code);
    const marketPercent = (formData.business_name || formData.existing_use) ? 100 : 35;

    return {
      score: completenessScore,
      address: addressFilled,
      basics: basicsFilled,
      financials: financialsPercent,
      site: siteFilled,
      market: marketPercent,
      workflowReady: completenessScore >= 65
    };
  };

  const metrics = calculateCompletenessMetrics();

  const handleOpenCreate = () => {
    setIsCreatingNew(true);
    setActiveTab('overview');
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
    setActiveTab('overview');
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

  const handleSave = async (e?: React.FormEvent) => {
    e?.preventDefault();

    if (!formData.property_uid?.trim()) {
      warning('Property UID is required');
      setActiveTab('overview');
      return;
    }
    if (!formData.address?.trim()) {
      warning('Street Address is required');
      setHighlightMissing(true);
      setActiveTab('address');
      return;
    }

    try {
      if (!isCreatingNew && activeProperty && activeProperty.id) {
        const updated = await propertyService.update(activeProperty.id, formData);
        setActiveProperty(updated);
        setFormData(updated);
        success('Property parameters saved successfully.');
      } else {
        const newProp = await propertyService.create(formData);
        await propertyService.assignToProject(newProp.id, activeProjectFilter);
        success('Registered new property parcel.');
        setActiveProperty(null);
        loadProperties();
      }
    } catch (err: any) {
      console.error('Error submitting property:', err);
      error(err.message || 'UID duplication or DB validation error.');
    }
  };

  const handleRefresh = async () => {
    if (!activeProperty?.id) return;
    setIsRefreshing(true);
    try {
      const fresh = await propertyService.get(activeProperty.id);
      setActiveProperty(fresh);
      setFormData(fresh);
      success('Property data refreshed from the backend.');
    } catch (err: any) {
      console.error('Failed to refresh property:', err);
      error('Failed to refresh property data.');
    } finally {
      setIsRefreshing(false);
    }
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

  const toolbarFilters = (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
      <span style={{ fontSize: '0.625rem', fontWeight: 700, color: 'var(--color-neutral-400)', textTransform: 'uppercase', letterSpacing: '0.05em', fontFamily: 'var(--font-mono)' }}>
        Workspace:
      </span>
      <select
        value={activeProjectFilter}
        onChange={(e) => {
          setActiveProjectFilter(e.target.value);
          onSelectProject(e.target.value);
        }}
        className="enterprise-form-input"
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
      className="enterprise-btn enterprise-btn-primary"
      id="add-property-btn"
    >
      <Plus className="w-3.5 h-3.5" />
      Add Property
    </button>
  );

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
            title="Open Property Workspace"
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

  const highlightClass = (fieldValue: any) => {
    if (highlightMissing && (!fieldValue || fieldValue === 0 || fieldValue === '')) {
      return styles.fieldErrorHighlight;
    }
    return '';
  };

  const currentProject = projects.find((p) => p.project_id === activeProjectFilter);
  const propertyName = formData.business_name || formData.address || 'Unnamed Property';
  const combinedAddress = formData.address
    ? `${formData.address}, ${formData.city || ''}, ${formData.state || ''} ${formData.zip || ''}`
    : '—';

  return (
    <div className={styles.workspaceContainer}>

      {activeProperty ? (
        <div className="space-y-6 animate-fade-in">

          <div className={styles.headerArea}>
            <div className={styles.titleArea}>
              <div className={styles.breadcrumbs}>
                <span>AI-CRE WIMLOGIC</span>
                <ChevronRight className="w-3 h-3 text-slate-300" />
                <span className="cursor-pointer hover:text-slate-600" onClick={() => setActiveProperty(null)}>Properties</span>
                <ChevronRight className="w-3 h-3 text-slate-300" />
                <span className={styles.breadcrumbActive}>{formData.address || 'PROP NEW PARCEL'}</span>
              </div>
              <h1 className={styles.pageTitle}>Property Workspace</h1>
              <p className={styles.pageSubtitle}>Manage property metrics, land assessments, and AI-readiness context</p>
            </div>

            <div className={styles.headerActions}>
              <button
                type="button"
                onClick={() => setActiveProperty(null)}
                className={`enterprise-btn ${styles.btnCancel}`}
                id="cancel-details-btn"
              >
                Cancel
              </button>

              {!isCreatingNew && activeProperty.id && (
                <button
                  type="button"
                  onClick={() => confirmDeleteProperty(activeProperty.id!)}
                  className={`enterprise-btn ${styles.btnDelete}`}
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
              </button>
            </div>
          </div>

          <div className={styles.workspaceGrid}>

            <div className={styles.leftColumn}>

              <div className={styles.tabBar} id="property-workspace-tabs">
                {TABS.map((tab) => {
                  const TabIcon = tab.icon;
                  const isActive = activeTab === tab.key;
                  return (
                    <button
                      key={tab.key}
                      type="button"
                      onClick={() => setActiveTab(tab.key)}
                      className={`${styles.tabButton} ${isActive ? styles.tabButtonActive : ''}`}
                      id={`property-tab-${tab.key}`}
                    >
                      <TabIcon className="w-3.5 h-3.5" />
                      {tab.label}
                    </button>
                  );
                })}
              </div>

              <div className={styles.tabPanel}>

                {activeTab === 'overview' && (
                  <EnterpriseCard title="Overview" subtitle="Core identity fields for this property record.">
                    <div className={styles.formGrid}>
                      <div className={styles.col12}>
                        <FormField label="Property UID Code" required>
                          <input
                            type="text"
                            required
                            disabled={!isCreatingNew}
                            value={formData.property_uid || ''}
                            onChange={(e) => setFormData({ ...formData, property_uid: e.target.value })}
                            className={`enterprise-form-input ${highlightClass(formData.property_uid)}`}
                            placeholder="PROP-00001227"
                          />
                        </FormField>
                      </div>

                      <div className={styles.col6}>
                        <FormField label="Business / Entity Name" helpText="Used as the property's display name where a formal name isn't available.">
                          <input
                            type="text"
                            value={formData.business_name || ''}
                            onChange={(e) => setFormData({ ...formData, business_name: e.target.value })}
                            className="enterprise-form-input"
                            placeholder="e.g. Alhambra Plaza Inc"
                          />
                        </FormField>
                      </div>

                      <div className={styles.col6}>
                        <FormField label="Status">
                          <select
                            value={formData.status || 'Active'}
                            onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                            className="enterprise-form-input"
                          >
                            <option value="Active">Active (Ready for Workflow)</option>
                            <option value="Draft">Draft (Incomplete data)</option>
                            <option value="Flagged">Flagged (Conflicting tax data)</option>
                            <option value="Archived">Archived (historical reference)</option>
                          </select>
                        </FormField>
                      </div>
                    </div>
                  </EnterpriseCard>
                )}

                {activeTab === 'address' && (
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
                            className={`enterprise-form-input ${highlightClass(formData.state)}`}
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
                            className="enterprise-form-input"
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
                            className="enterprise-form-input"
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
                            value={combinedAddress === '—' ? '' : combinedAddress}
                            className="enterprise-form-input"
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
                            className="enterprise-form-input"
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
                            className="enterprise-form-input"
                            placeholder="-118.14872"
                          />
                        </FormField>
                      </div>

                    </div>
                  </EnterpriseCard>
                )}

                {activeTab === 'details' && (
                  <EnterpriseCard title="Property Details" subtitle="Structural characteristics and current use profile.">
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

                      <div className={styles.col12}>
                        <FormField label="Existing Use Profile">
                          <select
                            value={formData.existing_use || ''}
                            onChange={(e) => setFormData({ ...formData, existing_use: e.target.value })}
                            className="enterprise-form-input"
                          >
                            <option value="Retail Commercial">Retail Commercial</option>
                            <option value="Medical Office">Medical Office</option>
                            <option value="Warehouse / Industrial">Warehouse / Industrial</option>
                            <option value="Multi-Family Residential">Multi-Family Residential</option>
                            <option value="Mixed-Use Redevelopment">Mixed-Use Redevelopment</option>
                          </select>
                        </FormField>
                      </div>

                    </div>
                  </EnterpriseCard>
                )}

                {activeTab === 'parcel' && (
                  <EnterpriseCard title="Parcel & Zoning" subtitle="Assessor and municipal zoning identifiers.">
                    <div className={styles.formGrid}>

                      <div className={styles.col6}>
                        <FormField label="Zoning Designation Code" required>
                          <input
                            type="text"
                            required
                            value={formData.zoning_code || ''}
                            onChange={(e) => setFormData({ ...formData, zoning_code: e.target.value })}
                            className={`enterprise-form-input ${highlightClass(formData.zoning_code)}`}
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
                            className={`enterprise-form-input ${highlightClass(formData.apn)}`}
                            placeholder="e.g. 5342-016-012"
                          />
                        </FormField>
                      </div>

                    </div>
                  </EnterpriseCard>
                )}

                {activeTab === 'financial' && (
                  <EnterpriseCard title="Financial" subtitle="Tax assessments, land versus improvements valuations.">
                    <div className={styles.formGrid}>

                      <div className={styles.col4}>
                        <FormField label="Land Value ($)">
                          <input
                            type="number"
                            value={formData.land_value || ''}
                            onChange={(e) => setFormData({ ...formData, land_value: parseInt(e.target.value) || 0 })}
                            className={`enterprise-form-input ${highlightClass(formData.land_value)}`}
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
                            className={`enterprise-form-input ${highlightClass(formData.improvement_value)}`}
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
                            className={`enterprise-form-input ${highlightClass(formData.total_assessed_value)}`}
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
                            className="enterprise-form-input"
                          />
                        </FormField>
                      </div>

                      <div className={styles.col6}>
                        <FormField label="Calculated Improvement Value / SQFT">
                          <input
                            type="text"
                            readOnly
                            value={formData.improvement_value && formData.building_sqft ? `$${(formData.improvement_value / formData.building_sqft).toFixed(2)}` : '--'}
                            className="enterprise-form-input"
                          />
                        </FormField>
                      </div>

                    </div>
                  </EnterpriseCard>
                )}

                {activeTab === 'ownership' && (
                  <EnterpriseCard title="Ownership" subtitle="Data provenance, confidence, and secondary source references.">
                    <div className={styles.formGrid}>

                      <div className={styles.col6}>
                        <FormField label="Primary Data Source">
                          <select
                            value={formData.data_source || 'County Assessor'}
                            onChange={(e) => setFormData({ ...formData, data_source: e.target.value })}
                            className="enterprise-form-input"
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
                            className="enterprise-form-input"
                          >
                            <option value="High">High Confidence (95%+ match)</option>
                            <option value="Medium">Medium Confidence (80%+ match)</option>
                            <option value="Low">Low Confidence (Manual check needed)</option>
                          </select>
                        </FormField>
                      </div>

                      <div className={styles.col6}>
                        <FormField label="Record Source" helpText="How this property record originally entered the system.">
                          <input
                            type="text"
                            value={formData.source || ''}
                            onChange={(e) => setFormData({ ...formData, source: e.target.value })}
                            className="enterprise-form-input"
                            placeholder="e.g. Manual Entry"
                          />
                        </FormField>
                      </div>

                      <div className={styles.col12}>
                        <FormField label="Phase 2 Source Provider">
                          <select
                            value={formData.phase2_source || ''}
                            onChange={(e) => setFormData({ ...formData, phase2_source: e.target.value })}
                            className="enterprise-form-input"
                          >
                            <option value="">No Active Provider</option>
                            <option value="Google Maps">Google Maps API (Roads/Entrances)</option>
                            <option value="Esri ArcGIS">Esri ArcGIS Urban Core</option>
                            <option value="OpenStreetMap">OpenStreetMap Geodata</option>
                          </select>
                        </FormField>
                      </div>

                    </div>
                  </EnterpriseCard>
                )}

                {activeTab === 'images' && (
                  <EnterpriseCard title="Images" subtitle="Property image assets are managed in the dedicated Property Images workspace.">
                    <div className={styles.linkOutPanel}>
                      <ImageIcon className="w-8 h-8" style={{ color: 'var(--color-neutral-300)' }} />
                      <p className={styles.linkOutText}>
                        {imageCount === null
                          ? 'Save this property to begin attaching images.'
                          : `${imageCount} image${imageCount === 1 ? '' : 's'} currently attached to this property.`}
                      </p>
                      <button
                        type="button"
                        className="enterprise-btn enterprise-btn-secondary"
                        onClick={() => onNavigate('Property Images')}
                        disabled={!activeProperty.id}
                      >
                        Open Property Images
                      </button>
                    </div>
                  </EnterpriseCard>
                )}

                {activeTab === 'workflow' && (
                  <EnterpriseCard title="Workflow" subtitle="AI workflow executions are run and monitored from AI Orchestration.">
                    <div className={styles.linkOutPanel}>
                      <GitBranch className="w-8 h-8" style={{ color: 'var(--color-neutral-300)' }} />
                      <p className={styles.linkOutText}>
                        {workflowCount === null
                          ? 'Save this property to become eligible for AI workflows.'
                          : workflowCount > 0
                            ? `${workflowCount} workflow execution${workflowCount === 1 ? '' : 's'} on record for this property.`
                            : 'No workflow executions have been run for this property yet.'}
                      </p>
                      <button
                        type="button"
                        className="enterprise-btn enterprise-btn-secondary"
                        onClick={() => onNavigate('AI Orchestration')}
                        disabled={!activeProperty.id}
                      >
                        Open AI Orchestration
                      </button>
                    </div>
                  </EnterpriseCard>
                )}

                {activeTab === 'ai' && (
                  <EnterpriseCard title="AI Analysis" subtitle="Raw API payload context used by downstream AI workflows.">
                    <div className="space-y-4">
                      <FormField label="Municipal API Source Endpoint">
                        <input
                          type="text"
                          value={formData.api_source_url || ''}
                          onChange={(e) => setFormData({ ...formData, api_source_url: e.target.value })}
                          className="enterprise-form-input"
                          placeholder="https://api.cre-handshake.gov/parcels/"
                        />
                      </FormField>

                      <FormField label="Raw Database/API JSON Context" helpText="This structured payload is what DEV-TOOLS WIMLOGIC receives as AI analysis context.">
                        <textarea
                          rows={6}
                          value={formData.raw_api_json || ''}
                          onChange={(e) => setFormData({ ...formData, raw_api_json: e.target.value })}
                          className="enterprise-form-input"
                          placeholder="{}"
                        />
                      </FormField>

                      <div className={styles.jsonTriggerRow}>
                        <span className="enterprise-form-help">
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
                  </EnterpriseCard>
                )}

                {activeTab === 'notes' && (
                  <EnterpriseCard title="Notes" subtitle="Strategic descriptors and freeform property annotations.">
                    <FormField label="Strategic Descriptors & Property Notes">
                      <textarea
                        rows={10}
                        value={formData.notes || ''}
                        onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                        className={`enterprise-form-input ${highlightClass(formData.notes)}`}
                        placeholder="Add annotations about property easements, height limits, access corridors, pedestrian density, or street frontages..."
                      />
                    </FormField>
                  </EnterpriseCard>
                )}

              </div>
            </div>

            {/* RIGHT COLUMN: Fixed inspector panel - Quick Actions, then AI
                Readiness KPIs, then Property Summary. Stays visible and
                unchanged while the left tab selection changes. */}
            <div className={styles.rightColumn}>

              <EnterpriseCard title="Quick Actions">
                <div className={styles.quickActionsGrid}>
                  <button type="button" className="enterprise-btn enterprise-btn-primary" onClick={handleSave} id="quick-action-save">
                    Save
                  </button>
                  <button
                    type="button"
                    className="enterprise-btn enterprise-btn-secondary"
                    onClick={handleRefresh}
                    disabled={!activeProperty.id || isRefreshing}
                    id="quick-action-refresh"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
                    Refresh
                  </button>
                  <button
                    type="button"
                    className="enterprise-btn enterprise-btn-outline"
                    onClick={() => onNavigate('Property Images')}
                    disabled={!activeProperty.id}
                    id="quick-action-open-images"
                  >
                    Open Images
                  </button>
                  <button
                    type="button"
                    className="enterprise-btn enterprise-btn-outline"
                    onClick={() => onNavigate('AI Orchestration')}
                    disabled={!activeProperty.id}
                    id="quick-action-run-workflow"
                  >
                    Run Workflow
                  </button>
                  <button
                    type="button"
                    className="enterprise-btn enterprise-btn-ghost"
                    onClick={() => onNavigate('Workflow Results')}
                    disabled={!activeProperty.id}
                    id="quick-action-view-analysis"
                  >
                    View Analysis
                  </button>
                </div>
              </EnterpriseCard>

              <EnterpriseCard title="AI Readiness" subtitle="Real-time readiness signals for this property.">
                <div className={styles.kpiGrid}>

                  <div className={styles.kpiTile}>
                    <span className={styles.kpiLabel}>Data Completeness</span>
                    <span className={styles.kpiValue}>{metrics.score}%</span>
                  </div>

                  <div className={styles.kpiTile}>
                    <span className={styles.kpiLabel}>Image Readiness</span>
                    <span className={`${styles.kpiValue} ${styles.kpiValueText}`}>
                      {imageCount === null ? '—' : imageCount > 0 ? 'Ready' : 'Needs Images'}
                    </span>
                  </div>

                  <div className={styles.kpiTile}>
                    <span className={styles.kpiLabel}>Workflow Ready</span>
                    <span className={`${styles.kpiValue} ${styles.kpiValueText}`} style={{ color: metrics.workflowReady ? '#059669' : '#d97706' }}>
                      {metrics.workflowReady ? 'Ready' : 'Draft'}
                    </span>
                  </div>

                  <div className={styles.kpiTile}>
                    <span className={styles.kpiLabel}>Analysis Status</span>
                    <span className={`${styles.kpiValue} ${styles.kpiValueText}`}>
                      {workflowCount === null ? '—' : workflowCount > 0 ? 'Analyzed' : 'Pending'}
                    </span>
                  </div>

                </div>

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
                      <span>Property Details Block</span>
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
                      <span>Parcel & Zoning</span>
                    </div>
                    <span className={styles.checklistPercent}>{metrics.site ? '100%' : 'Incomplete'}</span>
                  </div>

                  <div className={styles.checklistItem}>
                    <div className={styles.checklistLabelWithIcon}>
                      {metrics.market === 100 ? (
                        <CheckCircle className={`w-4 h-4 ${styles.checklistCheckedIcon}`} />
                      ) : (
                        <AlertTriangle className={`w-4 h-4 ${styles.checklistWarningIcon}`} />
                      )}
                      <span>Ownership & Market Context</span>
                    </div>
                    <span className={styles.checklistPercent}>{metrics.market}%</span>
                  </div>

                </div>
              </EnterpriseCard>

              <EnterpriseCard title="Property Summary" subtitle="Live snapshot - stays visible while you edit other tabs.">
                <div className={styles.overviewList}>

                  <div className={styles.overviewItem}>
                    <span className={styles.overviewLabel}>Project</span>
                    <span className={styles.overviewValue}>{currentProject?.project_name || activeProjectFilter || '--'}</span>
                  </div>

                  <div className={styles.overviewItem}>
                    <span className={styles.overviewLabel}>Property Name</span>
                    <span className={styles.overviewValue}>{propertyName}</span>
                  </div>

                  <div className={styles.overviewItem}>
                    <span className={styles.overviewLabel}>Property Type</span>
                    <span className={styles.overviewValue}>{formData.existing_use || '--'}</span>
                  </div>

                  <div className={styles.overviewItem}>
                    <span className={styles.overviewLabel}>Address</span>
                    <span className={styles.overviewValue} style={{ textAlign: 'right' }}>{combinedAddress}</span>
                  </div>

                  <div className={styles.overviewItem}>
                    <span className={styles.overviewLabel}>Status</span>
                    <span className={styles.overviewValue}>
                      <span className={styles.stickyDot} style={{ backgroundColor: formData.status !== 'Active' ? '#f59e0b' : '#10b981' }} />
                      {formData.status || 'Active'}
                    </span>
                  </div>

                  <div className={styles.overviewItem}>
                    <span className={styles.overviewLabel}>Image Count</span>
                    <span className={styles.overviewValue}>{imageCount === null ? '—' : imageCount}</span>
                  </div>

                  <div className={styles.overviewItem}>
                    <span className={styles.overviewLabel}>Workflow Count</span>
                    <span className={styles.overviewValue}>{workflowCount === null ? '—' : workflowCount}</span>
                  </div>

                  <div className={styles.overviewItem}>
                    <span className={styles.overviewLabel}>Last Updated</span>
                    <span className={styles.overviewValue}>
                      <Calendar className="w-3.5 h-3.5" style={{ color: 'var(--color-neutral-400)' }} />
                      {formData.updated_at ? new Date(formData.updated_at).toLocaleDateString() : 'Just now'}
                    </span>
                  </div>

                  <div className={styles.overviewItem}>
                    <span className={styles.overviewLabel}>Property ID</span>
                    <span className={`${styles.overviewValue} ${styles.valueMono}`}>{formData.property_uid || '--'}</span>
                  </div>

                </div>
              </EnterpriseCard>

            </div>

          </div>

        </div>
      ) : (

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

      {showJsonModal && (
        <div className="enterprise-dialog-overlay" onClick={() => setShowJsonModal(false)}>
          <div
            className="enterprise-dialog-panel"
            style={{ maxWidth: '44rem' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="enterprise-dialog-header">
              <div>
                <h2 className="enterprise-dialog-title">WIMLOGIC Sandbox JSON Handshake</h2>
                <p className="enterprise-dialog-subtitle">
                  Verify the structured payload context extracted from the municipal geocoding assessor integrations.
                </p>
              </div>
              <button className={styles.modalCloseBtn} onClick={() => setShowJsonModal(false)}>
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="enterprise-dialog-body">
              <JsonViewer data={jsonModalData} title="Structured Assessor Metadata Payload" />
            </div>
            <div className="enterprise-dialog-footer">
              <button
                type="button"
                onClick={() => setShowJsonModal(false)}
                className="enterprise-btn enterprise-btn-primary"
              >
                Close Sandbox
              </button>
            </div>
          </div>
        </div>
      )}

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
