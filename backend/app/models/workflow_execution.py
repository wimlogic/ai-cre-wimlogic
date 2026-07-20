from sqlalchemy import Column, Integer, BigInteger, String, Text, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class WorkflowExecution(Base):
    __tablename__ = "cre_workflow_executions"

    execution_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    execution_number = Column(String(50), unique=True, index=True, nullable=False)
    project_id = Column(BigInteger, nullable=False)
    property_id = Column(BigInteger, ForeignKey("cre_properties.id", ondelete="CASCADE"), nullable=False)
    scenario_id = Column(BigInteger, nullable=True)
    workflow_code = Column(String(100), nullable=False)
    workflow_version = Column(String(50), nullable=True)
    devtools_execution_id = Column(String(100), nullable=True)
    status = Column(String(30), default="Submitted", nullable=False)  # Submitted, Running, Completed, Failed, Pending
    priority = Column(String(20), default="Normal", nullable=False)  # Low, Normal, High, Critical
    requested_by = Column(BigInteger, nullable=True)
    submitted_at = Column(DateTime, default=func.now(), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    # Distinct from error_message (which records a genuine REMOTE workflow
    # failure - _sync_failed_job()). This records a LOCAL failure to fetch
    # or map DEV-TOOLS' output AFTER the remote workflow already completed
    # successfully - the remote job is not re-run to recover from this;
    # re-polling (GET /ai-orchestration/status/{execution_id}) retries
    # only the fetch+sync step. Cleared back to NULL the moment a sync
    # attempt succeeds.
    result_sync_error = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    property = relationship("Property", back_populates="workflow_executions")
    results = relationship("WorkflowResult", back_populates="execution", cascade="all, delete-orphan")
    events = relationship("WorkflowEvent", back_populates="execution", cascade="all, delete-orphan")
    property_analysis_reports = relationship("PropertyAnalysisReport", back_populates="workflow_execution")
    concept_designs = relationship("ConceptDesign", back_populates="workflow_execution")
    generated_assets = relationship("GeneratedAsset", back_populates="execution", cascade="all, delete-orphan")
    estimates = relationship("Estimate", back_populates="workflow_execution")

    
