from sqlalchemy import Column, BigInteger, String, JSON, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class DesignToolImageRequirement(Base):
    __tablename__ = "cre_design_tool_image_requirements"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    tool_id = Column(BigInteger, ForeignKey("cre_design_tools.id", ondelete="CASCADE"), nullable=False)
    input_role = Column(String(30), nullable=False)  # primary, supporting, reference
    allowed_image_roles_json = Column(JSON, nullable=True)
    min_count = Column(Integer, default=0, nullable=False)
    max_count = Column(Integer, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    tool = relationship("DesignTool", back_populates="image_requirements")
