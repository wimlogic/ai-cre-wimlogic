from sqlalchemy import Column, Integer, BigInteger, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class ScanProperty(Base):
    __tablename__ = "cre_scan_properties"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    scan_id = Column(BigInteger, ForeignKey("cre_scans.id", ondelete="CASCADE"), nullable=False)
    property_id = Column(BigInteger, ForeignKey("cre_properties.id", ondelete="CASCADE"), nullable=False)
    scan_order = Column(Integer, nullable=True)
    side_of_street = Column(String(20), nullable=True)
    frontage_street = Column(String(150), nullable=True)
    included_reason = Column(String(255), nullable=True)

    # Relationships
    scan = relationship("Scan", back_populates="properties_association")
    property = relationship("Property", back_populates="scans_association")

