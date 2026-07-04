from sqlalchemy import Column, Integer, BigInteger, String, DateTime, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class Scan(Base):
    __tablename__ = "cre_scans"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    scan_uid = Column(String(120), unique=True, index=True, nullable=False)
    city = Column(String(100), nullable=True)
    state = Column(String(20), nullable=True)
    main_street = Column(String(150), nullable=True)
    start_address = Column(String(255), nullable=True)
    end_address = Column(String(255), nullable=True)
    side = Column(String(50), nullable=False)  # north, south, east, west, both
    scan_mode = Column(String(50), nullable=False)  # quick, full
    status = Column(String(50), default="pending", nullable=False)  # pending, processing, complete, failed
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    project_id = Column(String(100), nullable=True)
    project_name = Column(String(255), nullable=True)
    scan_source = Column(String(120), nullable=True)

    # Relationships
    properties_association = relationship("ScanProperty", back_populates="scan", cascade="all, delete-orphan")

