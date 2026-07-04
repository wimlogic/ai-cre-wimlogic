from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class ProjectProperty(Base):
    __tablename__ = "cre_project_properties"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(String(100), ForeignKey("cre_projects.project_id", ondelete="CASCADE"), nullable=False)
    property_id = Column(BigInteger, ForeignKey("cre_properties.id", ondelete="CASCADE"), nullable=False)
    scan_id = Column(String(100), nullable=True)
    role = Column(String(100), nullable=True)
    selected = Column(Integer, default=0, nullable=False)  # tinyint(1) DEFAULT '0'
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="properties_association")
    property = relationship("Property", back_populates="projects_association")

