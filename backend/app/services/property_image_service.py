from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.crud.property_image import property_image as crud_property_image
from app.schemas.property_image import PropertyImageCreate, PropertyImageUpdate
from app.models.property_image import PropertyImage

class PropertyImageService:
    def get_image(self, db: Session, id: int) -> Optional[PropertyImage]:
        """Retrieve a property image by its database primary key ID."""
        return crud_property_image.get(db, id)

    def get_images(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        property_id: Optional[int] = None,
        project_id: Optional[str] = None,
        image_type: Optional[str] = None,
        include_deleted: bool = False,
        search: Optional[str] = None
    ) -> Tuple[List[PropertyImage], int]:
        """Get a list of property images with pagination and multiple filtering options."""
        return crud_property_image.get_multi(
            db,
            skip=skip,
            limit=limit,
            property_id=property_id,
            project_id=project_id,
            image_type=image_type,
            include_deleted=include_deleted,
            search=search
        )

    def create_image(self, db: Session, image_in: PropertyImageCreate) -> PropertyImage:
        """Create a new property image entry."""
        return crud_property_image.create(db, obj_in=image_in)

    def update_image(self, db: Session, id: int, image_in: PropertyImageUpdate) -> Optional[PropertyImage]:
        """Update fields of an existing property image by database primary key ID."""
        db_obj = crud_property_image.get(db, id)
        if not db_obj:
            return None
        return crud_property_image.update(db, db_obj=db_obj, obj_in=image_in)

    def delete_image(self, db: Session, id: int, soft: bool = True) -> Optional[PropertyImage]:
        """Delete an image by database ID. Supports soft deleting (setting is_deleted to 1) or hard removal."""
        db_obj = crud_property_image.get(db, id)
        if not db_obj:
            return None
        
        if soft:
            # Update is_deleted to 1
            update_in = PropertyImageUpdate(is_deleted=1)
            return crud_property_image.update(db, db_obj=db_obj, obj_in=update_in)
        else:
            # Perform actual database hard deletion
            return crud_property_image.remove(db, id=id)

property_image_service = PropertyImageService()
