from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator

class DesignToolImageRequirementBase(BaseModel):
    tool_id: int
    input_role: str  # primary, supporting, reference
    # Ordered JSON collection of allowed Property Image roles for this
    # requirement, e.g. ["primary", "exterior", "street_view", "drone"] -
    # not a key/value object.
    allowed_image_roles_json: Optional[List[str]] = None
    min_count: int = 0
    max_count: Optional[int] = None
    display_order: int = 0

    @field_validator("min_count")
    @classmethod
    def _min_count_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("min_count must be >= 0")
        return v

    @field_validator("max_count")
    @classmethod
    def _max_count_non_negative(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("max_count must be >= 0")
        return v

class DesignToolImageRequirementCreate(DesignToolImageRequirementBase):
    pass

class DesignToolImageRequirementUpdate(BaseModel):
    tool_id: Optional[int] = None
    input_role: Optional[str] = None
    allowed_image_roles_json: Optional[List[str]] = None
    min_count: Optional[int] = None
    max_count: Optional[int] = None
    display_order: Optional[int] = None

    @field_validator("min_count")
    @classmethod
    def _min_count_non_negative(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("min_count must be >= 0")
        return v

    @field_validator("max_count")
    @classmethod
    def _max_count_non_negative(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("max_count must be >= 0")
        return v

class DesignToolImageRequirementRead(DesignToolImageRequirementBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
