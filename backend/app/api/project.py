from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.crud.project import project as crud_project
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
from pydantic import BaseModel

router = APIRouter()

class DeleteResponse(BaseModel):
    success: bool = True

@router.post("/", response_model=ProjectResponse, status_code=201)
def create_project(obj_in: ProjectCreate, db: Session = Depends(get_db)):
    existing = crud_project.get_by_project_id(db, obj_in.project_id)
    if existing:
        raise HTTPException(status_code=400, detail=f"Project with project_id '{obj_in.project_id}' already exists")
    return crud_project.create(db, obj_in=obj_in)

@router.get("/{id}", response_model=ProjectResponse)
def get_project(id: int, db: Session = Depends(get_db)):
    db_obj = crud_project.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_obj

@router.get("/by-id/{project_id}", response_model=ProjectResponse)
def get_project_by_project_id(project_id: str, db: Session = Depends(get_db)):
    db_obj = crud_project.get_by_project_id(db, project_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return db_obj

@router.get("/", response_model=ProjectListResponse)
def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    items, total = crud_project.get_multi(
        db, skip=skip, limit=limit, status=status, search=search
    )
    return {"count": total, "items": items}

@router.put("/{id}", response_model=ProjectResponse)
def update_project(id: int, obj_in: ProjectUpdate, db: Session = Depends(get_db)):
    db_obj = crud_project.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Project not found")
    if obj_in.project_id and obj_in.project_id != db_obj.project_id:
        existing = crud_project.get_by_project_id(db, obj_in.project_id)
        if existing:
            raise HTTPException(status_code=400, detail=f"Project with project_id '{obj_in.project_id}' already exists")
    return crud_project.update(db, db_obj=db_obj, obj_in=obj_in)

@router.delete("/{id}", response_model=DeleteResponse)
def delete_project(id: int, db: Session = Depends(get_db)):
    db_obj = crud_project.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Project not found")
    crud_project.remove(db, id=id)
    return {"success": True}
