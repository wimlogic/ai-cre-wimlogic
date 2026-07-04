import express from 'express';
import path from 'path';
import fs from 'fs';
import { createServer as createViteServer } from 'vite';
import { 
  CreProject, 
  CreProperty, 
  CrePropertyImage, 
  CreScanJob, 
  CreScan,
  CreProjectProperty, 
  CreWorkflowExecution, 
  CreWorkflowResult, 
  CreWorkflowEvent, 
  CreRenovationScenario, 
  CrePropertyAnalysisReport, 
  CreConceptDesign, 
  CreGeneratedAsset, 
  CreEstimate, 
  CreZoningNote,
  ApiUsageLog
} from './src/types';

const app = express();
const PORT = 3000;
const DB_FILE = path.join(process.cwd(), 'cre_db.json');

app.use(express.json());

// Structure of our DB file
interface CreDatabaseSchema {
  projects: CreProject[];
  properties: CreProperty[];
  project_properties: CreProjectProperty[];
  property_images: CrePropertyImage[];
  scan_jobs: CreScanJob[];
  scans: CreScan[];
  workflow_executions: CreWorkflowExecution[];
  workflow_results: CreWorkflowResult[];
  workflow_events: CreWorkflowEvent[];
  renovation_scenarios: CreRenovationScenario[];
  property_analysis_reports: CrePropertyAnalysisReport[];
  concept_designs: CreConceptDesign[];
  generated_assets: CreGeneratedAsset[];
  estimates: CreEstimate[];
  zoning_notes: CreZoningNote[];
  api_usage_logs: ApiUsageLog[];
  settings: {
    devtools_endpoint: string;
    google_maps_api_key: string;
    mls_integration_enabled: boolean;
    auto_trigger_workflow: boolean;
  };
}

