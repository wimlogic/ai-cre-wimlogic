from sqlalchemy import Column, BigInteger, String, Text, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class DesignJob(Base):
    __tablename__ = "cre_design_jobs"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    job_number = Column(String(50), unique=True, index=True, nullable=False)
    project_id = Column(String(100), nullable=False)  # business context only, not FK'd - matches existing convention
    property_id = Column(BigInteger, ForeignKey("cre_properties.id"), nullable=False)
    tool_id = Column(BigInteger, ForeignKey("cre_design_tools.id"), nullable=False)
    tool_code = Column(String(50), nullable=False)
    design_type = Column(String(50), nullable=False)
    workflow_code = Column(String(100), nullable=False)
    tool_options_json = Column(JSON, nullable=True)
    effective_context_json = Column(JSON, nullable=True)
    submitted_payload_json = Column(JSON, nullable=True)
    status = Column(String(30), default="draft", nullable=False)  # draft, submitted, processing, completed, failed, cancelled
    # Knowledge Inheritance Engine Phase 1.2A - additive, nullable, job-wide
    # instructions distinct in scope from per-image ai_prompt/constraints on
    # cre_property_images (both are aggregated together in effective_context,
    # neither overrides the other - see DESIGN_JOB.PROMPT / .CONSTRAINTS in
    # knowledge_context_builder.py's FIELD_RULE_REGISTRY). Settable via the
    # existing DesignJobConfigureOptionsRequest, mutable while status='draft',
    # exactly like tool_options_json already is.
    job_prompt = Column(Text, nullable=True)
    job_constraints = Column(Text, nullable=True)
    requested_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    # DB FK on property_id / tool_id has no ON DELETE clause (RESTRICT) -
    # no destructive ORM cascade against Property or DesignTool.
    property = relationship("Property", back_populates="design_jobs")
    tool = relationship("DesignTool", back_populates="design_jobs")

    # Owned children - DB FK is ON DELETE CASCADE, so ORM cascade matches.
    executions = relationship("DesignJobExecution", back_populates="design_job", cascade="all, delete-orphan")
    images = relationship("DesignJobImage", back_populates="design_job", cascade="all, delete-orphan")

    # Referenced by - DB FK from cre_design_image_versions.design_job_id has
    # no ON DELETE clause (RESTRICT), so no destructive ORM cascade here.
    image_versions = relationship("DesignImageVersion", back_populates="design_job")
    approved_design_baselines = relationship("ApprovedDesignBaseline", back_populates="design_job")
