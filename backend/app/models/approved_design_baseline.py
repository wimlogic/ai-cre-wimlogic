from sqlalchemy import Column, BigInteger, String, JSON, DateTime, ForeignKey, Computed, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class ApprovedDesignBaseline(Base):
    """
    Formal V1.1D -> V1.1G business handoff. Self-sufficient snapshot -
    never requires reconstructing historical mutable state.

    active_scope_key is a database-generated (STORED) column: it collapses
    to NULL for every non-'active' row and to a composite
    "property_id|design_type|design_scope" string only while status='active'.
    Combined with the UNIQUE constraint on that column, this makes it
    structurally impossible for two ACTIVE baselines to exist for the same
    property_id + design_type + design_scope, while placing no limit on how
    many superseded rows accumulate. This column is database-computed and
    must never be set directly from the ORM side.
    """
    __tablename__ = "cre_approved_design_baselines"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    baseline_uid = Column(String(120), unique=True, index=True, nullable=False)
    project_id = Column(String(100), nullable=False)  # business context only, not FK'd
    property_id = Column(BigInteger, ForeignKey("cre_properties.id"), nullable=False)
    design_job_id = Column(BigInteger, ForeignKey("cre_design_jobs.id"), nullable=False)
    image_version_id = Column(BigInteger, ForeignKey("cre_design_image_versions.id"), nullable=False, unique=True)
    tool_id = Column(BigInteger, ForeignKey("cre_design_tools.id"), nullable=False)
    tool_code = Column(String(50), nullable=False)
    design_type = Column(String(50), nullable=False)
    design_scope = Column(String(100), nullable=False)
    tool_options_json = Column(JSON, nullable=True)
    effective_context_json = Column(JSON, nullable=True)
    submitted_payload_json = Column(JSON, nullable=True)
    status = Column(String(30), default="active", nullable=False)  # active, superseded
    # Database GENERATED ALWAYS ... STORED column. Mapped via Computed so
    # SQLAlchemy treats this as a server-side generated value: it is never
    # included in INSERT/UPDATE statements, and MySQL remains the sole
    # authority for its value. Expression must stay semantically identical
    # to the actual DDL:
    #   CASE WHEN status = 'active'
    #        THEN CONCAT(property_id, '|', design_type, '|', design_scope)
    #        ELSE NULL
    #   END
    active_scope_key = Column(
        String(300),
        Computed(
            "CASE "
            "WHEN status = 'active' "
            "THEN CONCAT(property_id, '|', design_type, '|', design_scope) "
            "ELSE NULL "
            "END",
            persisted=True,
        ),
        nullable=True,
    )
    approved_by = Column(BigInteger, nullable=True)
    approved_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    # Every FK here is RESTRICT in the DB - this is deliberately the least-
    # deletable table in the schema. No destructive ORM cascade anywhere.
    property = relationship("Property", back_populates="approved_design_baselines")
    design_job = relationship("DesignJob", back_populates="approved_design_baselines")
    image_version = relationship("DesignImageVersion")
    tool = relationship("DesignTool", back_populates="approved_design_baselines")