const DEFAULT_DB: CreDatabaseSchema = {
  projects: [
    {
      id: 1,
      project_id: "PRJ-9021-LA",
      project_name: "Broadway Mixed-Use Redevelopment",
      description: "Analyzing high-density residential conversion potential for prime retail frontage on South Broadway, Los Angeles.",
      status: "active",
      default_city: "Los Angeles",
      default_state: "CA",
      main_street: "S Broadway",
      beginning_address: "800",
      ending_address: "1000",
      side: "both",
      scan_mode: "full",
      created_at: "2026-06-15 08:30:00",
      updated_at: "2026-06-20 14:22:15"
    },
    {
      id: 2,
      project_id: "PRJ-8012-NY",
      project_name: "Brooklyn Warehouse Industrial Conversion",
      description: "Repurposing light industrial logistics yards in Williamsburg into creative commercial hubs and modern retail bays.",
      status: "active",
      default_city: "Brooklyn",
      default_state: "NY",
      main_street: "Kent Ave",
      beginning_address: "150",
      ending_address: "300",
      side: "west",
      scan_mode: "quick",
      created_at: "2026-06-18 10:15:00",
      updated_at: "2026-06-25 11:40:00"
    },
    {
      id: 3,
      project_id: "PRJ-3049-MIA",
      project_name: "Brickell Plaza Transit-Oriented Office",
      description: "Evaluating land assembly and commercial zoning variances around Brickell public transit corridors.",
      status: "completed",
      default_city: "Miami",
      default_state: "FL",
      main_street: "Brickell Ave",
      beginning_address: "1100",
      ending_address: "1300",
      side: "both",
      scan_mode: "full",
      created_at: "2026-05-01 09:00:00",
      updated_at: "2026-05-28 17:00:00"
    }
  ],
  properties: [
    {
      id: 101,
      property_uid: "PROP-812-BWAY",
      address: "812 S Broadway, Los Angeles, CA 90014",
      city: "Los Angeles",
      state: "CA",
      zip: "90014",
      apn: "5144-012-024",
      latitude: 34.043122,
      longitude: -118.254128,
      lot_sqft: 14500,
      building_sqft: 28200,
      year_built: 1923,
      zoning_code: "LA-C5",
      existing_use: "Vacant Ground Floor Retail / Unused Upper Theater",
      business_name: "Former Rialto Theater Complex",
      land_value: 4800000.00,
      improvement_value: 3200000.00,
      total_assessed_value: 8000000.00,
      data_source: "LA County Assessor / MLS Link",
      created_at: "2026-06-15 09:00:00",
      updated_at: "2026-06-16 11:20:00",
      street_number: "812",
      street_name: "S Broadway",
      side_of_street: "east",
      phase2_source: "County Tax Database",
      display_address: "812 S Broadway",
      status: "under_review",
      source: "Google Street Scan",
      notes: "Historically significant facade. Potential tax credit candidate. High priority target.",
      confidence_score: "0.95"
    },
    {
      id: 102,
      property_uid: "PROP-910-BWAY",
      address: "910 S Broadway, Los Angeles, CA 90015",
      city: "Los Angeles",
      state: "CA",
      zip: "90015",
      apn: "5144-013-002",
      latitude: 34.041852,
      longitude: -118.256245,
      lot_sqft: 12000,
      building_sqft: 18000,
      year_built: 1955,
      zoning_code: "LA-C5",
      existing_use: "Commercial Car Wash / Single Story Parking Deck",
      business_name: "Broadway Express Auto Care",
      land_value: 6200000.00,
      improvement_value: 450000.00,
      total_assessed_value: 6650000.00,
      data_source: "LA County Assessor",
      created_at: "2026-06-15 09:12:00",
      updated_at: "2026-06-15 09:12:00",
      street_number: "910",
      street_name: "S Broadway",
      side_of_street: "west",
      display_address: "910 S Broadway",
      status: "approved",
      source: "Manual Import",
      notes: "Optimal parcel for complete demolition and rebuild. Low improvement ratio makes it highly favorable.",
      confidence_score: "0.89"
    },
    {
      id: 103,
      property_uid: "PROP-210-KENT",
      address: "210 Kent Ave, Brooklyn, NY 11249",
      city: "Brooklyn",
      state: "NY",
      zip: "11249",
      apn: "3-02345-0012",
      latitude: 40.718321,
      longitude: -73.964923,
      lot_sqft: 22000,
      building_sqft: 34000,
      year_built: 1910,
      zoning_code: "NY-M1-2",
      existing_use: "Light Industrial Warehouse & Storage Yard",
      business_name: "Kent Freight Logistics",
      land_value: 12500000.00,
      improvement_value: 1800000.00,
      total_assessed_value: 14300000.00,
      data_source: "NYC ACRIS",
      created_at: "2026-06-18 10:30:00",
      updated_at: "2026-06-19 14:00:00",
      street_number: "210",
      street_name: "Kent Ave",
      side_of_street: "west",
      display_address: "210 Kent Ave",
      status: "under_review",
      source: "Street Scan API",
      notes: "Williamsburg submarket. High demand for creative brick-and-beam spaces. Heavy remodel scenario recommended.",
      confidence_score: "0.98"
    }
  ],
  project_properties: [
    { id: 1, project_id: "PRJ-9021-LA", property_id: 101, selected: 1, created_at: "2026-06-15 09:05:00" },
    { id: 2, project_id: "PRJ-9021-LA", property_id: 102, selected: 1, created_at: "2026-06-15 09:15:00" },
    { id: 3, project_id: "PRJ-8012-NY", property_id: 103, selected: 1, created_at: "2026-06-18 10:45:00" }
  ],
  property_images: [
    {
      id: 1,
      property_id: 101,
      image_type: "street_view",
      image_url: "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=800&q=80",
      provider: "Google Street View",
      heading: 180.5,
      pitch: 5.2,
      fov: 90.0,
      cached_path: "/cached/812_broadway_street.jpg",
      created_at: "2026-06-15 09:30:00",
      is_deleted: 0
    },
    {
      id: 2,
      property_id: 101,
      image_type: "satellite",
      image_url: "https://images.unsplash.com/photo-1526778548025-fa2f459cd5c1?auto=format&fit=crop&w=800&q=80",
      provider: "Google Maps API",
      cached_path: "/cached/812_broadway_sat.jpg",
      created_at: "2026-06-15 09:32:00",
      is_deleted: 0
    },
    {
      id: 3,
      property_id: 102,
      image_type: "street_view",
      image_url: "https://images.unsplash.com/photo-1582407947304-fd86f028f716?auto=format&fit=crop&w=800&q=80",
      provider: "Google Street View",
      heading: 270.0,
      pitch: 2.0,
      fov: 90.0,
      cached_path: "/cached/910_broadway_street.jpg",
      created_at: "2026-06-15 09:40:00",
      is_deleted: 0
    },
    {
      id: 4,
      property_id: 103,
      image_type: "street_view",
      image_url: "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=800&q=80",
      provider: "Google Street View",
      heading: 45.1,
      pitch: -1.5,
      fov: 90.0,
      cached_path: "/cached/210_kent_street.jpg",
      created_at: "2026-06-18 11:00:00",
      is_deleted: 0
    }
  ],
  scan_jobs: [
    {
      id: 1,
      scan_id: "SCN-1029-LA",
      project_id: "PRJ-9021-LA",
      project_name: "Broadway Mixed-Use Redevelopment",
      main_street: "S Broadway",
      beginning_address: "800",
      ending_address: "1000",
      side_selection: "both",
      status: "completed",
      found_count: 2,
      notes: "Street scan completed successfully. Identified 812 S Broadway and 910 S Broadway.",
      created_at: "2026-06-15 08:45:00",
      updated_at: "2026-06-15 09:15:00",
      scan_source: "Mobile LIDAR Scanner Unit"
    }
  ],
  scans: [
    {
      id: 1,
      scan_uid: "SCN-1029-LA",
      city: "Los Angeles",
      state: "CA",
      main_street: "S Broadway",
      start_address: "800",
      end_address: "1000",
      side: "both",
      scan_mode: "full",
      status: "complete",
      created_at: "2026-06-15 08:45:00",
      updated_at: "2026-06-15 09:15:00",
      project_id: "PRJ-9021-LA",
      project_name: "Broadway Mixed-Use Redevelopment",
      scan_source: "Mobile LIDAR Scanner Unit"
    }
  ],
  workflow_executions: [
    {
      execution_id: 1,
      execution_number: "WF-EX-0001",
      project_id: 1,
      property_id: 101,
      scenario_id: 1,
      workflow_code: "CRE_COMPREHENSIVE_ANALYZE",
      workflow_version: "1.2.0",
      devtools_execution_id: "DEV-RUN-77341",
      status: "Completed",
      priority: "High",
      requested_by: 1,
      submitted_at: "2026-06-16 09:00:00",
      started_at: "2026-06-16 09:00:05",
      completed_at: "2026-06-16 09:01:12",
      retry_count: 0,
      created_at: "2026-06-16 09:00:00",
      updated_at: "2026-06-16 09:01:12"
    },
    {
      execution_id: 2,
      execution_number: "WF-EX-0002",
      project_id: 1,
      property_id: 102,
      scenario_id: 2,
      workflow_code: "CRE_ZONING_CHECK",
      workflow_version: "1.0.1",
      devtools_execution_id: "DEV-RUN-77345",
      status: "Completed",
      priority: "Normal",
      requested_by: 1,
      submitted_at: "2026-06-16 10:30:00",
      started_at: "2026-06-16 10:30:04",
      completed_at: "2026-06-16 10:30:45",
      retry_count: 0,
      created_at: "2026-06-16 10:30:00",
      updated_at: "2026-06-16 10:30:45"
    },
    {
      execution_id: 3,
      execution_number: "WF-EX-0003",
      project_id: 2,
      property_id: 103,
      scenario_id: 3,
      workflow_code: "CRE_CONCEPTUAL_DESIGN",
      workflow_version: "2.0.0",
      devtools_execution_id: "DEV-RUN-79012",
      status: "Running",
      priority: "Critical",
      requested_by: 1,
      submitted_at: "2026-06-30 14:00:00",
      started_at: "2026-06-30 14:00:10",
      retry_count: 0,
      created_at: "2026-06-30 14:00:00",
      updated_at: "2026-06-30 14:00:10"
    }
  ],
  workflow_results: [
    {
      result_id: 1,
      execution_id: 1,
      result_type: "COMPREHENSIVE_ANALYSIS",
      result_version: "1.2.0",
      response_json: JSON.stringify({
        score: 87.5,
        zoning: "C5 zoning allows up to 13:1 FAR with Transit-Oriented incentives. Facade preservation constraint applies.",
        financial: { low: 18000000, high: 24000000 },
        recommendation: "Pursue cosmetic facade refurbishment paired with multi-story apartment infill. Preserve ground floor commercial."
      }),
      normalized: 1,
      received_at: "2026-06-16 09:01:12",
      created_at: "2026-06-16 09:01:12"
    },
    {
      result_id: 2,
      execution_id: 2,
      result_type: "ZONING_CHECK",
      result_version: "1.0.1",
      response_json: JSON.stringify({
        allowed_uses: ["Retail", "Multi-family Residential", "Mixed-Use Hotel"],
        height_limit: "Unlimited",
        setbacks: "0ft street setback, 5ft rear setback required for residential levels"
      }),
      normalized: 1,
      received_at: "2026-06-16 10:30:45",
      created_at: "2026-06-16 10:30:45"
    }
  ],
  workflow_events: [
    { event_id: 1, execution_id: 1, event_type: "Trigger", status: "Success", message: "Dispatched workflow call to DEV-TOOLS WIMLOGIC orchestrator core.", created_at: "2026-06-16 09:00:01" },
    { event_id: 2, execution_id: 1, event_type: "Agent Handshake", status: "Success", message: "Document parsing agent connected to MLS county tax indexes.", created_at: "2026-06-16 09:00:15" },
    { event_id: 3, execution_id: 1, event_type: "Zoning Validation", status: "Success", message: "Zoning agent validated FAR ratios and facade heritage registries.", created_at: "2026-06-16 09:00:40" },
    { event_id: 4, execution_id: 1, event_type: "Completion", status: "Success", message: "Analysis report normalized and stored in central database. Dispatched generated assets.", created_at: "2026-06-16 09:01:12" },
    { event_id: 5, execution_id: 3, event_type: "Trigger", status: "Success", message: "Design generation request dispatched to DEV-TOOLS AI Imaging agent.", created_at: "2026-06-30 14:00:12" }
  ],
  renovation_scenarios: [
    {
      id: 1,
      project_id: "PRJ-9021-LA",
      property_id: 101,
      renovation_type: "Boutique Apartment & Facade Refurbishment",
      scenario_type: "co-living_residential",
      scenario_name: "Facade Preserved Residential Adaptive Reuse",
      rationale: "Leveraging high-ceiling timber structural bays for luxury loft apartments with a ground-floor restaurant arcade. High historic tax credit eligibility.",
      risk_level: "medium",
      estimated_complexity: "high",
      custom_notes: "Subject to LA Heritage Commission approvals. Retain structural timber posts.",
      status: "approved",
      source: "DEV-TOOLS Scenario Planner Agent",
      created_at: "2026-06-15 11:00:00",
      updated_at: "2026-06-16 09:01:12"
    },
    {
      id: 2,
      project_id: "PRJ-9021-LA",
      property_id: 102,
      renovation_type: "Complete Demolition & Mixed-Use Rebuild",
      scenario_type: "commercial_mixed_use",
      scenario_name: "Transit Oriented Core Highrise",
      rationale: "Due to low current improvement value, demolition of the single-story carwash allows maximum site density with a 15-story residential over retail highrise.",
      risk_level: "high",
      estimated_complexity: "high",
      custom_notes: "Requires standard soils engineering and street closure during utility tie-ins.",
      status: "draft",
      source: "DEV-TOOLS Scenario Planner Agent",
      created_at: "2026-06-15 11:15:00",
      updated_at: "2026-06-15 11:15:00"
    },
    {
      id: 3,
      project_id: "PRJ-8012-NY",
      property_id: 103,
      renovation_type: "Creative Commercial & Micro Retail Incubator",
      scenario_type: "creative_office_incubator",
      scenario_name: "Williamsburg Brick-and-Beam Commercial",
      rationale: "Repurpose timber roof beams and exposed brickwork into a high-end multi-tenant commercial studio space with dynamic hot-desking, shared meeting pods, and coffee court.",
      risk_level: "low",
      estimated_complexity: "medium",
      custom_notes: "Highly aligned with surrounding submarket office demographics.",
      status: "approved",
      source: "DEV-TOOLS Scenario Planner Agent",
      created_at: "2026-06-19 09:00:00",
      updated_at: "2026-06-19 14:00:00"
    }
  ],
  property_analysis_reports: [
    {
      id: 1,
      project_id: "PRJ-9021-LA",
      property_id: 101,
      scenario_id: 1,
      estimate_low: 18000000.00,
      estimate_high: 24000000.00,
      zoning_notes: "C5-FAR incentives. Heritage preservation zone. Rear residential setback must align with code.",
      risk_notes: "Structural retrofitting required for unreinforced masonry portions.",
      recommendation: "Proceed with Schematic Design phase. Lock in historic tax consultants.",
      score: 87.5,
      report_json: JSON.stringify({
        zoning_score: 92,
        financial_irr: "21.4%",
        cash_on_cash: "8.2%",
        environmental_risk: "Low"
      }),
      created_at: "2026-06-16 09:01:12",
      updated_at: "2026-06-16 09:01:12",
      workflow_execution_id: 1,
      workflow_result_id: 1,
      analysis_version: "1.2.0",
      confidence_score: 94.0,
      workflow_status: "Completed",
      completed_at: "2026-06-16 09:01:12"
    }
  ],
  concept_designs: [
    {
      id: 1,
      project_id: "PRJ-9021-LA",
      property_id: 101,
      scenario_id: 1,
      title: "Rialto Lofts & Atrium Concept",
      concept_prompt: "Exterior hyper-realistic rendering of a historic 1920s theater facade integrated with a modern steel-and-glass residential expansion. Sunset warm lighting, bustling pedestrian sidewalk, lush green roof balconies.",
      concept_notes: "Combines classic masonry detailing with sleek, lightweight floor plates above.",
      image_reference_ids: JSON.stringify([1]),
      status: "approved",
      created_at: "2026-06-16 11:30:00",
      updated_at: "2026-06-17 14:00:00",
      workflow_execution_id: 1,
      design_version: "V1.0",
      approved_by: 1,
      approved_at: "2026-06-17 14:00:00"
    }
  ],
  generated_assets: [
    {
      asset_id: 1,
      execution_id: 1,
      property_id: 101,
      asset_type: "pdf",
      asset_category: "Feasibility Study",
      title: "S Broadway 812 Comprehensive Feasibility PDF",
      description: "Complete architectural, structural, and financial pro-forma analysis for Broadway adaptive lofts.",
      file_name: "bway_812_feasibility_v1.pdf",
      storage_path: "/assets/documents/bway_812_feasibility_v1.pdf",
      thumbnail_path: "https://images.unsplash.com/photo-1586075010923-2dd45e9b2d4f?auto=format&fit=crop&w=150&q=80",
      mime_type: "application/pdf",
      file_size: 4850000,
      version: "1.2.0",
      created_at: "2026-06-16 09:01:12"
    },
    {
      asset_id: 2,
      execution_id: 1,
      property_id: 101,
      asset_type: "spreadsheet",
      asset_category: "Financial Model",
      title: "Broadway Lofts Adaptive IRR Excel Pro-Forma",
      description: "30-year cash flow projections, construction financing schedules, and dynamic equity waterfalls.",
      file_name: "bway_lofts_irr_model.xlsx",
      storage_path: "/assets/documents/bway_lofts_irr_model.xlsx",
      mime_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      file_size: 1240000,
      version: "1.2.0",
      created_at: "2026-06-16 09:02:00"
    }
  ],
  estimates: [
    {
      id: 1,
      property_id: 101,
      scenario: "heavy_remodel",
      proposed_use: "Luxury Lofts / Ground Retail Atrium",
      proposed_building_sqft: 32000,
      proposed_units: 24,
      low_cost: 16500000.00,
      mid_cost: 18000000.00,
      high_cost: 21500000.00,
      cost_per_sqft_low: 515.00,
      cost_per_sqft_high: 670.00,
      assumptions: "Maintains existing frame. Assumes high-end structural timber restoration and full MEP overrides.",
      risk_level: "medium",
      created_at: "2026-06-15 11:30:00",
      workflow_execution_id: 1,
      estimate_source: "DEV-TOOLS Feasibility Pro",
      estimate_version: "1.2.0"
    }
  ],
  zoning_notes: [
    {
      id: 1,
      property_id: 101,
      zoning_code: "LA-C5",
      allowed_use_summary: "Allows full retail, hotel, creative office, and multi-family high-density development. High FAR baseline.",
      conditional_use_notes: "Adaptive reuse ordinance triggers exemption from residential parking spaces ratios.",
      parking_notes: "Exempt from standard minimums. Bicycle bays and subway correlation multipliers apply.",
      entitlement_risk: "low",
      source_url: "https://zoning.lacity.org/c5-rules",
      created_at: "2026-06-15 10:00:00"
    }
  ],
  api_usage_logs: [
    { id: 1, provider: "Google Maps", api_name: "Street View static API", endpoint: "/maps/api/streetview", request_count: 42, estimated_cost: 0.294, created_at: "2026-06-29 18:00:00" },
    { id: 2, provider: "MLS Connect", api_name: "Parcel Assessor API", endpoint: "/mls/parcels/search", request_count: 15, estimated_cost: 4.500, created_at: "2026-06-29 18:15:00" },
    { id: 3, provider: "DEV-TOOLS WIMLOGIC", api_name: "Agent Orchestration API", endpoint: "/devtools/v1/agent-workflows", request_count: 8, estimated_cost: 16.000, created_at: "2026-06-30 14:00:00" }
  ],
  settings: {
    devtools_endpoint: "https://devtools-gateway.wimlogic.net/api/v1",
    google_maps_api_key: "AIzaSyD_EXAMPLE_KEY_FOR_MOCK",
    mls_integration_enabled: true,
    auto_trigger_workflow: false
  }
};

