from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, update as sa_update
from app.models.property_image import PropertyImage
from app.schemas.property_image import PropertyImageCreate, PropertyImageUpdate

class CRUDPropertyImage:
    def get(self, db: Session, id: int) -> Optional[PropertyImage]:
        return db.get(PropertyImage, id)

    def get_by_ids(self, db: Session, ids: List[int]) -> List[PropertyImage]:
        """
        Batch lookup for Design Job selected-image validation (Section 3 of
        the approved implementation plan). Pure DB read - ownership/count
        validation against a Design Job's property remains a service-layer
        responsibility, not performed here.
        """
        if not ids:
            return []
        statement = select(PropertyImage).where(PropertyImage.id.in_(ids))
        results = db.execute(statement).scalars().all()
        return list(results)

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, property_id: Optional[int] = None, project_id: Optional[str] = None, image_type: Optional[str] = None, include_deleted: bool = False, search: Optional[str] = None
    ) -> Tuple[List[PropertyImage], int]:
        query = select(PropertyImage)
        
        # Apply filters
        if not include_deleted:
            query = query.where(PropertyImage.is_deleted == 0)
        if property_id:
            query = query.where(PropertyImage.property_id == property_id)
        if project_id:
            query = query.where(PropertyImage.project_id == project_id)
        if image_type:
            query = query.where(PropertyImage.image_type == image_type)
        if search:
            query = query.where(
                or_(
                    PropertyImage.provider.ilike(f"%{search}%"),
                    PropertyImage.notes.ilike(f"%{search}%"),
                    PropertyImage.original_file_name.ilike(f"%{search}%")
                )
            )
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.order_by(PropertyImage.created_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: PropertyImageCreate, commit: bool = True) -> PropertyImage:
        """
        commit=True (default, unchanged): standalone use - commits and
        refreshes, exactly as before this change.
        commit=False: participates in the Create-Primary-Image transaction
        (create the row + clear other images' is_primary as one atomic
        unit) - only flushes (so the new row's id is populated), does not
        commit or roll back. The calling service owns commit/rollback.
        """
        db_obj = PropertyImage(**obj_in.model_dump())
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

    def update(self, db: Session, *, db_obj: PropertyImage, obj_in: PropertyImageUpdate, commit: bool = True) -> PropertyImage:
        """
        commit=True (default, unchanged): standalone use - commits and
        refreshes, exactly as before this change.
        commit=False: participates in the Primary Image transaction (clear
        other images' is_primary + apply this update as one atomic unit) -
        only flushes, does not commit or roll back. The calling service
        owns commit/rollback.
        """
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

    def clear_primary_for_property(self, db: Session, *, property_id: int, exclude_id: Optional[int] = None, commit: bool = True) -> int:
        """
        Bulk-clears is_primary on every OTHER non-deleted Property Image
        belonging to property_id (scoped strictly to that one property -
        never touches any other property's rows). A single UPDATE
        statement rather than a per-row ORM loop, since this is exactly
        the "clear every other image" step of the one-primary-image
        transaction and doesn't need per-row Python objects.

        commit=False: participates in the service-owned Primary Image
        transaction - only flushes, does not commit or roll back.
        Returns the number of rows affected.
        """
        statement = sa_update(PropertyImage).where(
            PropertyImage.property_id == property_id,
            PropertyImage.is_deleted == 0,
            PropertyImage.is_primary == 1,
        )
        if exclude_id is not None:
            statement = statement.where(PropertyImage.id != exclude_id)
        statement = statement.values(is_primary=0)
        result = db.execute(statement)
        if commit:
            db.commit()
        else:
            db.flush()
        return result.rowcount

    def remove(self, db: Session, *, id: int) -> Optional[PropertyImage]:
        obj = db.get(PropertyImage, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

property_image = CRUDPropertyImage()
