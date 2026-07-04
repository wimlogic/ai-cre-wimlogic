# Import all the models so that Base has them registered before
# importing by Alembic/migration utilities.
from app.db.database import Base  # noqa
from app.models.project import Project  # noqa
from app.models.property import Property  # noqa
from app.models.project_property import ProjectProperty  # noqa
from app.models.property_image import PropertyImage  # noqa
from app.models.scan_job import ScanJob  # noqa
from app.models.scan import Scan  # noqa
from app.models.scan_property import ScanProperty  # noqa
from app.models.workflow_execution import WorkflowExecution  # noqa
from app.models.workflow_result import WorkflowResult  # noqa
from app.models.workflow_event import WorkflowEvent  # noqa
from app.models.result_section import ResultSection  # noqa
from app.models.renovation_scenario import RenovationScenario  # noqa
from app.models.property_analysis_report import PropertyAnalysisReport  # noqa
from app.models.concept_design import ConceptDesign  # noqa
from app.models.generated_asset import GeneratedAsset  # noqa
from app.models.estimate import Estimate  # noqa
from app.models.zoning_note import ZoningNote  # noqa
from app.models.api_usage_log import ApiUsageLog  # noqa

