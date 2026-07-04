from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.crud.api_usage_log import api_usage_log as crud_api_usage_log
from app.schemas import ApiUsageLogCreate, ApiUsageLogUpdate, ApiUsageLogResponse, ApiUsageLogListResponse
from pydantic import BaseModel

router = APIRouter()

class DeleteResponse(BaseModel):
    success: bool = True

@router.post("/", response_model=ApiUsageLogResponse, status_code=201)
def create_api_usage_log(obj_in: ApiUsageLogCreate, db: Session = Depends(get_db)):
    return crud_api_usage_log.create(db, obj_in=obj_in)

@router.get("/{id}", response_model=ApiUsageLogResponse)
def get_api_usage_log(id: int, db: Session = Depends(get_db)):
    db_obj = crud_api_usage_log.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="API usage log not found")
    return db_obj

@router.get("/", response_model=ApiUsageLogListResponse)
def list_api_usage_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    provider: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    items, total = crud_api_usage_log.get_multi(db, skip=skip, limit=limit, provider=provider)
    return {"count": total, "items": items}

@router.put("/{id}", response_model=ApiUsageLogResponse)
def update_api_usage_log(id: int, obj_in: ApiUsageLogUpdate, db: Session = Depends(get_db)):
    db_obj = crud_api_usage_log.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="API usage log not found")
    return crud_api_usage_log.update(db, db_obj=db_obj, obj_in=obj_in)

@router.delete("/{id}", response_model=DeleteResponse)
def delete_api_usage_log(id: int, db: Session = Depends(get_db)):
    db_obj = crud_api_usage_log.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="API usage log not found")
    crud_api_usage_log.remove(db, id=id)
    return {"success": True}