// Function to load database
function loadDb(): CreDatabaseSchema {
  try {
    if (fs.existsSync(DB_FILE)) {
      const fileData = fs.readFileSync(DB_FILE, 'utf-8');
      return JSON.parse(fileData);
    }
  } catch (err) {
    console.error("Failed to read database file, restoring defaults:", err);
  }
  // Write default DB file
  fs.writeFileSync(DB_FILE, JSON.stringify(DEFAULT_DB, null, 2), 'utf-8');
  return DEFAULT_DB;
}

// Function to save database
function saveDb(db: CreDatabaseSchema) {
  try {
    fs.writeFileSync(DB_FILE, JSON.stringify(db, null, 2), 'utf-8');
  } catch (err) {
    console.error("Failed to write to database file:", err);
  }
}

// Ensure the local database loads on startup
let dbState = loadDb();

// API Endpoints Complying with WIMLOGIC API Standards:
// Standard Endpoint Prefix: /api/v1

// GET Stats Summary
app.get('/api/v1/stats', (req, res) => {
  const activeWorkflowsCount = dbState.workflow_executions.filter(e => e.status === 'Running' || e.status === 'Submitted').length;
  const apiTotalCost = dbState.api_usage_logs.reduce((sum, curr) => sum + (curr.estimated_cost || 0), 0);

  const stats = {
    totalProjects: dbState.projects.length,
    totalProperties: dbState.properties.length,
    activeWorkflows: activeWorkflowsCount,
    generatedAssetsCount: dbState.generated_assets.length,
    apiUsageCost: Number(apiTotalCost.toFixed(2))
  };

  res.json({
    status: 200,
    message: "Stats compiled successfully",
    data: stats
  });
});

