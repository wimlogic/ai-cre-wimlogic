from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class DesignImageLineage(Base):
    """
    Sole authority for all generated-version ancestry. Supports:
        ONE Property Image  -> MANY generated versions
        MANY source images  -> ONE generated version
        Prior version        -> New version (refinement chains, via
                                 source_type = 'image_version')

    cre_design_image_versions carries no parent_version_id of its own -
    ancestry, including version-to-version refinement chains, is never
    duplicated across the two tables.
    """
    __tablename__ = "cre_design_image_lineage"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    image_version_id = Column(BigInteger, ForeignKey("cre_design_image_versions.id", ondelete="CASCADE"), nullable=False)
    source_type = Column(String(20), nullable=False)  # property_image, image_version
    source_property_image_id = Column(BigInteger, ForeignKey("cre_property_images.id"), nullable=True)
    source_image_version_id = Column(BigInteger, ForeignKey("cre_design_image_versions.id"), nullable=True)
    lineage_role = Column(String(30), default="primary", nullable=False)  # primary, supporting, reference, parent
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    image_version = relationship(
        "DesignImageVersion",
        back_populates="lineage_entries",
        foreign_keys=[image_version_id],
    )
    # DB FK on source_property_image_id has no ON DELETE clause (RESTRICT) -
    # no destructive ORM cascade against PropertyImage.
    source_property_image = relationship(
        "PropertyImage",
        back_populates="lineage_as_source",
        foreign_keys=[source_property_image_id],
    )
    # DB FK on source_image_version_id is also RESTRICT - no destructive
    # ORM cascade here either.
    source_image_version = relationship(
        "DesignImageVersion",
        back_populates="sourced_lineage_entries",
        foreign_keys=[source_image_version_id],
    )
