from sqlalchemy import Column, Integer, BigInteger, String, Text, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class ConceptDesign(Base):
    __tablename__ = "cre_concept_designs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(String(100), ForeignKey("cre_projects.project_id", ondelete="CASCADE"), nullable=False)
    property_id = Column(BigInteger, ForeignKey("cre_properties.id", ondelete="CASCADE"), nullable=False)
    scenario_id = Column(Integer, ForeignKey("cre_renovation_scenarios.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=True)
    concept_prompt = Column(Text, nullable=False)
    concept_notes = Column(Text, nullable=True)
    image_reference_ids = Column(JSON, nullable=True)
    status = Column(String(50), default="draft", nullable=False)  # draft, under_review, approved
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    workflow_execution_id = Column(BigInteger, ForeignKey("cre_workflow_executions.execution_id", ondelete="SET NULL"), nullable=True)
    design_version = Column(String(30), nullable=True)
    approved_by = Column(BigInteger, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="concept_designs")
    property = relationship("Property", back_populates="concept_designs")
    scenario = relationship("RenovationScenario", back_populates="concept_designs")
    workflow_execution = relationship("WorkflowExecution", back_populates="concept_designs")

