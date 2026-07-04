from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class GeneratedAsset(Base):
    __tablename__ = "cre_generated_assets"

    asset_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    execution_id = Column(BigInteger, ForeignKey("cre_workflow_executions.execution_id", ondelete="CASCADE"), nullable=False)
    property_id = Column(BigInteger, ForeignKey("cre_properties.id", ondelete="CASCADE"), nullable=False)
    asset_type = Column(String(50), nullable=False)
    asset_category = Column(String(50), nullable=True)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    file_name = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=True)
    mime_type = Column(String(100), nullable=True)
    file_size = Column(BigInteger, nullable=True)
    version = Column(String(30), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    execution = relationship("WorkflowExecution", back_populates="generated_assets")
    property = relationship("Property", back_populates="generated_assets")

