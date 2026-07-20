from datetime import datetime
from typing import Optional, List, Any
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class ProjectBase(BaseModel):
    project_id: str
    project_name: str
    description: Optional[str] = None
    status: str = "active"
    default_city: Optional[str] = None
    default_state: Optional[str] = None
    main_street: Optional[str] = None
    beginning_address: Optional[str] = None
    ending_address: Optional[str] = None
    side: Optional[str] = None
    scan_mode: Optional[str] = None
    # Knowledge Inheritance Engine Phase 1.2A
    goals: Optional[str] = None
    hoa_rules: Optional[str] = None
    climate: Optional[str] = None
    budget_low: Optional[Decimal] = None
    budget_high: Optional[Decimal] = None
    preferred_styles: Optional[List[str]] = None
    design_preferences: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    default_city: Optional[str] = None
    default_state: Optional[str] = None
    main_street: Optional[str] = None
    beginning_address: Optional[str] = None
    ending_address: Optional[str] = None
    side: Optional[str] = None
    scan_mode: Optional[str] = None
    goals: Optional[str] = None
    hoa_rules: Optional[str] = None
    climate: Optional[str] = None
    budget_low: Optional[Decimal] = None
    budget_high: Optional[Decimal] = None
    preferred_styles: Optional[List[str]] = None
    design_preferences: Optional[str] = None

class ProjectRead(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProjectResponse(ProjectRead):
    pass

class ProjectListResponse(BaseModel):
    count: int
    items: List[ProjectRead]

    model_config = ConfigDict(from_attributes=True)
