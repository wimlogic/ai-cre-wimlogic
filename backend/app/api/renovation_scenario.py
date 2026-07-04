from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.crud.renovation_scenario import renovation_scenario as crud_renovation_scenario
from app.schemas import RenovationScenarioCreate, RenovationScenarioUpdate, RenovationScenarioResponse, RenovationScenarioListResponse
from pydantic import BaseModel

router = APIRouter()

class DeleteResponse(BaseModel):
    success: bool = True

@router.post("/", response_model=RenovationScenarioResponse, status_code=201)
def create_renovation_scenario(obj_in: RenovationScenarioCreate, db: Session = Depends(get_db)):
    return crud_renovation_scenario.create(db, obj_in=obj_in)

@router.get("/{id}", response_model=RenovationScenarioResponse)
def get_renovation_scenario(id: int, db: Session = Depends(get_db)):
    db_obj = crud_renovation_scenario.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Renovation scenario not found")
    return db_obj

@router.get("/", response_model=RenovationScenarioListResponse)
def list_renovation_scenarios(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    project_id: Optional[str] = Query(None),
    property_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    items, total = crud_renovation_scenario.get_multi(
        db, skip=skip, limit=limit, project_id=project_id, property_id=property_id, status=status, search=search
    )
    return {"count": total, "items": items}

@router.put("/{id}", response_model=RenovationScenarioResponse)
def update_renovation_scenario(id: int, obj_in: RenovationScenarioUpdate, db: Session = Depends(get_db)):
    db_obj = crud_renovation_scenario.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Renovation scenario not found")
    return crud_renovation_scenario.update(db, db_obj=db_obj, obj_in=obj_in)

@router.delete("/{id}", response_model=DeleteResponse)
def delete_renovation_scenario(id: int, db: Session = Depends(get_db)):
    db_obj = crud_renovation_scenario.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Renovation scenario not found")
    crud_renovation_scenario.remove(db, id=id)
    return {"success": True}
