from sqlalchemy import Column, BigInteger, String, Text, JSON, Integer, DateTime, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class DesignTool(Base):
    __tablename__ = "cre_design_tools"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    tool_code = Column(String(50), unique=True, index=True, nullable=False)
    tool_name = Column(String(150), nullable=False)
    design_type = Column(String(50), nullable=False)
    workflow_code = Column(String(100), nullable=False)
    card_image_path = Column(String(500), nullable=True)
    icon_code = Column(String(50), nullable=True)
    business_description = Column(Text, nullable=True)
    business_purpose = Column(Text, nullable=True)
    business_instructions = Column(Text, nullable=True)
    input_config_json = Column(JSON, nullable=True)
    output_expectations_json = Column(JSON, nullable=True)
    status = Column(String(30), default="active", nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    # Catalog children - DB FK is ON DELETE CASCADE, so ORM cascade matches.
    options = relationship("DesignToolOption", back_populates="tool", cascade="all, delete-orphan")
    image_requirements = relationship("DesignToolImageRequirement", back_populates="tool", cascade="all, delete-orphan")
    knowledge_rules = relationship("DesignToolKnowledgeRule", back_populates="tool", cascade="all, delete-orphan")

    # Referenced by - DB FK from these tables back to cre_design_tools has
    # no ON DELETE clause (RESTRICT), so no destructive ORM cascade here.
    design_jobs = relationship("DesignJob", back_populates="tool")
    approved_design_baselines = relationship("ApprovedDesignBaseline", back_populates="tool")
