"""
tests/crud/test_design_tool_knowledge_rule_guard.py

Knowledge Inheritance Engine Phase 1.2A - Checkpoint 2 tests for the
duplicate-blanket-rule guard in crud/design_tool_knowledge_rule.py.
Requires a real database (create/update go through the real CRUD).
"""
import datetime

import pytest

from app.db.database import SessionLocal
from app.models.design_tool import DesignTool
from app.crud.design_tool_knowledge_rule import design_tool_knowledge_rule as crud_rule
from app.schemas.design_tool_knowledge_rule import DesignToolKnowledgeRuleCreate, DesignToolKnowledgeRuleUpdate


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def tool(db):
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    t = DesignTool(tool_code=f"TOOL-{suffix}", tool_name="Guard Test Tool", design_type="image_creation", workflow_code="WF_TEST")
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def test_second_blanket_rule_same_scope_rejected(db, tool):
    crud_rule.create(db, obj_in=DesignToolKnowledgeRuleCreate(tool_id=tool.id, knowledge_scope="project", field_code=None))
    with pytest.raises(ValueError, match="blanket Knowledge Rule"):
        crud_rule.create(db, obj_in=DesignToolKnowledgeRuleCreate(tool_id=tool.id, knowledge_scope="project", field_code=None))


def test_field_level_rule_alongside_blanket_rule_allowed(db, tool):
    crud_rule.create(db, obj_in=DesignToolKnowledgeRuleCreate(tool_id=tool.id, knowledge_scope="project", field_code=None))
    # Must not raise - a field-level row is not a second blanket row.
    field_rule = crud_rule.create(db, obj_in=DesignToolKnowledgeRuleCreate(tool_id=tool.id, knowledge_scope="project", field_code="PROJECT.GOALS"))
    assert field_rule.field_code == "PROJECT.GOALS"


def test_multiple_field_level_rules_same_scope_allowed(db, tool):
    crud_rule.create(db, obj_in=DesignToolKnowledgeRuleCreate(tool_id=tool.id, knowledge_scope="project", field_code="PROJECT.GOALS"))
    crud_rule.create(db, obj_in=DesignToolKnowledgeRuleCreate(tool_id=tool.id, knowledge_scope="project", field_code="PROJECT.BUDGET"))
    rules, count = crud_rule.get_multi(db, tool_id=tool.id)
    assert count == 2


def test_blanket_rules_different_scopes_both_allowed(db, tool):
    crud_rule.create(db, obj_in=DesignToolKnowledgeRuleCreate(tool_id=tool.id, knowledge_scope="project", field_code=None))
    crud_rule.create(db, obj_in=DesignToolKnowledgeRuleCreate(tool_id=tool.id, knowledge_scope="property", field_code=None))
    rules, count = crud_rule.get_multi(db, tool_id=tool.id)
    assert count == 2


def test_update_to_blanket_rejected_when_another_blanket_exists(db, tool):
    crud_rule.create(db, obj_in=DesignToolKnowledgeRuleCreate(tool_id=tool.id, knowledge_scope="project", field_code=None))
    field_rule = crud_rule.create(db, obj_in=DesignToolKnowledgeRuleCreate(tool_id=tool.id, knowledge_scope="project", field_code="PROJECT.GOALS"))

    with pytest.raises(ValueError, match="blanket Knowledge Rule"):
        crud_rule.update(db, db_obj=field_rule, obj_in=DesignToolKnowledgeRuleUpdate(field_code=None))


def test_get_by_scope_returns_only_blanket_row(db, tool):
    blanket = crud_rule.create(db, obj_in=DesignToolKnowledgeRuleCreate(tool_id=tool.id, knowledge_scope="project", field_code=None))
    crud_rule.create(db, obj_in=DesignToolKnowledgeRuleCreate(tool_id=tool.id, knowledge_scope="project", field_code="PROJECT.GOALS"))

    result = crud_rule.get_by_scope(db, tool_id=tool.id, knowledge_scope="project")
    assert result is not None
    assert result.id == blanket.id
