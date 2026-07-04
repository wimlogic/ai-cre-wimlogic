from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class ConceptDesignBase(BaseModel):
    project_id: str
    property_id: int
    scenario_id: Optional[int] = None
    title: Optional[str] = None
    concept_prompt: str
    concept_notes: Optional[str] = None
    image_reference_ids: Optional[List[str]] = None
    status: str = "draft"
    workflow_execution_id: Optional[int] = None
    design_version: Optional[str] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None

class ConceptDesignCreate(ConceptDesignBase):
    pass

class ConceptDesignUpdate(BaseModel):
    project_id: Optional[str] = None
    property_id: Optional[int] = None
    scenario_id: Optional[int] = None
    title: Optional[str] = None
    concept_prompt: Optional[str] = None
    concept_notes: Optional[str] = None
    image_reference_ids: Optional[List[str]] = None
    status: Optional[str] = None
    workflow_execution_id: Optional[int] = None
    design_version: Optional[str] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None

class ConceptDesignRead(ConceptDesignBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ConceptDesignResponse(ConceptDesignRead):
    pass

class ConceptDesignListResponse(BaseModel):
    count: int
    items: List[ConceptDesignRead]

    model_config = ConfigDict(from_attributes=True)
