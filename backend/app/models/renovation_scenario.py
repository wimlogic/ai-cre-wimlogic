from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class RenovationScenario(Base):
    __tablename__ = "cre_renovation_scenarios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(String(100), ForeignKey("cre_projects.project_id", ondelete="CASCADE"), nullable=False)
    property_id = Column(BigInteger, ForeignKey("cre_properties.id", ondelete="CASCADE"), nullable=False)
    renovation_type = Column(String(100), nullable=False)
    scenario_type = Column(String(100), nullable=True)
    scenario_name = Column(String(255), nullable=True)
    rationale = Column(Text, nullable=True)
    risk_level = Column(String(50), nullable=True)  # low, medium, high
    estimated_complexity = Column(String(50), nullable=True)  # low, medium, high
    custom_notes = Column(Text, nullable=True)
    status = Column(String(50), default="draft", nullable=False)  # draft, approved, rejected
    source = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="renovation_scenarios")
    property = relationship("Property", back_populates="renovation_scenarios")
    property_analysis_reports = relationship("PropertyAnalysisReport", back_populates="scenario")
    concept_designs = relationship("ConceptDesign", back_populates="scenario")