// GET Settings
app.get('/api/v1/settings', (req, res) => {
  res.json({
    status: 200,
    message: "Settings loaded successfully",
    data: dbState.settings
  });
});

// PUT Settings
app.put('/api/v1/settings', (req, res) => {
  const newSettings = req.body;
  dbState.settings = { ...dbState.settings, ...newSettings };
  saveDb(dbState);
  res.json({
    status: 200,
    message: "Settings updated successfully",
    data: dbState.settings
  });
});

// --- PROJECTS ---
// GET Projects (List with count and items)
app.get('/api/v1/projects', (req, res) => {
  const { status, search } = req.query;
  let items = dbState.projects;

  if (status) {
    items = items.filter(p => p.status === status);
  }

  if (search) {
    const q = String(search).toLowerCase();
    items = items.filter(p => 
      p.project_name.toLowerCase().includes(q) || 
      p.project_id.toLowerCase().includes(q) ||
      p.description.toLowerCase().includes(q)
    );
  }

  res.json({
    count: items.length,
    items: items
  });
});

// GET Project Single
app.get('/api/v1/projects/:id', (req, res) => {
  const idStr = req.params.id;
  // Can look up by incremental id or project_id string
  const project = dbState.projects.find(p => p.id === Number(idStr) || p.project_id === idStr);
  if (!project) {
    return res.status(404).json({
      success: false,
      error: { code: "NOT_FOUND", message: "Project not found" }
    });
  }
  res.json(project);
});

