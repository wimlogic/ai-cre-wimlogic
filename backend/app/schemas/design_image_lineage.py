from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class DesignImageLineageRead(BaseModel):
    """
    Read-only through the public API - lineage rows are written only by
    workflow result ingestion (Design Image Version persistence), never
    created or updated directly via the API.
    """
    id: int
    image_version_id: int
    source_type: str  # property_image, image_version
    source_property_image_id: Optional[int] = None
    source_image_version_id: Optional[int] = None
    lineage_role: str  # primary, supporting, reference, parent
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
