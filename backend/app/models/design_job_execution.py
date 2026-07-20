from sqlalchemy import Column, BigInteger, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class DesignJobExecution(Base):
    __tablename__ = "cre_design_job_executions"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    design_job_id = Column(BigInteger, ForeignKey("cre_design_jobs.id", ondelete="CASCADE"), nullable=False)
    workflow_execution_id = Column(BigInteger, ForeignKey("cre_workflow_executions.execution_id"), nullable=False, unique=True)
    attempt_number = Column(Integer, nullable=False)
    is_current = Column(Integer, default=1, nullable=False)  # tinyint(1) DEFAULT '1'
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    design_job = relationship("DesignJob", back_populates="executions")
    workflow_execution = relationship("WorkflowExecution")
