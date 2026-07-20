from sqlalchemy import Column, BigInteger, String, JSON, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class DesignImageVersion(Base):
    __tablename__ = "cre_design_image_versions"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    version_uid = Column(String(120), unique=True, index=True, nullable=False)
    design_job_id = Column(BigInteger, ForeignKey("cre_design_jobs.id"), nullable=False)
    property_id = Column(BigInteger, ForeignKey("cre_properties.id"), nullable=False)
    workflow_execution_id = Column(BigInteger, ForeignKey("cre_workflow_executions.execution_id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    file_name = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=True)
    mime_type = Column(String(100), nullable=True)
    file_size = Column(BigInteger, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    # Optional future promotion reference only - approval never auto-populates
    # this. DB FK is ON DELETE SET NULL, so it must remain nullable here.
    generated_asset_id = Column(BigInteger, ForeignKey("cre_generated_assets.asset_id", ondelete="SET NULL"), nullable=True)
    status = Column(String(30), default="generated", nullable=False)  # generated, rejected, approved, superseded
    generated_at = Column(DateTime, nullable=False)
    generated_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    # DB FKs on design_job_id / property_id / workflow_execution_id all have
    # no ON DELETE clause (RESTRICT) - no destructive ORM cascade.
    design_job = relationship("DesignJob", back_populates="image_versions")
    property = relationship("Property", back_populates="design_image_versions")
    workflow_execution = relationship("WorkflowExecution")
    generated_asset = relationship("GeneratedAsset")

    # cre_design_image_lineage is the sole ancestry authority. This version
    # owns its own lineage rows (DB FK image_version_id is ON DELETE CASCADE).
    lineage_entries = relationship(
        "DesignImageLineage",
        back_populates="image_version",
        foreign_keys="DesignImageLineage.image_version_id",
        cascade="all, delete-orphan",
    )
    # Rows where THIS version is itself a source for another version (prior
    # version -> new version refinement chains). DB FK here is RESTRICT, so
    # no destructive ORM cascade.
    sourced_lineage_entries = relationship(
        "DesignImageLineage",
        back_populates="source_image_version",
        foreign_keys="DesignImageLineage.source_image_version_id",
    )
