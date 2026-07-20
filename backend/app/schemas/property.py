from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class PropertyBase(BaseModel):
    property_uid: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    apn: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    lot_sqft: Optional[int] = None
    building_sqft: Optional[int] = None
    year_built: Optional[int] = None
    zoning_code: Optional[str] = None
    existing_use: Optional[str] = None
    business_name: Optional[str] = None
    land_value: Optional[float] = None
    improvement_value: Optional[float] = None
    total_assessed_value: Optional[float] = None
    data_source: Optional[str] = None
    street_number: Optional[str] = None
    street_name: Optional[str] = None
    side_of_street: Optional[str] = None
    phase2_source: Optional[str] = None
    display_address: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    confidence_score: Optional[str] = None
    raw_api_json: Optional[str] = None
    api_source_url: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    construction_type: Optional[str] = None
    existing_materials: Optional[List[str]] = None
    existing_colors: Optional[List[str]] = None

class PropertyCreate(PropertyBase):
    pass

class PropertyUpdate(BaseModel):
    property_uid: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    apn: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    lot_sqft: Optional[int] = None
    building_sqft: Optional[int] = None
    year_built: Optional[int] = None
    zoning_code: Optional[str] = None
    existing_use: Optional[str] = None
    business_name: Optional[str] = None
    land_value: Optional[float] = None
    improvement_value: Optional[float] = None
    total_assessed_value: Optional[float] = None
    data_source: Optional[str] = None
    street_number: Optional[str] = None
    street_name: Optional[str] = None
    side_of_street: Optional[str] = None
    phase2_source: Optional[str] = None
    display_address: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    confidence_score: Optional[str] = None
    raw_api_json: Optional[str] = None
    api_source_url: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    construction_type: Optional[str] = None
    existing_materials: Optional[List[str]] = None
    existing_colors: Optional[List[str]] = None

class PropertyRead(PropertyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PropertyResponse(PropertyRead):
    pass

class PropertyListResponse(BaseModel):
    count: int
    items: List[PropertyRead]

    model_config = ConfigDict(from_attributes=True)
