from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class RenovationScenarioBase(BaseModel):
    project_id: str
    property_id: int
    renovation_type: str
    scenario_type: Optional[str] = None
    scenario_name: Optional[str] = None
    rationale: Optional[str] = None
    risk_level: Optional[str] = None
    estimated_complexity: Optional[str] = None
    custom_notes: Optional[str] = None
    status: str = "draft"
    source: Optional[str] = None

class RenovationScenarioCreate(RenovationScenarioBase):
    pass

class RenovationScenarioUpdate(BaseModel):
    project_id: Optional[str] = None
    property_id: Optional[int] = None
    renovation_type: Optional[str] = None
    scenario_type: Optional[str] = None
    scenario_name: Optional[str] = None
    rationale: Optional[str] = None
    risk_level: Optional[str] = None
    estimated_complexity: Optional[str] = None
    custom_notes: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None

class RenovationScenarioRead(RenovationScenarioBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RenovationScenarioResponse(RenovationScenarioRead):
    pass

class RenovationScenarioListResponse(BaseModel):
    count: int
    items: List[RenovationScenarioRead]

    model_config = ConfigDict(from_attributes=True)
