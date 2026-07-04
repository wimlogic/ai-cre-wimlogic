from sqlalchemy import Column, Integer, BigInteger, String, Text, Numeric, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class PropertyAnalysisReport(Base):
    __tablename__ = "cre_property_analysis_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(String(100), ForeignKey("cre_projects.project_id", ondelete="CASCADE"), nullable=False)
    property_id = Column(BigInteger, ForeignKey("cre_properties.id", ondelete="CASCADE"), nullable=False)
    scenario_id = Column(Integer, ForeignKey("cre_renovation_scenarios.id", ondelete="SET NULL"), nullable=True)
    estimate_low = Column(Numeric(14, 2), nullable=True)
    estimate_high = Column(Numeric(14, 2), nullable=True)
    zoning_notes = Column(Text, nullable=True)
    risk_notes = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    score = Column(Numeric(5, 2), nullable=True)
    report_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    workflow_execution_id = Column(BigInteger, ForeignKey("cre_workflow_executions.execution_id", ondelete="SET NULL"), nullable=True)
    workflow_result_id = Column(BigInteger, ForeignKey("cre_workflow_results.result_id", ondelete="SET NULL"), nullable=True)
    analysis_version = Column(String(30), nullable=True)
    confidence_score = Column(Numeric(5, 2), nullable=True)
    workflow_status = Column(String(30), nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="property_analysis_reports")
    property = relationship("Property", back_populates="property_analysis_reports")
    scenario = relationship("RenovationScenario", back_populates="property_analysis_reports")
    workflow_execution = relationship("WorkflowExecution", back_populates="property_analysis_reports")
    workflow_result = relationship("WorkflowResult", back_populates="property_analysis_reports")
