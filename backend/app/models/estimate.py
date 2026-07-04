from sqlalchemy import Column, Integer, BigInteger, String, Text, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class Estimate(Base):
    __tablename__ = "cre_estimates"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    property_id = Column(BigInteger, ForeignKey("cre_properties.id", ondelete="CASCADE"), nullable=False)
    scenario = Column(String(100), nullable=False)  # enum('cosmetic','heavy_remodel','demo_rebuild','custom')
    proposed_use = Column(String(255), nullable=True)
    proposed_building_sqft = Column(Integer, nullable=True)
    proposed_units = Column(Integer, nullable=True)
    low_cost = Column(Numeric(14, 2), nullable=True)
    mid_cost = Column(Numeric(14, 2), nullable=True)
    high_cost = Column(Numeric(14, 2), nullable=True)
    cost_per_sqft_low = Column(Numeric(10, 2), nullable=True)
    cost_per_sqft_high = Column(Numeric(10, 2), nullable=True)
    assumptions = Column(Text, nullable=True)
    risk_level = Column(String(50), default="medium", nullable=False)  # enum('low','medium','high')
    created_at = Column(DateTime, default=func.now(), nullable=False)
    workflow_execution_id = Column(BigInteger, ForeignKey("cre_workflow_executions.execution_id", ondelete="SET NULL"), nullable=True)
    estimate_source = Column(String(50), nullable=True)
    estimate_version = Column(String(30), nullable=True)

    # Relationships
    property = relationship("Property", back_populates="estimates")
    workflow_execution = relationship("WorkflowExecution", back_populates="estimates")

