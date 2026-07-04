from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class WorkflowResult(Base):
    __tablename__ = "cre_workflow_results"

    result_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    execution_id = Column(BigInteger, ForeignKey("cre_workflow_executions.execution_id", ondelete="CASCADE"), nullable=False)
    result_type = Column(String(50), nullable=False)
    result_version = Column(String(30), nullable=True)
    response_json = Column(Text, nullable=True)  # longtext
    normalized = Column(Integer, default=1, nullable=False)  # tinyint(1) NOT NULL DEFAULT '1'
    received_at = Column(DateTime, default=func.now(), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    execution = relationship("WorkflowExecution", back_populates="results")
    property_analysis_reports = relationship("PropertyAnalysisReport", back_populates="workflow_result")
    sections = relationship("ResultSection", back_populates="workflow_result", cascade="all, delete-orphan")

