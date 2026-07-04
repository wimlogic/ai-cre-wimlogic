from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.crud.project import project as crud_project
from app.crud.project_property import project_property as crud_project_property
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.models.project import Project
from app.schemas.project_property import ProjectPropertyCreate

class ProjectService:
    def get_project(self, db: Session, id: int) -> Optional[Project]:
        """Retrieve a project by its primary key ID."""
        return crud_project.get(db, id)

    def get_project_by_project_id(self, db: Session, project_id: str) -> Optional[Project]:
        """Retrieve a project by its unique, user-defined project_id string."""
        return crud_project.get_by_project_id(db, project_id)

    def get_projects(
        self, db: Session, skip: int = 0, limit: int = 100, status: Optional[str] = None, search: Optional[str] = None
    ) -> Tuple[List[Project], int]:
        """Get a list of projects with pagination, status filtering, and search options."""
        return crud_project.get_multi(db, skip=skip, limit=limit, status=status, search=search)

    def create_project(self, db: Session, project_in: ProjectCreate) -> Project:
        """Create a new project after ensuring the project_id does not conflict."""
        existing = crud_project.get_by_project_id(db, project_in.project_id)
        if existing:
            raise ValueError(f"Project with project_id '{project_in.project_id}' already exists")
        return crud_project.create(db, obj_in=project_in)

    def update_project(self, db: Session, id: int, project_in: ProjectUpdate) -> Optional[Project]:
        """Update an existing project by primary key ID with duplicate checks on project_id change."""
        db_obj = crud_project.get(db, id)
        if not db_obj:
            return None
        if project_in.project_id and project_in.project_id != db_obj.project_id:
            existing = crud_project.get_by_project_id(db, project_in.project_id)
            if existing:
                raise ValueError(f"Project with project_id '{project_in.project_id}' already exists")
        return crud_project.update(db, db_obj=db_obj, obj_in=project_in)

    def delete_project(self, db: Session, id: int) -> Optional[Project]:
        """Delete a project by primary key ID."""
        return crud_project.remove(db, id=id)

    def link_property(
        self, db: Session, project_id: str, property_id: int, scan_id: Optional[str] = None, role: Optional[str] = None, selected: int = 0
    ) -> None:
        """Link a property to a project."""
        link_in = ProjectPropertyCreate(
            project_id=project_id,
            property_id=property_id,
            scan_id=scan_id,
            role=role,
            selected=selected
        )
        crud_project_property.create(db, obj_in=link_in)

    def unlink_property(self, db: Session, project_property_link_id: int) -> Optional[object]:
        """Unlink a property from a project by deleting the relation row."""
        return crud_project_property.remove(db, id=project_property_link_id)

project_service = ProjectService()
