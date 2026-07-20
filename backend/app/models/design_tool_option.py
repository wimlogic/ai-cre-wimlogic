from sqlalchemy import Column, BigInteger, String, JSON, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class DesignToolOption(Base):
    __tablename__ = "cre_design_tool_options"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    tool_id = Column(BigInteger, ForeignKey("cre_design_tools.id", ondelete="CASCADE"), nullable=False)
    option_code = Column(String(50), nullable=False)
    option_label = Column(String(150), nullable=False)
    option_type = Column(String(30), nullable=False)  # select, multiselect, boolean, number, text, slider
    allowed_values_json = Column(JSON, nullable=True)
    default_value = Column(String(255), nullable=True)
    is_required = Column(Integer, default=0, nullable=False)  # tinyint(1) DEFAULT '0'
    display_order = Column(Integer, default=0, nullable=False)
    status = Column(String(30), default="active", nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    tool = relationship("DesignTool", back_populates="options")
