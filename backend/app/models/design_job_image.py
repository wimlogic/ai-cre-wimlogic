from sqlalchemy import Column, BigInteger, String, JSON, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class DesignJobImage(Base):
    __tablename__ = "cre_design_job_images"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    design_job_id = Column(BigInteger, ForeignKey("cre_design_jobs.id", ondelete="CASCADE"), nullable=False)
    property_image_id = Column(BigInteger, ForeignKey("cre_property_images.id"), nullable=False)
    input_role = Column(String(30), default="primary", nullable=False)  # primary, supporting, reference
    image_knowledge_snapshot_json = Column(JSON, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    design_job = relationship("DesignJob", back_populates="images")
    # DB FK on property_image_id has no ON DELETE clause (RESTRICT) - no
    # destructive ORM cascade against PropertyImage.
    property_image = relationship("PropertyImage", back_populates="design_job_images")
