from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class DesignToolBase(BaseModel):
    tool_code: str
    tool_name: str
    design_type: str
    workflow_code: str
    card_image_path: Optional[str] = None
    icon_code: Optional[str] = None
    business_description: Optional[str] = None
    business_purpose: Optional[str] = None
    business_instructions: Optional[str] = None
    input_config_json: Optional[Dict[str, Any]] = None
    output_expectations_json: Optional[Dict[str, Any]] = None
    status: str = "active"
    display_order: int = 0

class DesignToolCreate(DesignToolBase):
    pass

class DesignToolUpdate(BaseModel):
    tool_code: Optional[str] = None
    tool_name: Optional[str] = None
    design_type: Optional[str] = None
    workflow_code: Optional[str] = None
    card_image_path: Optional[str] = None
    icon_code: Optional[str] = None
    business_description: Optional[str] = None
    business_purpose: Optional[str] = None
    business_instructions: Optional[str] = None
    input_config_json: Optional[Dict[str, Any]] = None
    output_expectations_json: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    display_order: Optional[int] = None

class DesignToolRead(DesignToolBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DesignToolResponse(DesignToolRead):
    pass

class DesignToolListResponse(BaseModel):
    count: int
    items: List[DesignToolRead]

    model_config = ConfigDict(from_attributes=True)
