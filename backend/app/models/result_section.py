from sqlalchemy import Column, Integer, BigInteger, String, Text, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class ResultSection(Base):
    __tablename__ = "cre_result_sections"

    section_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    result_id = Column(BigInteger, ForeignKey("cre_workflow_results.result_id", ondelete="CASCADE"), nullable=False)
    section_type = Column(String(50), nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)  # maps to longtext
    confidence_score = Column(Numeric(5, 2), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    workflow_result = relationship("WorkflowResult", back_populates="sections")

