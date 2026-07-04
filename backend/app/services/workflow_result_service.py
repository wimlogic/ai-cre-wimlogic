from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.crud.workflow_result import workflow_result as crud_workflow_result
from app.crud.result_section import result_section as crud_result_section
from app.crud.property_analysis_report import property_analysis_report as crud_property_analysis_report
from app.schemas.workflow_result import WorkflowResultCreate, WorkflowResultUpdate
from app.schemas.result_section import ResultSectionCreate, ResultSectionUpdate
from app.schemas.property_analysis_report import PropertyAnalysisReportCreate, PropertyAnalysisReportUpdate
from app.models.workflow_result import WorkflowResult
from app.models.result_section import ResultSection
from app.models.property_analysis_report import PropertyAnalysisReport

class WorkflowResultService:
    def get_result(self, db: Session, result_id: int) -> Optional[WorkflowResult]:
        """Retrieve a raw workflow result by database ID."""
        return crud_workflow_result.get(db, result_id)

    def get_results(
        self, db: Session, skip: int = 0, limit: int = 100, execution_id: Optional[int] = None, search: Optional[str] = None
    ) -> Tuple[List[WorkflowResult], int]:
        """Get a list of workflow results with pagination and filtering."""
        return crud_workflow_result.get_multi(db, skip=skip, limit=limit, execution_id=execution_id, search=search)

    def create_result(self, db: Session, result_in: WorkflowResultCreate) -> WorkflowResult:
        """Create a new raw workflow result entry."""
        return crud_workflow_result.create(db, obj_in=result_in)

    def update_result(self, db: Session, result_id: int, result_in: WorkflowResultUpdate) -> Optional[WorkflowResult]:
        """Update fields of an existing workflow result."""
        db_obj = crud_workflow_result.get(db, result_id)
        if not db_obj:
            return None
        return crud_workflow_result.update(db, db_obj=db_obj, obj_in=result_in)

    def delete_result(self, db: Session, result_id: int) -> Optional[WorkflowResult]:
        """Delete a workflow result by database ID."""
        return crud_workflow_result.remove(db, result_id=result_id)

    # Result Section Operations
    def get_section(self, db: Session, section_id: int) -> Optional[ResultSection]:
        """Retrieve a specific section of a parsed workflow result."""
        return crud_result_section.get(db, section_id)

    def get_sections(
        self, db: Session, skip: int = 0, limit: int = 100, result_id: Optional[int] = None, section_type: Optional[str] = None, search: Optional[str] = None
    ) -> Tuple[List[ResultSection], int]:
        """Get a list of parsed result sections with filtering."""
        return crud_result_section.get_multi(db, skip=skip, limit=limit, result_id=result_id, section_type=section_type, search=search)

    def create_section(self, db: Session, section_in: ResultSectionCreate) -> ResultSection:
        """Create a parsed section of a workflow result."""
        return crud_result_section.create(db, obj_in=section_in)

    def update_section(self, db: Session, section_id: int, section_in: ResultSectionUpdate) -> Optional[ResultSection]:
        """Update a parsed result section."""
        db_obj = crud_result_section.get(db, section_id)
        if not db_obj:
            return None
        return crud_result_section.update(db, db_obj=db_obj, obj_in=section_in)

    def delete_section(self, db: Session, section_id: int) -> Optional[ResultSection]:
        """Delete a parsed result section."""
        return crud_result_section.remove(db, section_id=section_id)

    # Property Analysis Report Operations
    def get_report(self, db: Session, report_id: int) -> Optional[PropertyAnalysisReport]:
        """Retrieve a compiled property analysis report."""
        return crud_property_analysis_report.get(db, report_id)

    def get_reports(
        self, db: Session, skip: int = 0, limit: int = 100, project_id: Optional[str] = None, property_id: Optional[int] = None, search: Optional[str] = None
    ) -> Tuple[List[PropertyAnalysisReport], int]:
        """Get a list of property analysis reports with filtering."""
        return crud_property_analysis_report.get_multi(db, skip=skip, limit=limit, project_id=project_id, property_id=property_id, search=search)

    def create_report(self, db: Session, report_in: PropertyAnalysisReportCreate) -> PropertyAnalysisReport:
        """Create a new property analysis report entry."""
        return crud_property_analysis_report.create(db, obj_in=report_in)

    def update_report(self, db: Session, report_id: int, report_in: PropertyAnalysisReportUpdate) -> Optional[PropertyAnalysisReport]:
        """Update an existing property analysis report."""
        db_obj = crud_property_analysis_report.get(db, report_id)
        if not db_obj:
            return None
        return crud_property_analysis_report.update(db, db_obj=db_obj, obj_in=report_in)

    def delete_report(self, db: Session, report_id: int) -> Optional[PropertyAnalysisReport]:
        """Delete a property analysis report."""
        return crud_property_analysis_report.remove(db, id=report_id)

workflow_result_service = WorkflowResultService()
