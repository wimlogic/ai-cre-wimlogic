from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class WorkflowEvent(Base):
    __tablename__ = "cre_workflow_events"

    event_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    execution_id = Column(BigInteger, ForeignKey("cre_workflow_executions.execution_id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    execution = relationship("WorkflowExecution", back_populates="events")

