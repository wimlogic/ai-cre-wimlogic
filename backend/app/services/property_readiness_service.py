"""
services/property_readiness_service.py

AI-CRE WIMLOGIC V1.0A -- Enterprise Business Service
Phase 3 -- Enterprise Image Upload & Workflow Integration

Purpose
-------
Pure computation service that evaluates whether a Property has enough
business data and images to proceed toward AI workflow submission.

This service performs NO AI calls and NO workflow execution. It reads
existing Property and PropertyImage data and produces a structured
readiness assessment: Data Completeness, Image Completeness, Required
Fields status, Workflow Readiness, AI Readiness, Missing Information,
and Suggested Next Actions.

Grounded In
-----------
- 07_PROPERTIES.md "Add Property Dialog" (General/Business fields) and
  "Business Summary" KPIs (Ready for AI, Missing Images, Missing
  Information).
- 08_PROPERTY_IMAGES.md "AI Readiness" examples (Ready, Missing Street
  View, Missing Exterior, Missing Interior).
- The actual columns present on app.models.property.Property and
  app.models.property_image.PropertyImage. No new database columns or
  tables are assumed or invented.

Architecture Compliance
-------------------------
- No SQL appears in this file.
- No new CRUD is introduced. All data access is performed through the
  EXISTING service layer: app.services.property_service (wraps
  crud.property) and app.services.property_image_service (wraps
  crud.property_image) -- reused rather than duplicated.
- This service does not call AI orchestration, submit workflows, or
  reach DEV-TOOLS WIMLOGIC in any way. It only reads and computes.
- Output is expressed as plain dataclasses rather than a persisted
  Pydantic/DB schema, since readiness is a computed, non-persisted
  business view, not a database entity.

Required Property Fields (Data Completeness)
------------------------------------------------
Sourced from the Enterprise "Add Property Dialog" General/Business
sections, mapped onto existing Property columns:

    address        -> "Address"
    city           -> "City"
    state          -> "State"
    zip            -> "ZIP Code"
    apn            -> "APN"
    existing_use   -> "Property Type"
    zoning_code    -> "Zoning"
    lot_sqft       -> "Land Area"
    building_sqft  -> "Building Area"
    year_built     -> "Year Built"

Required Image Categories (Image Completeness)
------------------------------------------------
Sourced from the "AI Readiness" examples in 08_PROPERTY_IMAGES.md
("Missing Street View", "Missing Exterior", "Missing Interior"), mapped
onto the existing PropertyImage.image_type enum and the free-text
PropertyImage.image_role column (no new columns introduced):

    image_type == 'street_view'          -> "Street View"
    image_role contains 'exterior' (ci)  -> "Exterior Photos"
    image_role contains 'interior' (ci)  -> "Interior Photos"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.property import Property
from app.models.property_image import PropertyImage
from app.services.property_image_service import property_image_service
from app.services.property_service import property_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output data contracts (computed views, not persisted entities)
# ---------------------------------------------------------------------------

@dataclass
class MissingField:
    """A single required Property field that is empty/null."""

    field_name: str
    label: str


@dataclass
class DataCompletenessResult:
    """Completeness of the core business fields on a Property record."""

    total_required: int
    present_count: int
    percentage: float
    missing_fields: List[MissingField] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return self.present_count == self.total_required


@dataclass
class ImageCategoryStatus:
    """Whether a single required image category is satisfied."""

    category_label: str
    satisfied: bool
    matched_count: int


@dataclass
class ImageCompletenessResult:
    """Completeness of the required image categories for a Property."""

    total_images: int
    total_required_categories: int
    satisfied_categories: int
    percentage: float
    categories: List[ImageCategoryStatus] = field(default_factory=list)
    blocked_image_count: int = 0

    @property
    def is_complete(self) -> bool:
        return self.satisfied_categories == self.total_required_categories


@dataclass
class PropertyReadinessResult:
    """
    Full readiness assessment for a single Property. Computed on demand;
    never persisted.
    """

    property_id: int
    data_completeness: DataCompletenessResult
    image_completeness: ImageCompletenessResult
    workflow_ready: bool
    ai_ready: bool
    missing_information: List[str] = field(default_factory=list)
    suggested_next_actions: List[str] = field(default_factory=list)
    computed_at: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class PropertyReadinessService:
    """
    Computes business and image readiness for a Property ahead of AI
    workflow submission. Pure computation only -- no AI calls, no
    workflow execution, no writes.
    """

    # -- Required Property fields (Data Completeness) -----------------------
    # (attribute_name, human-readable label)
    REQUIRED_PROPERTY_FIELDS = (
        ("address", "Address"),
        ("city", "City"),
        ("state", "State"),
        ("zip", "ZIP Code"),
        ("apn", "APN"),
        ("existing_use", "Property Type"),
        ("zoning_code", "Zoning"),
        ("lot_sqft", "Land Area"),
        ("building_sqft", "Building Area"),
        ("year_built", "Year Built"),
    )

    # -- Required image categories (Image Completeness) ---------------------
    CATEGORY_STREET_VIEW = "Street View"
    CATEGORY_EXTERIOR = "Exterior Photos"
    CATEGORY_INTERIOR = "Interior Photos"

    # Image statuses that block AI Readiness even if categories are present.
    BLOCKED_IMAGE_STATUSES = {"failed", "rejected", "corrupted", "invalid"}

    # Upper bound used when reading all images for a property through the
    # existing paginated property_image_service.get_images(). Readiness
    # computation needs the full set, not a page, so a generously high
    # limit is passed explicitly rather than introducing a new
    # "get all" method on the CRUD/service layer.
    _MAX_IMAGE_FETCH = 5000

    # -- Public API -----------------------------------------------------

    def assess_property(self, db: Session, *, property_id: int) -> PropertyReadinessResult:
        """
        Compute the full readiness assessment for a Property.

        Raises ValueError if the property does not exist.
        """
        property_obj = property_service.get_property(db, property_id)
        if not property_obj:
            raise ValueError(f"Property with ID '{property_id}' does not exist")

        images, _total = property_image_service.get_images(
            db,
            skip=0,
            limit=self._MAX_IMAGE_FETCH,
            property_id=property_id,
            include_deleted=False,
        )

        data_result = self._compute_data_completeness(property_obj)
        image_result = self._compute_image_completeness(images)

        workflow_ready = data_result.is_complete and image_result.is_complete
        ai_ready = workflow_ready and image_result.blocked_image_count == 0

        missing_information = self._build_missing_information(data_result, image_result)
        suggested_next_actions = self._build_suggested_next_actions(
            data_result, image_result, ai_ready=ai_ready, workflow_ready=workflow_ready
        )

        logger.info(
            "Computed readiness for property_id=%s: data=%.0f%% image=%.0f%% "
            "workflow_ready=%s ai_ready=%s",
            property_id, data_result.percentage, image_result.percentage,
            workflow_ready, ai_ready,
        )

        return PropertyReadinessResult(
            property_id=property_id,
            data_completeness=data_result,
            image_completeness=image_result,
            workflow_ready=workflow_ready,
            ai_ready=ai_ready,
            missing_information=missing_information,
            suggested_next_actions=suggested_next_actions,
        )

    # -- Data Completeness ------------------------------------------------

    def _compute_data_completeness(self, property_obj: Property) -> DataCompletenessResult:
        missing_fields: List[MissingField] = []
        present_count = 0

        for attribute_name, label in self.REQUIRED_PROPERTY_FIELDS:
            value = getattr(property_obj, attribute_name, None)
            if self._is_present(value):
                present_count += 1
            else:
                missing_fields.append(MissingField(field_name=attribute_name, label=label))

        total_required = len(self.REQUIRED_PROPERTY_FIELDS)
        percentage = (present_count / total_required * 100.0) if total_required else 100.0

        return DataCompletenessResult(
            total_required=total_required,
            present_count=present_count,
            percentage=round(percentage, 2),
            missing_fields=missing_fields,
        )

    # -- Image Completeness ------------------------------------------------

    def _compute_image_completeness(self, images: List[PropertyImage]) -> ImageCompletenessResult:
        street_view_count = sum(1 for img in images if (img.image_type or "").lower() == "street_view")
        exterior_count = sum(1 for img in images if "exterior" in (img.image_role or "").lower())
        interior_count = sum(1 for img in images if "interior" in (img.image_role or "").lower())

        blocked_count = sum(
            1 for img in images if (img.status or "").lower() in self.BLOCKED_IMAGE_STATUSES
        )

        categories = [
            ImageCategoryStatus(
                category_label=self.CATEGORY_STREET_VIEW,
                satisfied=street_view_count > 0,
                matched_count=street_view_count,
            ),
            ImageCategoryStatus(
                category_label=self.CATEGORY_EXTERIOR,
                satisfied=exterior_count > 0,
                matched_count=exterior_count,
            ),
            ImageCategoryStatus(
                category_label=self.CATEGORY_INTERIOR,
                satisfied=interior_count > 0,
                matched_count=interior_count,
            ),
        ]

        satisfied_categories = sum(1 for c in categories if c.satisfied)
        total_required_categories = len(categories)
        percentage = (
            (satisfied_categories / total_required_categories * 100.0) if total_required_categories else 100.0
        )

        return ImageCompletenessResult(
            total_images=len(images),
            total_required_categories=total_required_categories,
            satisfied_categories=satisfied_categories,
            percentage=round(percentage, 2),
            categories=categories,
            blocked_image_count=blocked_count,
        )

    # -- Missing Information / Suggested Next Actions -----------------------

    def _build_missing_information(
        self, data_result: DataCompletenessResult, image_result: ImageCompletenessResult
    ) -> List[str]:
        missing: List[str] = [f"Missing {mf.label}" for mf in data_result.missing_fields]
        missing.extend(
            f"Missing {c.category_label}" for c in image_result.categories if not c.satisfied
        )
        if image_result.blocked_image_count > 0:
            missing.append(
                f"{image_result.blocked_image_count} image(s) require review before AI processing"
            )
        return missing

    def _build_suggested_next_actions(
        self,
        data_result: DataCompletenessResult,
        image_result: ImageCompletenessResult,
        *,
        ai_ready: bool,
        workflow_ready: bool,
    ) -> List[str]:
        actions: List[str] = []

        for missing_field_item in data_result.missing_fields:
            actions.append(f"Add {missing_field_item.label} for this property.")

        for category in image_result.categories:
            if not category.satisfied:
                actions.append(f"Upload at least one {category.category_label} image.")

        if image_result.blocked_image_count > 0:
            actions.append(
                f"Review {image_result.blocked_image_count} image(s) with a blocked status "
                f"before running an AI workflow."
            )

        if workflow_ready and ai_ready and not actions:
            actions.append("Property is ready for AI workflow submission.")

        return actions

    # -- Internal helpers ---------------------------------------------------

    @staticmethod
    def _is_present(value: Optional[object]) -> bool:
        """
        A field is considered present if it is not None and, for strings,
        not empty/whitespace-only.
        """
        if value is None:
            return False
        if isinstance(value, str) and not value.strip():
            return False
        return True


property_readiness_service = PropertyReadinessService()
