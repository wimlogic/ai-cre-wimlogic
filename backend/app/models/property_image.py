from sqlalchemy import Column, Integer, BigInteger, String, Text, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class PropertyImage(Base):
    __tablename__ = "cre_property_images"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    property_id = Column(BigInteger, ForeignKey("cre_properties.id", ondelete="CASCADE"), nullable=False)
    image_type = Column(String(50), nullable=False)  # street_view, satellite, parcel_map, uploaded
    image_url = Column(Text, nullable=True)
    provider = Column(String(50), nullable=True)
    heading = Column(Numeric(8, 3), nullable=True)
    pitch = Column(Numeric(8, 3), nullable=True)
    fov = Column(Numeric(8, 3), nullable=True)
    cached_path = Column(Text, nullable=True)
    last_checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    project_id = Column(String(100), nullable=True)
    original_file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String(100), nullable=True)
    image_role = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(50), nullable=True)
    is_deleted = Column(Integer, default=0, nullable=False)  # tinyint(1) DEFAULT '0'

    # Relationships
    property = relationship("Property", back_populates="images")

