from fastapi import APIRouter

from app.api.api_usage_log import router as api_usage_log_router
from app.api.concept_design import router as concept_design_router
from app.api.estimate import router as estimate_router
from app.api.generated_asset import router as generated_asset_router
from app.api.project_property import router as project_property_router
from app.api.project import router as project_router
from app.api.property import router as property_router
from app.api.property_analysis_report import router as property_analysis_report_router
from app.api.property_image import router as property_image_router
from app.api.renovation_scenario import router as renovation_scenario_router
from app.api.result_section import router as result_section_router
from app.api.scan_job import router as scan_job_router
from app.api.scan_property import router as scan_property_router
from app.api.scan import router as scan_router
from app.api.workflow_event import router as workflow_event_router
from app.api.workflow_execution import router as workflow_execution_router
from app.api.workflow_result import router as workflow_result_router
from app.api.zoning_note import router as zoning_note_router
from app.api.ai_orchestration import router as ai_orchestration_router
from app.api.design_studio_tool import router as design_studio_tool_router
from app.api.design_studio_job import router as design_studio_job_router

api_router = APIRouter()

# Register all 18 entity routers + 1 custom orchestration router
api_router.include_router(api_usage_log_router, prefix="/api-usage-logs", tags=["API Usage Logs"])
api_router.include_router(concept_design_router, prefix="/concept-designs", tags=["Concept Designs"])
api_router.include_router(estimate_router, prefix="/estimates", tags=["Estimates"])
api_router.include_router(generated_asset_router, prefix="/generated-assets", tags=["Generated Assets"])
api_router.include_router(project_property_router, prefix="/project-properties", tags=["Project Properties"])
api_router.include_router(project_router, prefix="/projects", tags=["Projects"])
api_router.include_router(property_router, prefix="/properties", tags=["Properties"])
api_router.include_router(property_analysis_report_router, prefix="/property-analysis-reports", tags=["Property Analysis Reports"])
api_router.include_router(property_image_router, prefix="/property-images", tags=["Property Images"])
api_router.include_router(renovation_scenario_router, prefix="/renovation-scenarios", tags=["Renovation Scenarios"])
api_router.include_router(result_section_router, prefix="/result-sections", tags=["Result Sections"])
api_router.include_router(scan_job_router, prefix="/scan-jobs", tags=["Scan Jobs"])
api_router.include_router(scan_property_router, prefix="/scan-properties", tags=["Scan Properties"])
api_router.include_router(scan_router, prefix="/scans", tags=["Scans"])
api_router.include_router(workflow_event_router, prefix="/workflow-events", tags=["Workflow Events"])
api_router.include_router(workflow_execution_router, prefix="/workflow-executions", tags=["Workflow Executions"])
api_router.include_router(workflow_result_router, prefix="/workflow-results", tags=["Workflow Results"])
api_router.include_router(zoning_note_router, prefix="/zoning-notes", tags=["Zoning Notes"])
api_router.include_router(ai_orchestration_router, prefix="/ai-orchestration", tags=["AI Orchestration"])

# Design Studio (V1.1C/D) - approved namespace: /api/v1/design-studio/*
api_router.include_router(design_studio_tool_router, prefix="/design-studio/tools", tags=["Design Studio - Tools"])
api_router.include_router(design_studio_job_router, prefix="/design-studio/jobs", tags=["Design Studio - Jobs"])
