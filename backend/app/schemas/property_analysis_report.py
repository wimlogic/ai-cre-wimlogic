from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class PropertyAnalysisReportBase(BaseModel):
    project_id: str
    property_id: int
    scenario_id: Optional[int] = None
    estimate_low: Optional[float] = None
    estimate_high: Optional[float] = None
    zoning_notes: Optional[str] = None
    risk_notes: Optional[str] = None
    recommendation: Optional[str] = None
    score: Optional[float] = None
    report_json: Optional[Dict[str, Any]] = None
    workflow_execution_id: Optional[int] = None
    workflow_result_id: Optional[int] = None
    analysis_version: Optional[str] = None
    confidence_score: Optional[float] = None
    workflow_status: Optional[str] = None
    completed_at: Optional[datetime] = None

class PropertyAnalysisReportCreate(PropertyAnalysisReportBase):
    pass

class PropertyAnalysisReportUpdate(BaseModel):
    project_id: Optional[str] = None
    property_id: Optional[int] = None
    scenario_id: Optional[int] = None
    estimate_low: Optional[float] = None
    estimate_high: Optional[float] = None
    zoning_notes: Optional[str] = None
    risk_notes: Optional[str] = None
    recommendation: Optional[str] = None
    score: Optional[float] = None
    report_json: Optional[Dict[str, Any]] = None
    workflow_execution_id: Optional[int] = None
    workflow_result_id: Optional[int] = None
    analysis_version: Optional[str] = None
    confidence_score: Optional[float] = None
    workflow_status: Optional[str] = None
    completed_at: Optional[datetime] = None

class PropertyAnalysisReportRead(PropertyAnalysisReportBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PropertyAnalysisReportResponse(PropertyAnalysisReportRead):
    pass

class PropertyAnalysisReportListResponse(BaseModel):
    count: int
    items: List[PropertyAnalysisReportRead]

    model_config = ConfigDict(from_attributes=True)