// POST Create Project
app.post('/api/v1/projects', (req, res) => {
  const { project_name, description, status, default_city, default_state, main_street, beginning_address, ending_address, side, scan_mode } = req.body;
  if (!project_name) {
    return res.status(400).json({
      success: false,
      error: { code: "VALIDATION_ERROR", message: "project_name is a required parameter" }
    });
  }

  const cleanProjectName = String(project_name).trim();
  const rawPrefix = cleanProjectName.replace(/[^a-zA-Z0-9]/g, '').slice(0, 4).toUpperCase();
  const randNum = Math.floor(1000 + Math.random() * 9000);
  const project_id = `PRJ-${randNum}-${rawPrefix || "CRE"}`;

  const timestamp = new Date().toISOString().replace('T', ' ').slice(0, 19);

  const newProject: CreProject = {
    id: dbState.projects.length > 0 ? Math.max(...dbState.projects.map(p => p.id)) + 1 : 1,
    project_id,
    project_name: cleanProjectName,
    description: description || "Custom Commercial Real Estate research workspace.",
    status: status || "active",
    default_city: default_city || "Los Angeles",
    default_state: default_state || "CA",
    main_street,
    beginning_address,
    ending_address,
    side: side || "both",
    scan_mode: scan_mode || "quick",
    created_at: timestamp,
    updated_at: timestamp
  };

  dbState.projects.push(newProject);

  // If a main_street and bounding address exist, create a corresponding seed scan job
  if (main_street && beginning_address && ending_address) {
    const scanId = `SCN-${Math.floor(1000 + Math.random() * 9000)}-${rawPrefix || "CRE"}`;
    const newScanJob: CreScanJob = {
      id: dbState.scan_jobs.length > 0 ? Math.max(...dbState.scan_jobs.map(s => s.id)) + 1 : 1,
      scan_id: scanId,
      project_id: project_id,
      project_name: cleanProjectName,
      main_street,
      beginning_address,
      ending_address,
      side_selection: side || "both",
      status: "created",
      found_count: 0,
      notes: "Scan queued for county assessor and Google Street View sync.",
      created_at: timestamp,
      updated_at: timestamp,
      scan_source: "System GIS Orchestrator"
    };
    dbState.scan_jobs.push(newScanJob);

    // Also populate a scan list entity
    const newScan: CreScan = {
      id: newScanJob.id,
      scan_uid: scanId,
      city: default_city || "Los Angeles",
      state: default_state || "CA",
      main_street,
      start_address: beginning_address,
      end_address: ending_address,
      side: (side as any) || "both",
      scan_mode: (scan_mode as any) || "quick",
      status: "pending",
      created_at: timestamp,
      updated_at: timestamp,
      project_id: project_id,
      project_name: cleanProjectName,
      scan_source: "System GIS Orchestrator"
    };
    dbState.scans.push(newScan);
  }

  saveDb(dbState);
  res.status(201).json(newProject);
});

// DELETE Project
app.delete('/api/v1/projects/:id', (req, res) => {
  const idNum = Number(req.params.id);
  const exists = dbState.projects.some(p => p.id === idNum);
  if (!exists) {
    return res.status(404).json({
      success: false,
      error: { code: "NOT_FOUND", message: "Project not found" }
    });
  }
  dbState.projects = dbState.projects.filter(p => p.id !== idNum);
  saveDb(dbState);
  res.json({ success: true });
});


// --- PROPERTIES ---
// GET Properties (List with count and items)
app.get('/api/v1/properties', (req, res) => {
  const { project_id, search, status } = req.query;
  let items = dbState.properties;

  // Filter properties by project mapping if project_id is supplied
  if (project_id) {
    const mappedIds = dbState.project_properties
      .filter(pp => pp.project_id === project_id)
      .map(pp => pp.property_id);
    items = items.filter(prop => mappedIds.includes(prop.id));
  }

  if (status) {
    items = items.filter(prop => prop.status === status);
  }

  if (search) {
    const q = String(search).toLowerCase();
    items = items.filter(prop => 
      (prop.address && prop.address.toLowerCase().includes(q)) ||
      (prop.business_name && prop.business_name.toLowerCase().includes(q)) ||
      (prop.apn && prop.apn.toLowerCase().includes(q)) ||
      (prop.property_uid && prop.property_uid.toLowerCase().includes(q))
    );
  }

  res.json({
    count: items.length,
    items: items
  });
});

// GET Property Single (Returns single directly)
app.get('/api/v1/properties/:id', (req, res) => {
  const idNum = Number(req.params.id);
  const property = dbState.properties.find(p => p.id === idNum);
  if (!property) {
    return res.status(404).json({
      success: false,
      error: { code: "NOT_FOUND", message: "Property not found" }
    });
  }
  res.json(property);
});

// POST Create Property (Can map to an existing project)
app.post('/api/v1/properties', (req, res) => {
  const { 
    project_id, address, city, state, zip, apn, 
    building_sqft, lot_sqft, year_built, zoning_code, 
    existing_use, business_name, land_value, improvement_value, notes 
  } = req.body;

  if (!address) {
    return res.status(400).json({
      success: false,
      error: { code: "VALIDATION_ERROR", message: "address is required" }
    });
  }

  const timestamp = new Date().toISOString().replace('T', ' ').slice(0, 19);
  const cleanAddress = String(address).trim();
  const uidSuffix = Math.floor(100 + Math.random() * 900);
  const property_uid = `PROP-${uidSuffix}-${(city || "CRE").toUpperCase().slice(0, 4)}`;

  const lVal = Number(land_value) || 1200000;
  const iVal = Number(improvement_value) || 800000;
  const newPropertyId = dbState.properties.length > 0 ? Math.max(...dbState.properties.map(p => p.id)) + 1 : 101;

  const newProperty: CreProperty = {
    id: newPropertyId,
    property_uid,
    address: cleanAddress,
    city: city || "Los Angeles",
    state: state || "CA",
    zip: zip || "90014",
    apn: apn || `${Math.floor(1000 + Math.random()*9000)}-${Math.floor(100 + Math.random()*900)}-${Math.floor(10 + Math.random()*90)}`,
    latitude: 34.043 + (Math.random() - 0.5) * 0.01,
    longitude: -118.25 + (Math.random() - 0.5) * 0.01,
    lot_sqft: Number(lot_sqft) || 8500,
    building_sqft: Number(building_sqft) || 12000,
    year_built: Number(year_built) || 1960,
    zoning_code: zoning_code || "LA-C5",
    existing_use: existing_use || "Mixed Use Commercial Storefront",
    business_name: business_name || "Unbranded Commercial Space",
    land_value: lVal,
    improvement_value: iVal,
    total_assessed_value: lVal + iVal,
    data_source: "Manual Assessor Record Integration",
    created_at: timestamp,
    updated_at: timestamp,
    display_address: cleanAddress.split(',')[0],
    status: "under_review",
    source: "Manual Input Link",
    notes: notes || "Added property to workspace queue for automated analysis.",
    confidence_score: "0.91"
  };

  dbState.properties.push(newProperty);

  // Link property to the supplied project_id
  if (project_id) {
    const newProjProp: CreProjectProperty = {
      id: dbState.project_properties.length > 0 ? Math.max(...dbState.project_properties.map(pp => pp.id)) + 1 : 1,
      project_id: String(project_id),
      property_id: newPropertyId,
      selected: 1,
      created_at: timestamp
    };
    dbState.project_properties.push(newProjProp);
  }

  // Generate some realistic seed zoning records
  const newZoning: CreZoningNote = {
    id: dbState.zoning_notes.length > 0 ? Math.max(...dbState.zoning_notes.map(z => z.id)) + 1 : 1,
    property_id: newPropertyId,
    zoning_code: newProperty.zoning_code,
    allowed_use_summary: `Allows high-density ${newProperty.existing_use} and general residential conversions.`,
    conditional_use_notes: "Subject to standard municipal parking reductions and setback allowances.",
    parking_notes: "1 slot per 1000 square feet baseline, reduced in transit lanes.",
    entitlement_risk: "low",
    created_at: timestamp
  };
  dbState.zoning_notes.push(newZoning);

  saveDb(dbState);
  res.status(201).json(newProperty);
});

