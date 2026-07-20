from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.crud.design_tool import design_tool as crud_design_tool
from app.crud.design_tool_option import design_tool_option as crud_design_tool_option
from app.schemas.design_tool_option import DesignToolOptionCreate, DesignToolOptionUpdate
from app.models.design_tool_option import DesignToolOption

class DesignToolOptionService:
    def get_option(self, db: Session, id: int) -> Optional[DesignToolOption]:
        return crud_design_tool_option.get(db, id)

    def get_option_scoped(self, db: Session, *, tool_id: int, id: int) -> Optional[DesignToolOption]:
        """
        Ownership-scoped lookup: returns the Option only if it both exists
        AND belongs to the given tool_id. Used by every nested GET/PUT/
        DELETE action so a child owned by one Tool can never be read,
        updated, or deleted through a different Tool's URL. Returns None
        (not the object) on any ownership mismatch, so the caller cannot
        distinguish "doesn't exist" from "belongs to another Tool" -
        both correctly surface as 404.
        """
        db_obj = crud_design_tool_option.get(db, id)
        if not db_obj or db_obj.tool_id != tool_id:
            return None
        return db_obj

    def get_options(self, db: Session, *, skip: int = 0, limit: int = 100, tool_id: Optional[int] = None) -> Tuple[List[DesignToolOption], int]:
        return crud_design_tool_option.get_multi(db, skip=skip, limit=limit, tool_id=tool_id)

    def create_option(self, db: Session, option_in: DesignToolOptionCreate) -> DesignToolOption:
        """
        Business rules validated here (not in CRUD): the parent Tool must
        actually exist, and (tool_id, option_code) must be unique - both
        pre-checked so the router can return a clean 400/404 instead of a
        raw FK/IntegrityError from the database.
        """
        tool = crud_design_tool.get(db, option_in.tool_id)
        if not tool:
            raise ValueError(f"Tool {option_in.tool_id} does not exist")
        existing_options, _ = crud_design_tool_option.get_multi(db, tool_id=option_in.tool_id, limit=1000)
        if any(o.option_code == option_in.option_code for o in existing_options):
            raise ValueError(f"Option code '{option_in.option_code}' already exists for this Tool")
        return crud_design_tool_option.create(db, obj_in=option_in)

    def update_option(self, db: Session, *, tool_id: int, id: int, option_in: DesignToolOptionUpdate) -> Optional[DesignToolOption]:
        """
        Ownership-checked update: the Option must belong to tool_id or
        this returns None (router maps to 404). If option_code is being
        changed, (tool_id, option_code) must remain unique among the
        Tool's other options - the current row is excluded from the
        collision check.
        """
        db_obj = self.get_option_scoped(db, tool_id=tool_id, id=id)
        if not db_obj:
            return None
        if option_in.option_code is not None and option_in.option_code != db_obj.option_code:
            existing_options, _ = crud_design_tool_option.get_multi(db, tool_id=tool_id, limit=1000)
            if any(o.option_code == option_in.option_code and o.id != id for o in existing_options):
                raise ValueError(f"Option code '{option_in.option_code}' already exists for this Tool")
        return crud_design_tool_option.update(db, db_obj=db_obj, obj_in=option_in)

    def delete_option(self, db: Session, *, tool_id: int, id: int) -> Optional[DesignToolOption]:
        """Ownership-checked delete: the Option must belong to tool_id or this returns None (router maps to 404)."""
        db_obj = self.get_option_scoped(db, tool_id=tool_id, id=id)
        if not db_obj:
            return None
        return crud_design_tool_option.remove(db, id=id)

design_tool_option_service = DesignToolOptionService()
