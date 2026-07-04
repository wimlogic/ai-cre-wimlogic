from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class EstimateBase(BaseModel):
    property_id: int
    scenario: str
    proposed_use: Optional[str] = None
    proposed_building_sqft: Optional[int] = None
    proposed_units: Optional[int] = None
    low_cost: Optional[float] = None
    mid_cost: Optional[float] = None
    high_cost: Optional[float] = None
    cost_per_sqft_low: Optional[float] = None
    cost_per_sqft_high: Optional[float] = None
    assumptions: Optional[str] = None
    risk_level: str = "medium"
    workflow_execution_id: Optional[int] = None
    estimate_source: Optional[str] = None
    estimate_version: Optional[str] = None

class EstimateCreate(EstimateBase):
    pass

class EstimateUpdate(BaseModel):
    property_id: Optional[int] = None
    scenario: Optional[str] = None
    proposed_use: Optional[str] = None
    proposed_building_sqft: Optional[int] = None
    proposed_units: Optional[int] = None
    low_cost: Optional[float] = None
    mid_cost: Optional[float] = None
    high_cost: Optional[float] = None
    cost_per_sqft_low: Optional[float] = None
    cost_per_sqft_high: Optional[float] = None
    assumptions: Optional[str] = None
    risk_level: Optional[str] = None
    workflow_execution_id: Optional[int] = None
    estimate_source: Optional[str] = None
    estimate_version: Optional[str] = None

class EstimateRead(EstimateBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EstimateResponse(EstimateRead):
    pass

class EstimateListResponse(BaseModel):
    count: int
    items: List[EstimateRead]

    model_config = ConfigDict(from_attributes=True)
