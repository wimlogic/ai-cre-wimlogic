from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict

class DesignJobImageCreate(BaseModel):
    design_job_id: int
    # AIHOME Design Studio V2 - exactly one of these two is populated per
    # row, never both, never neither (validated in
    # design_job_service.set_images(), not here - this schema only
    # shapes the request).
    property_image_id: Optional[int] = None
    source_image_version_id: Optional[int] = None
    input_role: str = "primary"  # primary, supporting, reference
    image_knowledge_snapshot_json: Optional[Dict[str, Any]] = None
    display_order: int = 0

class DesignJobImageRead(DesignJobImageCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
