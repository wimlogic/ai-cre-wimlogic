from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class DesignImageVersionRead(BaseModel):
    """
    Design Image Versions are created by workflow result ingestion, not by
    a public Create endpoint - no Create schema exists here by design.
    No parent_version_id, no original_image_id - ancestry is owned
    exclusively by cre_design_image_lineage / DesignImageLineageRead.
    """
    id: int
    version_uid: str
    design_job_id: int
    property_id: int
    workflow_execution_id: int
    version_number: int
    file_name: str
    storage_path: str
    thumbnail_path: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    generated_asset_id: Optional[int] = None
    status: str  # generated, rejected, approved, superseded
    generated_at: datetime
    generated_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DesignImageVersionResponse(DesignImageVersionRead):
    pass

class DesignImageVersionListResponse(BaseModel):
    count: int
    items: List[DesignImageVersionRead]

    model_config = ConfigDict(from_attributes=True)
