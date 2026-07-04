from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class ScanJob(Base):
    __tablename__ = "cre_scan_jobs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    scan_id = Column(String(100), unique=True, index=True, nullable=False)
    project_id = Column(String(100), ForeignKey("cre_projects.project_id", ondelete="CASCADE"), nullable=False)
    project_name = Column(String(255), nullable=False)
    main_street = Column(String(255), nullable=False)
    beginning_address = Column(String(255), nullable=False)
    ending_address = Column(String(255), nullable=False)
    side_selection = Column(String(50), nullable=False)
    status = Column(String(50), default="created", nullable=False)  # created, pending, running, completed, failed
    found_count = Column(Integer, default=0, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    scan_source = Column(String(120), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="scan_jobs")
