from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, JSON, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class Project(Base):
    __tablename__ = "cre_projects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(String(100), unique=True, index=True, nullable=False)
    project_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="active", nullable=False)  # active, archived, completed
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    default_city = Column(String(120), nullable=True)
    default_state = Column(String(50), nullable=True)
    main_street = Column(String(255), nullable=True)
    beginning_address = Column(String(255), nullable=True)
    ending_address = Column(String(255), nullable=True)
    side = Column(String(50), nullable=True)
    scan_mode = Column(String(50), nullable=True)
    # Knowledge Inheritance Engine Phase 1.2A - additive, nullable.
    # Populated only ever read into effective_context via an explicit
    # FIELD_RULE_REGISTRY-backed Knowledge Rule (knowledge_context_builder.py) -
    # never automatically, regardless of any existing blanket scope rule.
    goals = Column(Text, nullable=True)
    hoa_rules = Column(Text, nullable=True)
    climate = Column(Text, nullable=True)
    budget_low = Column(Numeric(14, 2), nullable=True)
    budget_high = Column(Numeric(14, 2), nullable=True)
    preferred_styles = Column(JSON, nullable=True)
    design_preferences = Column(Text, nullable=True)

    # Relationships
    properties_association = relationship("ProjectProperty", back_populates="project", cascade="all, delete-orphan")
    scan_jobs = relationship("ScanJob", back_populates="project", cascade="all, delete-orphan")
    renovation_scenarios = relationship("RenovationScenario", back_populates="project", cascade="all, delete-orphan")
    property_analysis_reports = relationship("PropertyAnalysisReport", back_populates="project", cascade="all, delete-orphan")
    concept_designs = relationship("ConceptDesign", back_populates="project", cascade="all, delete-orphan")