// DELETE Property
app.delete('/api/v1/properties/:id', (req, res) => {
  const idNum = Number(req.params.id);
  const exists = dbState.properties.some(p => p.id === idNum);
  if (!exists) {
    return res.status(404).json({
      success: false,
      error: { code: "NOT_FOUND", message: "Property not found" }
    });
  }

  dbState.properties = dbState.properties.filter(p => p.id !== idNum);
  dbState.project_properties = dbState.project_properties.filter(pp => pp.property_id !== idNum);
  dbState.property_images = dbState.property_images.filter(img => img.property_id !== idNum);
  saveDb(dbState);

  res.json({ success: true });
});


// --- PROPERTY IMAGES ---
// GET Property Images
app.get('/api/v1/properties/:id/images', (req, res) => {
  const propId = Number(req.params.id);
  const images = dbState.property_images.filter(img => img.property_id === propId && img.is_deleted === 0);
  res.json({
    count: images.length,
    items: images
  });
});

// POST Upload / Link Property Image
app.post('/api/v1/properties/:id/images', (req, res) => {
  const propId = Number(req.params.id);
  const { image_type, image_url, notes, file_name, file_size } = req.body;

  if (!image_url) {
    return res.status(400).json({
      success: false,
      error: { code: "VALIDATION_ERROR", message: "image_url is required" }
    });
  }

  const timestamp = new Date().toISOString().replace('T', ' ').slice(0, 19);
  const newImageId = dbState.property_images.length > 0 ? Math.max(...dbState.property_images.map(img => img.id)) + 1 : 1;

  const newImage: CrePropertyImage = {
    id: newImageId,
    property_id: propId,
    image_type: image_type || "uploaded",
    image_url,
    provider: image_type === "street_view" ? "Google Street View" : "User Upload",
    heading: 180.0,
    pitch: 0.0,
    fov: 90.0,
    cached_path: `/cached/upload_${newImageId}.jpg`,
    created_at: timestamp,
    original_file_name: file_name || `upload_${newImageId}.jpg`,
    file_size: Number(file_size) || 154000,
    file_type: "image/jpeg",
    notes: notes || "Context image uploaded successfully to parcel workspace.",
    status: "active",
    is_deleted: 0
  };

  dbState.property_images.push(newImage);
  saveDb(dbState);

  res.status(201).json(newImage);
});

// DELETE Property Image (soft delete)
app.delete('/api/v1/property-images/:id', (req, res) => {
  const imgId = Number(req.params.id);
  const imgIndex = dbState.property_images.findIndex(img => img.id === imgId);
  if (imgIndex === -1) {
    return res.status(404).json({
      success: false,
      error: { code: "NOT_FOUND", message: "Property image not found" }
    });
  }

  dbState.property_images[imgIndex].is_deleted = 1;
  saveDb(dbState);
  res.json({ success: true });
});


// --- SCAN JOBS ---
// GET Scan Jobs
app.get('/api/v1/scans', (req, res) => {
  res.json({
    count: dbState.scans.length,
    items: dbState.scans
  });
});

// PUT Trigger Scan Job Execution (Simulate scan completion)
app.put('/api/v1/scans/:id/execute', (req, res) => {
  const scanId = Number(req.params.id);
  const scanIndex = dbState.scans.findIndex(s => s.id === scanId);
  if (scanIndex === -1) {
    return res.status(404).json({
      success: false,
      error: { code: "NOT_FOUND", message: "Scan record not found" }
    });
  }

  const timestamp = new Date().toISOString().replace('T', ' ').slice(0, 19);

  // Update scan and corresponding scan_job status
  dbState.scans[scanIndex].status = "complete";
  dbState.scans[scanIndex].updated_at = timestamp;

  const jobIndex = dbState.scan_jobs.findIndex(j => j.scan_id === dbState.scans[scanIndex].scan_uid);
  if (jobIndex !== -1) {
    dbState.scan_jobs[jobIndex].status = "completed";
    dbState.scan_jobs[jobIndex].found_count = 2; // Simulated found property count
    dbState.scan_jobs[jobIndex].updated_at = timestamp;
  }

  // Also seed some api usage logs for realism
  dbState.api_usage_logs.push({
    id: dbState.api_usage_logs.length + 1,
    provider: "Google Maps",
    api_name: "Street View static API",
    endpoint: "/maps/api/streetview",
    request_count: 10,
    estimated_cost: 0.07,
    created_at: timestamp
  });

  saveDb(dbState);

  res.json({
    success: true,
    message: "LIDAR Scanner sync simulation completed successfully.",
    data: dbState.scans[scanIndex]
  });
});


// --- WORKFLOW EXECUTIONS (DEV-TOOLS INTERFACE) ---
// GET Workflows
app.get('/api/v1/workflows', (req, res) => {
  const { property_id } = req.query;
  let items = dbState.workflow_executions;

  if (property_id) {
    items = items.filter(e => e.property_id === Number(property_id));
  }

  res.json({
    count: items.length,
    items: items
  });
});

// GET Workflow single
app.get('/api/v1/workflows/:id', (req, res) => {
  const execId = Number(req.params.id);
  const execution = dbState.workflow_executions.find(e => e.execution_id === execId);
  if (!execution) {
    return res.status(404).json({
      success: false,
      error: { code: "NOT_FOUND", message: "Workflow execution not found" }
    });
  }

  // Join events and results
  const events = dbState.workflow_events.filter(ev => ev.execution_id === execId);
  const result = dbState.workflow_results.find(r => r.execution_id === execId);

  res.json({
    ...execution,
    events,
    result
  });
});

