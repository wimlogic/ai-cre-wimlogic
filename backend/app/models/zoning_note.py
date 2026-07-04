from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class ZoningNote(Base):
    __tablename__ = "cre_zoning_notes"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    property_id = Column(BigInteger, ForeignKey("cre_properties.id", ondelete="CASCADE"), nullable=False)
    zoning_code = Column(String(50), nullable=True)
    allowed_use_summary = Column(Text, nullable=True)
    conditional_use_notes = Column(Text, nullable=True)
    parking_notes = Column(Text, nullable=True)
    entitlement_risk = Column(String(50), default="medium", nullable=False)  # low, medium, high
    source_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    property = relationship("Property", back_populates="zoning_notes")
