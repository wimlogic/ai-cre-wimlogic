from sqlalchemy import Column, Integer, BigInteger, String, Text, Numeric, DateTime, JSON, ForeignKey, func
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
    ai_prompt = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    constraints = Column(Text, nullable=True)
    priority = Column(Integer, nullable=True)
    is_primary = Column(Integer, default=0, nullable=False)  # tinyint(1) DEFAULT '0'
    status = Column(String(50), nullable=True)
    is_deleted = Column(Integer, default=0, nullable=False)  # tinyint(1) DEFAULT '0'
    # Knowledge Inheritance Engine Phase 1.2A - additive, nullable, same
    # registry-gated inclusion rule as Project/Property's new fields.
    camera_direction = Column(String(50), nullable=True)
    existing_furniture = Column(JSON, nullable=True)
    existing_lighting = Column(Text, nullable=True)

    # Relationships
    property = relationship("Property", back_populates="images")

    # Design Studio (V1.1C/D) - DB FKs from these tables' property_image_id
    # back to cre_property_images.id have no ON DELETE clause (RESTRICT),
    # so no destructive ORM cascade is declared on either relationship below.
    design_job_images = relationship("DesignJobImage", back_populates="property_image")
    lineage_as_source = relationship(
        "DesignImageLineage",
        back_populates="source_property_image",
        foreign_keys="DesignImageLineage.source_property_image_id",
    )