// POST Dispatch Workflow to DEV-TOOLS
app.post('/api/v1/workflows', (req, res) => {
  const { project_id, property_id, workflow_code, priority } = req.body;
  if (!property_id || !workflow_code) {
    return res.status(400).json({
      success: false,
      error: { code: "VALIDATION_ERROR", message: "property_id and workflow_code are required" }
    });
  }

  const timestamp = new Date().toISOString().replace('T', ' ').slice(0, 19);
  const newExecId = dbState.workflow_executions.length > 0 ? Math.max(...dbState.workflow_executions.map(e => e.execution_id)) + 1 : 1;
  const execution_number = `WF-EX-${String(newExecId).padStart(4, '0')}`;

  const newExecution: CreWorkflowExecution = {
    execution_id: newExecId,
    execution_number,
    project_id: Number(project_id) || 1,
    property_id: Number(property_id),
    scenario_id: undefined,
    workflow_code,
    workflow_version: "1.2.0",
    devtools_execution_id: `DEV-RUN-${Math.floor(10000 + Math.random() * 90000)}`,
    status: "Running",
    priority: priority || "Normal",
    requested_by: 1,
    submitted_at: timestamp,
    started_at: timestamp,
    retry_count: 0,
    created_at: timestamp,
    updated_at: timestamp
  };

  dbState.workflow_executions.push(newExecution);

  // Push immediate kickoff event
  dbState.workflow_events.push({
    event_id: dbState.workflow_events.length > 0 ? Math.max(...dbState.workflow_events.map(ev => ev.event_id)) + 1 : 1,
    execution_id: newExecId,
    event_type: "Trigger",
    status: "Success",
    message: `Initialized AI workflow ${workflow_code}. Dispatched payload to separate DEV-TOOLS orchestrator.`,
    created_at: timestamp
  });

  // Increment some API usage logs to represent DEV-TOOLS handshake
  dbState.api_usage_logs.push({
    id: dbState.api_usage_logs.length + 1,
    provider: "DEV-TOOLS WIMLOGIC",
    api_name: "Agent Orchestration API",
    endpoint: "/devtools/v1/agent-workflows",
    request_count: 1,
    estimated_cost: 2.00,
    created_at: timestamp
  });

  // Simulated Async execution delay: After 4 seconds, mark complete & generate report & scenarios!
  setTimeout(() => {
    try {
      const completionTime = new Date().toISOString().replace('T', ' ').slice(0, 19);
      const db = loadDb();
      const currentExec = db.workflow_executions.find(e => e.execution_id === newExecId);

      if (currentExec && currentExec.status === "Running") {
        currentExec.status = "Completed";
        currentExec.completed_at = completionTime;
        currentExec.updated_at = completionTime;

        // Add progress events
        const startEventId = db.workflow_events.length > 0 ? Math.max(...db.workflow_events.map(ev => ev.event_id)) + 1 : 1;
        db.workflow_events.push(
          {
            event_id: startEventId,
            execution_id: newExecId,
            event_type: "Agent Handshake",
            status: "Success",
            message: "Property data analysis agent matched zoning code guidelines with county indexes.",
            created_at: completionTime
          },
          {
            event_id: startEventId + 1,
            execution_id: newExecId,
            event_type: "Completion",
            status: "Success",
            message: "Successfully generated pro-forma projections and adaptive-reuse metrics.",
            created_at: completionTime
          }
        );

        // Generate Workflow result section
        const newResultId = db.workflow_results.length > 0 ? Math.max(...db.workflow_results.map(r => r.result_id)) + 1 : 1;
        const targetProp = db.properties.find(p => p.id === Number(property_id));

        const irr = `${(18 + Math.random() * 6).toFixed(1)}%`;
        const costLow = (targetProp?.lot_sqft || 10000) * 450;
        const costHigh = (targetProp?.lot_sqft || 10000) * 620;

        db.workflow_results.push({
          result_id: newResultId,
          execution_id: newExecId,
          result_type: "COMPREHENSIVE_ANALYSIS",
          result_version: "1.2.0",
          response_json: JSON.stringify({
            score: Math.round(75 + Math.random() * 20),
            zoning: `${targetProp?.zoning_code || "LA-C5"} allows Mixed-Use adaptive reuse. Multi-family overlay active.`,
            financial: { low: costLow, high: costHigh, irr },
            recommendation: "Repurpose framing for high-end creative commercial. Highly robust IRR opportunity."
          }),
          normalized: 1,
          received_at: completionTime,
          created_at: completionTime
        });

        // Generate Analysis Report
        const newReportId = db.property_analysis_reports.length > 0 ? Math.max(...db.property_analysis_reports.map(r => r.id)) + 1 : 1;
        db.property_analysis_reports.push({
          id: newReportId,
          project_id: currentExec.project_id === 1 ? "PRJ-9021-LA" : "PRJ-8012-NY",
          property_id: currentExec.property_id,
          scenario_id: undefined,
          estimate_low: costLow,
          estimate_high: costHigh,
          zoning_notes: `${targetProp?.zoning_code || "LA-C5"} High-density mixed occupancy permitted.`,
          risk_notes: "Requires environmental soil check due to previous historic usage notes.",
          recommendation: `Proceed with conceptual design using ${irr} IRR pro-forma parameters.`,
          score: Math.round(80 + Math.random() * 18),
          report_json: JSON.stringify({
            zoning_score: 90,
            financial_irr: irr,
            cash_on_cash: "7.8%",
            environmental_risk: "Low"
          }),
          created_at: completionTime,
          updated_at: completionTime,
          workflow_execution_id: newExecId,
          workflow_result_id: newResultId,
          analysis_version: "1.2.0",
          confidence_score: 95.0,
          workflow_status: "Completed",
          completed_at: completionTime
        });

        // Add realistic generated assets
        const newAssetId = db.generated_assets.length > 0 ? Math.max(...db.generated_assets.map(a => a.asset_id)) + 1 : 1;
        db.generated_assets.push({
          asset_id: newAssetId,
          execution_id: newExecId,
          property_id: currentExec.property_id,
          asset_type: "pdf",
          asset_category: "Feasibility Report",
          title: `Feasibility Study for ${targetProp?.display_address || "Parcel " + property_id}`,
          description: `Comprehensive feasibility pro-forma report detailing adaptive-reuse IRR scenarios (${irr}) and zoning variances.`,
          file_name: `feasibility_study_${property_id}.pdf`,
          storage_path: `/assets/documents/feasibility_${property_id}.pdf`,
          thumbnail_path: "https://images.unsplash.com/photo-1586075010923-2dd45e9b2d4f?auto=format&fit=crop&w=150&q=80",
          mime_type: "application/pdf",
          file_size: 4200000 + Math.floor(Math.random() * 500000),
          version: "1.2.0",
          created_at: completionTime
        });

        // Link report scenario
        const newScenarioId = db.renovation_scenarios.length > 0 ? Math.max(...db.renovation_scenarios.map(s => s.id)) + 1 : 1;
        db.renovation_scenarios.push({
          id: newScenarioId,
          project_id: currentExec.project_id === 1 ? "PRJ-9021-LA" : "PRJ-8012-NY",
          property_id: currentExec.property_id,
          renovation_type: "Adaptive Commercial Creative Studios",
          scenario_type: "commercial_mixed_use",
          scenario_name: "Creative Studio Hub Adaptive Conversion",
          rationale: `Repurpose warehouse bay. High-efficiency glass facade. IRR target ${irr}.`,
          risk_level: "low",
          estimated_complexity: "medium",
          custom_notes: "Subject to structural engineer facade reviews.",
          status: "approved",
          source: "DEV-TOOLS WIMLOGIC Agent Suite",
          created_at: completionTime,
          updated_at: completionTime
        });

        saveDb(db);
        console.log(`Async workflow complete. Added results for execution ${newExecId}`);
      }
    } catch (e) {
      console.error("Async workflow evaluation failed:", e);
    }
  }, 4000);

  saveDb(dbState);
  res.status(201).json(newExecution);
});


