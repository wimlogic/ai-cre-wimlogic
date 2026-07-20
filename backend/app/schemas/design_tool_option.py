from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict

class DesignToolOptionBase(BaseModel):
    tool_id: int
    option_code: str
    option_label: str
    # Business values currently include: select, multiselect, boolean,
    # number, text, slider. Kept as str rather than a Python Enum so new
    # option types can be introduced without a code change - matches the
    # existing codebase's convention of not enum-typing business status/type
    # strings (see status fields across all other schema modules).
    option_type: str
    # Ordered JSON collection of allowed values for select/multiselect
    # options, e.g. ["Modern", "Contemporary", "Minimalist"] - not a
    # key/value object.
    allowed_values_json: Optional[List[Any]] = None
    default_value: Optional[str] = None
    is_required: int = 0
    display_order: int = 0
    status: str = "active"

class DesignToolOptionCreate(DesignToolOptionBase):
    pass

class DesignToolOptionUpdate(BaseModel):
    tool_id: Optional[int] = None
    option_code: Optional[str] = None
    option_label: Optional[str] = None
    option_type: Optional[str] = None
    allowed_values_json: Optional[List[Any]] = None
    default_value: Optional[str] = None
    is_required: Optional[int] = None
    display_order: Optional[int] = None
    status: Optional[str] = None

class DesignToolOptionRead(DesignToolOptionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
