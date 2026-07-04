from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.crud.result_section import result_section as crud_result_section
from app.schemas import ResultSectionCreate, ResultSectionUpdate, ResultSectionResponse, ResultSectionListResponse
from pydantic import BaseModel

router = APIRouter()

class DeleteResponse(BaseModel):
    success: bool = True

@router.post("/", response_model=ResultSectionResponse, status_code=201)
def create_result_section(obj_in: ResultSectionCreate, db: Session = Depends(get_db)):
    return crud_result_section.create(db, obj_in=obj_in)

@router.get("/{id}", response_model=ResultSectionResponse)
def get_result_section(id: int, db: Session = Depends(get_db)):
    db_obj = crud_result_section.get(db, section_id=id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Result section not found")
    return db_obj

@router.get("/", response_model=ResultSectionListResponse)
def list_result_sections(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    result_id: Optional[int] = Query(None),
    section_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    items, total = crud_result_section.get_multi(
        db, skip=skip, limit=limit, result_id=result_id, section_type=section_type, search=search
    )
    return {"count": total, "items": items}

@router.put("/{id}", response_model=ResultSectionResponse)
def update_result_section(id: int, obj_in: ResultSectionUpdate, db: Session = Depends(get_db)):
    db_obj = crud_result_section.get(db, section_id=id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Result section not found")
    return crud_result_section.update(db, db_obj=db_obj, obj_in=obj_in)

@router.delete("/{id}", response_model=DeleteResponse)
def delete_result_section(id: int, db: Session = Depends(get_db)):
    db_obj = crud_result_section.get(db, section_id=id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Result section not found")
    crud_result_section.remove(db, section_id=id)
    return {"success": True}
