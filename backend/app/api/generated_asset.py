from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.crud.generated_asset import generated_asset as crud_generated_asset
from app.schemas import GeneratedAssetCreate, GeneratedAssetUpdate, GeneratedAssetResponse, GeneratedAssetListResponse
from pydantic import BaseModel

router = APIRouter()

class DeleteResponse(BaseModel):
    success: bool = True

@router.post("/", response_model=GeneratedAssetResponse, status_code=201)
def create_generated_asset(obj_in: GeneratedAssetCreate, db: Session = Depends(get_db)):
    return crud_generated_asset.create(db, obj_in=obj_in)

@router.get("/{id}", response_model=GeneratedAssetResponse)
def get_generated_asset(id: int, db: Session = Depends(get_db)):
    db_obj = crud_generated_asset.get(db, asset_id=id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Generated asset not found")
    return db_obj

@router.get("/", response_model=GeneratedAssetListResponse)
def list_generated_assets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    property_id: Optional[int] = Query(None),
    execution_id: Optional[int] = Query(None),
    asset_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    items, total = crud_generated_asset.get_multi(
        db, skip=skip, limit=limit, property_id=property_id, execution_id=execution_id, asset_type=asset_type, search=search
    )
    return {"count": total, "items": items}

@router.put("/{id}", response_model=GeneratedAssetResponse)
def update_generated_asset(id: int, obj_in: GeneratedAssetUpdate, db: Session = Depends(get_db)):
    db_obj = crud_generated_asset.get(db, asset_id=id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Generated asset not found")
    return crud_generated_asset.update(db, db_obj=db_obj, obj_in=obj_in)

@router.delete("/{id}", response_model=DeleteResponse)
def delete_generated_asset(id: int, db: Session = Depends(get_db)):
    db_obj = crud_generated_asset.get(db, asset_id=id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Generated asset not found")
    crud_generated_asset.remove(db, asset_id=id)
    return {"success": True}
