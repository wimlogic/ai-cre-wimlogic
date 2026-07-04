from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class GeneratedAssetBase(BaseModel):
    execution_id: int
    property_id: int
    asset_type: str
    asset_category: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    file_name: str
    storage_path: str
    thumbnail_path: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    version: Optional[str] = None

class GeneratedAssetCreate(GeneratedAssetBase):
    pass

class GeneratedAssetUpdate(BaseModel):
    execution_id: Optional[int] = None
    property_id: Optional[int] = None
    asset_type: Optional[str] = None
    asset_category: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    file_name: Optional[str] = None
    storage_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    version: Optional[str] = None

class GeneratedAssetRead(GeneratedAssetBase):
    asset_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class GeneratedAssetResponse(GeneratedAssetRead):
    pass

class GeneratedAssetListResponse(BaseModel):
    count: int
    items: List[GeneratedAssetRead]

    model_config = ConfigDict(from_attributes=True)
