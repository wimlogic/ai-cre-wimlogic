from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.crud.workflow_execution import workflow_execution as crud_workflow_execution
from app.crud.workflow_event import workflow_event as crud_workflow_event
from app.schemas.workflow_execution import WorkflowExecutionCreate, WorkflowExecutionUpdate
from app.schemas.workflow_event import WorkflowEventCreate
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_event import WorkflowEvent

class WorkflowExecutionService:
    def get_execution(self, db: Session, execution_id: int) -> Optional[WorkflowExecution]:
        """Retrieve a workflow execution by database primary key ID."""
        return crud_workflow_execution.get(db, execution_id)

    def get_execution_by_number(self, db: Session, execution_number: str) -> Optional[WorkflowExecution]:
        """Retrieve a workflow execution by its unique user-facing execution number."""
        return crud_workflow_execution.get_by_execution_number(db, execution_number)

    def get_executions(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        project_id: Optional[int] = None,
        property_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None
    ) -> Tuple[List[WorkflowExecution], int]:
        """Get a list of workflow executions with pagination and filtering."""
        return crud_workflow_execution.get_multi(
            db, skip=skip, limit=limit, project_id=project_id, property_id=property_id, status=status, search=search
        )

    def create_execution(self, db: Session, execution_in: WorkflowExecutionCreate, commit: bool = True) -> WorkflowExecution:
        """
        commit=True (default, unchanged): existing legacy behavior -
        commits immediately, as before this change.
        commit=False: participates in a service-owned transaction (Design
        Studio Phase 1 local attempt registration, Checkpoint 8) - only
        flushes; the calling service owns commit/rollback.
        """
        existing = crud_workflow_execution.get_by_execution_number(db, execution_in.execution_number)
        if existing:
            raise ValueError(f"Workflow execution with number '{execution_in.execution_number}' already exists")
        return crud_workflow_execution.create(db, obj_in=execution_in, commit=commit)

    def update_execution(
        self, db: Session, execution_id: int, execution_in: WorkflowExecutionUpdate
    ) -> Optional[WorkflowExecution]:
        """Update an existing workflow execution by primary key ID."""
        db_obj = crud_workflow_execution.get(db, execution_id)
        if not db_obj:
            return None
        if execution_in.execution_number and execution_in.execution_number != db_obj.execution_number:
            existing = crud_workflow_execution.get_by_execution_number(db, execution_in.execution_number)
            if existing:
                raise ValueError(f"Workflow execution with number '{execution_in.execution_number}' already exists")
        return crud_workflow_execution.update(db, db_obj=db_obj, obj_in=execution_in)

    def delete_execution(self, db: Session, execution_id: int) -> Optional[WorkflowExecution]:
        """Delete a workflow execution by primary key ID."""
        return crud_workflow_execution.remove(db, execution_id=execution_id)

    def get_events(
        self, db: Session, execution_id: int, skip: int = 0, limit: int = 100
    ) -> Tuple[List[WorkflowEvent], int]:
        """Get all status and log events associated with a specific workflow execution."""
        return crud_workflow_event.get_multi(db, execution_id=execution_id, skip=skip, limit=limit)

    def add_event(
        self, db: Session, execution_id: int, event_type: str, status: str, message: Optional[str] = None, commit: bool = True
    ) -> WorkflowEvent:
        """
        Add a new execution event log and automatically synchronize the
        parent execution status if changed.

        commit=True (default, unchanged): existing legacy behavior.
        commit=False: participates in a service-owned transaction (Design
        Studio Phase 1 local attempt registration, Checkpoint 8) - both
        the event insert and the execution status-sync update only flush;
        the calling service owns commit/rollback.
        """
        event_in = WorkflowEventCreate(
            execution_id=execution_id,
            event_type=event_type,
            status=status,
            message=message
        )
        # Create event log
        event_obj = crud_workflow_event.create(db, obj_in=event_in, commit=commit)
        
        # Update execution state
        execution_obj = crud_workflow_execution.get(db, execution_id)
        if execution_obj and execution_obj.status != status:
            update_in = WorkflowExecutionUpdate(status=status)
            crud_workflow_execution.update(db, db_obj=execution_obj, obj_in=update_in, commit=commit)
            
        return event_obj

workflow_execution_service = WorkflowExecutionService()