// --- RENOVATION SCENARIOS ---
// GET Scenarios
app.get('/api/v1/scenarios', (req, res) => {
  const { property_id } = req.query;
  let items = dbState.renovation_scenarios;

  if (property_id) {
    items = items.filter(s => s.property_id === Number(property_id));
  }

  res.json({
    count: items.length,
    items: items
  });
});

// POST Create Scenario
app.post('/api/v1/scenarios', (req, res) => {
  const { project_id, property_id, renovation_type, rationale, risk_level, estimated_complexity, custom_notes } = req.body;
  if (!property_id || !renovation_type) {
    return res.status(400).json({
      success: false,
      error: { code: "VALIDATION_ERROR", message: "property_id and renovation_type are required" }
    });
  }

  const timestamp = new Date().toISOString().replace('T', ' ').slice(0, 19);
  const newId = dbState.renovation_scenarios.length > 0 ? Math.max(...dbState.renovation_scenarios.map(s => s.id)) + 1 : 1;

  const newScenario: CreRenovationScenario = {
    id: newId,
    project_id: project_id || "PRJ-9021-LA",
    property_id: Number(property_id),
    renovation_type,
    scenario_type: "custom",
    scenario_name: renovation_type,
    rationale: rationale || "Manually drafted redevelopment corridor.",
    risk_level: risk_level || "medium",
    estimated_complexity: estimated_complexity || "medium",
    custom_notes: custom_notes || "",
    status: "draft",
    source: "Manual Business Input",
    created_at: timestamp,
    updated_at: timestamp
  };

  dbState.renovation_scenarios.push(newScenario);
  saveDb(dbState);

  res.status(201).json(newScenario);
});

// PUT Approve/Reject Scenario
app.put('/api/v1/scenarios/:id', (req, res) => {
  const idNum = Number(req.params.id);
  const { status } = req.body;

  const index = dbState.renovation_scenarios.findIndex(s => s.id === idNum);
  if (index === -1) {
    return res.status(404).json({
      success: false,
      error: { code: "NOT_FOUND", message: "Scenario not found" }
    });
  }

  dbState.renovation_scenarios[index].status = status || "draft";
  dbState.renovation_scenarios[index].updated_at = new Date().toISOString().replace('T', ' ').slice(0, 19);

  saveDb(dbState);
  res.json(dbState.renovation_scenarios[index]);
});


// --- PROPERTY ANALYSIS REPORTS ---
// GET Reports
app.get('/api/v1/reports', (req, res) => {
  const { property_id } = req.query;
  let items = dbState.property_analysis_reports;

  if (property_id) {
    items = items.filter(r => r.property_id === Number(property_id));
  }

  res.json({
    count: items.length,
    items: items
  });
});

// GET Single Report
app.get('/api/v1/reports/:id', (req, res) => {
  const report = dbState.property_analysis_reports.find(r => r.id === Number(req.params.id));
  if (!report) {
    return res.status(404).json({
      success: false,
      error: { code: "NOT_FOUND", message: "Analysis report not found" }
    });
  }
  res.json(report);
});


// --- CONCEPT DESIGNS ---
// GET Concept Designs
app.get('/api/v1/concept-designs', (req, res) => {
  const { property_id } = req.query;
  let items = dbState.concept_designs;

  if (property_id) {
    items = items.filter(c => c.property_id === Number(property_id));
  }

  res.json({
    count: items.length,
    items: items
  });
});

// POST Create Concept Design
app.post('/api/v1/concept-designs', (req, res) => {
  const { project_id, property_id, title, concept_prompt, concept_notes } = req.body;
  if (!property_id || !concept_prompt) {
    return res.status(400).json({
      success: false,
      error: { code: "VALIDATION_ERROR", message: "property_id and concept_prompt are required" }
    });
  }

  const timestamp = new Date().toISOString().replace('T', ' ').slice(0, 19);
  const newId = dbState.concept_designs.length > 0 ? Math.max(...dbState.concept_designs.map(c => c.id)) + 1 : 1;

  const newDesign: CreConceptDesign = {
    id: newId,
    project_id: project_id || "PRJ-9021-LA",
    property_id: Number(property_id),
    title: title || "New Creative Elevation Design",
    concept_prompt,
    concept_notes: concept_notes || "",
    image_reference_ids: JSON.stringify([]),
    status: "draft",
    created_at: timestamp,
    updated_at: timestamp,
    design_version: "V1.0"
  };

  dbState.concept_designs.push(newDesign);
  saveDb(dbState);

  res.status(201).json(newDesign);
});

// PUT Approve Concept Design
app.put('/api/v1/concept-designs/:id', (req, res) => {
  const idNum = Number(req.params.id);
  const { status } = req.body;

  const index = dbState.concept_designs.findIndex(c => c.id === idNum);
  if (index === -1) {
    return res.status(404).json({
      success: false,
      error: { code: "NOT_FOUND", message: "Concept design not found" }
    });
  }

  const timestamp = new Date().toISOString().replace('T', ' ').slice(0, 19);
  dbState.concept_designs[index].status = status || "draft";
  if (status === "approved") {
    dbState.concept_designs[index].approved_by = 1;
    dbState.concept_designs[index].approved_at = timestamp;
  }
  dbState.concept_designs[index].updated_at = timestamp;

  saveDb(dbState);
  res.json(dbState.concept_designs[index]);
});


// --- GENERATED ASSETS ---
// GET Generated Assets
app.get('/api/v1/generated-assets', (req, res) => {
  const { property_id } = req.query;
  let items = dbState.generated_assets;

  if (property_id) {
    items = items.filter(a => a.property_id === Number(property_id));
  }

  res.json({
    count: items.length,
    items: items
  });
});


// --- API USAGE LOGS ---
// GET API Logs
app.get('/api/v1/api-logs', (req, res) => {
  res.json({
    count: dbState.api_usage_logs.length,
    items: dbState.api_usage_logs
  });
});


// Serve static compiled assets in production
if (process.env.NODE_ENV === "production") {
  const distPath = path.join(process.cwd(), 'dist');
  app.use(express.static(distPath));
  app.get('*', (req, res) => {
    res.sendFile(path.join(distPath, 'index.html'));
  });
} else {
  // Vite middleware for development HMR
  const startDevVite = async () => {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa"
    });
    app.use(vite.middlewares);
  };
  startDevVite();
}

app.listen(PORT, "0.0.0.0", () => {
  console.log(`AI-CRE WIMLOGIC V1.0 fullstack server is booting on http://0.0.0.0:${PORT}`);
});
