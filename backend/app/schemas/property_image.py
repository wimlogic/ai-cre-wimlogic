from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class PropertyImageBase(BaseModel):
    property_id: int
    image_type: str
    image_url: Optional[str] = None
    provider: Optional[str] = None
    heading: Optional[float] = None
    pitch: Optional[float] = None
    fov: Optional[float] = None
    cached_path: Optional[str] = None
    last_checked_at: Optional[datetime] = None
    project_id: Optional[str] = None
    original_file_name: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    image_role: Optional[str] = None
    notes: Optional[str] = None
    ai_prompt: Optional[str] = None
    # Collection of Image Tags, e.g. ["front-facade", "retail", "signage",
    # "stucco"] - not a key/value object.
    tags: Optional[List[str]] = None
    constraints: Optional[str] = None
    priority: Optional[int] = None
    is_primary: int = 0
    status: Optional[str] = None
    is_deleted: int = 0
    camera_direction: Optional[str] = None
    existing_furniture: Optional[List[str]] = None
    existing_lighting: Optional[str] = None

class PropertyImageCreate(PropertyImageBase):
    pass

class PropertyImageUpdate(BaseModel):
    property_id: Optional[int] = None
    image_type: Optional[str] = None
    image_url: Optional[str] = None
    provider: Optional[str] = None
    heading: Optional[float] = None
    pitch: Optional[float] = None
    fov: Optional[float] = None
    cached_path: Optional[str] = None
    last_checked_at: Optional[datetime] = None
    project_id: Optional[str] = None
    original_file_name: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    image_role: Optional[str] = None
    notes: Optional[str] = None
    ai_prompt: Optional[str] = None
    tags: Optional[List[str]] = None
    constraints: Optional[str] = None
    priority: Optional[int] = None
    is_primary: Optional[int] = None
    status: Optional[str] = None
    is_deleted: Optional[int] = None
    camera_direction: Optional[str] = None
    existing_furniture: Optional[List[str]] = None
    existing_lighting: Optional[str] = None

class PropertyImageRead(PropertyImageBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PropertyImageResponse(PropertyImageRead):
    pass

class PropertyImageListResponse(BaseModel):
    count: int
    items: List[PropertyImageRead]

    model_config = ConfigDict(from_attributes=True)
