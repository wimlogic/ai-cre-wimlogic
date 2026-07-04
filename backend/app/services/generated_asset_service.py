from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.crud.generated_asset import generated_asset as crud_generated_asset
from app.schemas.generated_asset import GeneratedAssetCreate, GeneratedAssetUpdate
from app.models.generated_asset import GeneratedAsset

class GeneratedAssetService:
    def get_asset(self, db: Session, asset_id: int) -> Optional[GeneratedAsset]:
        """Retrieve a specific generated asset by its database primary key ID."""
        return crud_generated_asset.get(db, asset_id)

    def get_assets(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        property_id: Optional[int] = None,
        execution_id: Optional[int] = None,
        asset_type: Optional[str] = None,
        search: Optional[str] = None
    ) -> Tuple[List[GeneratedAsset], int]:
        """Get a list of generated assets with pagination and multiple filtering options."""
        return crud_generated_asset.get_multi(
            db,
            skip=skip,
            limit=limit,
            property_id=property_id,
            execution_id=execution_id,
            asset_type=asset_type,
            search=search
        )

    def create_asset(self, db: Session, asset_in: GeneratedAssetCreate) -> GeneratedAsset:
        """Create a new record for a workflow-generated asset."""
        return crud_generated_asset.create(db, obj_in=asset_in)

    def update_asset(self, db: Session, asset_id: int, asset_in: GeneratedAssetUpdate) -> Optional[GeneratedAsset]:
        """Update fields of an existing generated asset by database primary key ID."""
        db_obj = crud_generated_asset.get(db, asset_id)
        if not db_obj:
            return None
        return crud_generated_asset.update(db, db_obj=db_obj, obj_in=asset_in)

    def delete_asset(self, db: Session, asset_id: int) -> Optional[GeneratedAsset]:
        """Delete a generated asset metadata record by its database primary key ID."""
        return crud_generated_asset.remove(db, asset_id=asset_id)

generated_asset_service = GeneratedAssetService()
