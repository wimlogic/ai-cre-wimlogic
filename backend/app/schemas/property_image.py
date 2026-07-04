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
    status: Optional[str] = None
    is_deleted: int = 0

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
    status: Optional[str] = None
    is_deleted: Optional[int] = None

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
