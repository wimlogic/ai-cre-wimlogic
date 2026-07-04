from sqlalchemy import Column, Integer, BigInteger, String, Text, Numeric, DateTime, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class Property(Base):
    __tablename__ = "cre_properties"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    property_uid = Column(String(120), unique=True, index=True, nullable=False)
    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(20), nullable=True)
    zip = Column(String(20), nullable=True)
    apn = Column(String(50), nullable=True)
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)
    lot_sqft = Column(Integer, nullable=True)
    building_sqft = Column(Integer, nullable=True)
    year_built = Column(Integer, nullable=True)
    zoning_code = Column(String(50), nullable=True)
    existing_use = Column(String(150), nullable=True)
    business_name = Column(String(255), nullable=True)
    land_value = Column(Numeric(14, 2), nullable=True)
    improvement_value = Column(Numeric(14, 2), nullable=True)
    total_assessed_value = Column(Numeric(14, 2), nullable=True)
    data_source = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    street_number = Column(String(50), nullable=True)
    street_name = Column(String(255), nullable=True)
    side_of_street = Column(String(50), nullable=True)
    phase2_source = Column(String(100), nullable=True)
    display_address = Column(String(255), nullable=True)
    status = Column(String(80), nullable=True)
    source = Column(String(120), nullable=True)
    notes = Column(Text, nullable=True)
    confidence_score = Column(String(50), nullable=True)
    raw_api_json = Column(Text, nullable=True)  # longtext
    api_source_url = Column(String(500), nullable=True)

    # Relationships
    projects_association = relationship("ProjectProperty", back_populates="property", cascade="all, delete-orphan")
    images = relationship("PropertyImage", back_populates="property", cascade="all, delete-orphan")
    workflow_executions = relationship("WorkflowExecution", back_populates="property", cascade="all, delete-orphan")
    renovation_scenarios = relationship("RenovationScenario", back_populates="property", cascade="all, delete-orphan")
    property_analysis_reports = relationship("PropertyAnalysisReport", back_populates="property", cascade="all, delete-orphan")
    concept_designs = relationship("ConceptDesign", back_populates="property", cascade="all, delete-orphan")
    generated_assets = relationship("GeneratedAsset", back_populates="property", cascade="all, delete-orphan")
    estimates = relationship("Estimate", back_populates="property", cascade="all, delete-orphan")
    zoning_notes = relationship("ZoningNote", back_populates="property", cascade="all, delete-orphan")
    scans_association = relationship("ScanProperty", back_populates="property", cascade="all, delete-orphan")

