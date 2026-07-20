from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.design_tool_knowledge_rule import DesignToolKnowledgeRule
from app.schemas.design_tool_knowledge_rule import DesignToolKnowledgeRuleCreate, DesignToolKnowledgeRuleUpdate

class CRUDDesignToolKnowledgeRule:
    def get(self, db: Session, id: int) -> Optional[DesignToolKnowledgeRule]:
        return db.get(DesignToolKnowledgeRule, id)

    def get_by_scope(self, db: Session, *, tool_id: int, knowledge_scope: str) -> Optional[DesignToolKnowledgeRule]:
        """
        Returns the BLANKET (field_code IS NULL) rule row for this scope,
        if one exists. Phase 1.2A note: a scope may now additionally have
        any number of field-level rows (field_code IS NOT NULL) alongside
        this one - this function's contract is unchanged (it has always
        meant "the scope-wide rule", never "every rule for this scope"),
        it just no longer means "the only row" for this scope. Callers
        needing every rule for a scope (payload_builder.py's Phase 1.2A
        integration, Checkpoint 3) use get_multi() with their own filter.
        """
        statement = select(DesignToolKnowledgeRule).where(
            DesignToolKnowledgeRule.tool_id == tool_id,
            DesignToolKnowledgeRule.knowledge_scope == knowledge_scope,
            DesignToolKnowledgeRule.field_code.is_(None),
        )
        return db.execute(statement).scalars().first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, tool_id: Optional[int] = None
    ) -> Tuple[List[DesignToolKnowledgeRule], int]:
        query = select(DesignToolKnowledgeRule)

        if tool_id is not None:
            query = query.where(DesignToolKnowledgeRule.tool_id == tool_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()

        statement = query.order_by(DesignToolKnowledgeRule.created_at.asc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()

        return list(results), total_count

    def _assert_no_duplicate_blanket_rule(self, db: Session, *, tool_id: int, knowledge_scope: str, exclude_id: Optional[int] = None) -> None:
        """
        Phase 1.2A guard: the database's own UNIQUE(tool_id,
        knowledge_scope, field_code) constraint does NOT catch two
        blanket (field_code IS NULL) rows for the same tool+scope, since
        MySQL/MariaDB (and SQLite) treat multiple NULLs as distinct under
        a unique index. This service-layer check is the actual
        enforcement for that specific case - a second layer, not a
        replacement for the DB constraint, which still catches every
        other duplicate (two rows with the same non-null field_code).
        """
        statement = select(DesignToolKnowledgeRule).where(
            DesignToolKnowledgeRule.tool_id == tool_id,
            DesignToolKnowledgeRule.knowledge_scope == knowledge_scope,
            DesignToolKnowledgeRule.field_code.is_(None),
        )
        existing = db.execute(statement).scalars().first()
        if existing and existing.id != exclude_id:
            raise ValueError(
                f"A blanket Knowledge Rule (field_code=NULL) already exists for tool_id={tool_id}, "
                f"knowledge_scope='{knowledge_scope}' (rule id={existing.id}). Only one blanket rule "
                f"is permitted per (tool, scope); add a field_code-specific rule instead."
            )

    def create(self, db: Session, *, obj_in: DesignToolKnowledgeRuleCreate, commit: bool = True) -> DesignToolKnowledgeRule:
        if obj_in.field_code is None:
            self._assert_no_duplicate_blanket_rule(db, tool_id=obj_in.tool_id, knowledge_scope=obj_in.knowledge_scope)
        db_obj = DesignToolKnowledgeRule(**obj_in.model_dump())
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

    def update(self, db: Session, *, db_obj: DesignToolKnowledgeRule, obj_in: DesignToolKnowledgeRuleUpdate, commit: bool = True) -> DesignToolKnowledgeRule:
        update_data = obj_in.model_dump(exclude_unset=True)
        resulting_field_code = update_data.get("field_code", db_obj.field_code)
        if resulting_field_code is None:
            resulting_scope = update_data.get("knowledge_scope", db_obj.knowledge_scope)
            resulting_tool_id = update_data.get("tool_id", db_obj.tool_id)
            self._assert_no_duplicate_blanket_rule(
                db, tool_id=resulting_tool_id, knowledge_scope=resulting_scope, exclude_id=db_obj.id
            )
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

    def remove(self, db: Session, *, id: int, commit: bool = True) -> Optional[DesignToolKnowledgeRule]:
        obj = db.get(DesignToolKnowledgeRule, id)
        if obj:
            db.delete(obj)
            if commit:
                db.commit()
            else:
                db.flush()
        return obj

design_tool_knowledge_rule = CRUDDesignToolKnowledgeRule()
