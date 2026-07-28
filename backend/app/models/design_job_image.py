from sqlalchemy import Column, BigInteger, String, JSON, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class DesignJobImage(Base):
    __tablename__ = "cre_design_job_images"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    design_job_id = Column(BigInteger, ForeignKey("cre_design_jobs.id", ondelete="CASCADE"), nullable=False)
    # AIHOME Design Studio V2 - Image Workspace Evolution. A row
    # references EXACTLY ONE of the two sources below (enforced in
    # design_job_service.set_images(), not by a DB CHECK constraint -
    # matches this project's existing validation-lives-in-the-service-
    # layer convention, and mirrors how cre_design_image_lineage already
    # distinguishes its own two source types). Every AI-generated image
    # is a permanent Design Asset AIHOME owns - selecting one here as a
    # reference for a NEW Design Job is no different, architecturally,
    # from selecting an original photo; DEV-TOOLS never needs to know
    # which kind of asset it was handed.
    property_image_id = Column(BigInteger, ForeignKey("cre_property_images.id"), nullable=True)
    source_image_version_id = Column(BigInteger, ForeignKey("cre_design_image_versions.id"), nullable=True)
    input_role = Column(String(30), default="primary", nullable=False)  # primary, supporting, reference
    image_knowledge_snapshot_json = Column(JSON, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    design_job = relationship("DesignJob", back_populates="images")
    # DB FK on property_image_id has no ON DELETE clause (RESTRICT) - no
    # destructive ORM cascade against PropertyImage.
    property_image = relationship("PropertyImage", back_populates="design_job_images")
    # DB FK on source_image_version_id also has no ON DELETE clause
    # (RESTRICT) - a DesignImageVersion used as a reference input can
    # never be silently removed out from under the Design Job that used it.
    source_image_version = relationship("DesignImageVersion", foreign_keys=[source_image_version_id])
