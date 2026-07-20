"""
app/services/design_job_service.py

AI HOME WIMLOGIC -- Design Studio -- V1.1D Design Job
Stage A (CREATE), Stage B (CONFIGURE), and Stage C (SUBMIT-time
validation, default resolution, Effective AI Context assembly, and
submitted_payload_json freeze) business service.

Locked lifecycle: CREATE -> CONFIGURE -> SUBMIT -> RETRY.

CHECKPOINT 7 SCOPE: this service now owns the full SUBMIT-time
validation and freeze sequence - Tool Image Requirement min/max
validation, Tool Option required-completeness validation with default
resolution, Tool Knowledge Rule application, Effective AI Context
assembly, and building/freezing the exact submitted_payload_json. It
explicitly STOPS there: Workflow Execution creation, WACP submission,
cre_design_job_executions attempt tracking, and Retry are NOT
implemented here - those remain Checkpoint 8+. submit_design_job()
transitions status 'draft' -> 'submitted' as part of freezing, which is
what makes the Configure endpoints' draft-status gate correctly reject
further edits from this point forward - this status transition is
deliberate, not a shortcut into Checkpoint 8's scope: no
cre_workflow_executions row and no cre_design_job_executions row exist
after this method returns, and no WACP call is made.

A Design Job represents persistent AI Home business intent.

LOCKED CHECKPOINT 6 CONTRACT (fulfilled here): submit_design_job()
acquires the same crud_design_job.lock_for_update() that set_images()
and set_tool_options() use, as its very first step, before any
validation, holding it for the entire validate-then-freeze sequence and
releasing only on commit or rollback - Configure and Submit serialize on
the exact same cre_design_jobs row.
"""
import json
import uuid
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy.orm import Session

from app.crud.design_job import design_job as crud_design_job
from app.crud.design_job_image import design_job_image as crud_design_job_image
from app.crud.design_tool import design_tool as crud_design_tool
from app.crud.design_tool_option import design_tool_option as crud_design_tool_option
from app.crud.design_tool_image_requirement import design_tool_image_requirement as crud_design_tool_image_requirement
from app.crud.project_property import project_property as crud_project_property
from app.crud.property import property as crud_property
from app.crud.property_image import property_image as crud_property_image

from app.schemas.design_job import DesignJobCreate, DesignJobConfigureImageItem
from app.schemas.design_job_image import DesignJobImageCreate

# Reused as-is, per the locked "do not modify payload_builder.py" boundary -
# this is an import of the existing, unmodified utility, not an extension
# of that module. normalize_json_value() is exactly the Decimal/datetime/
# UUID -> JSON-safe recursive shim this service needs for effective_context_json
# and submitted_payload_json, and duplicating it here would violate the
# "never duplicate business logic" rule just as much as not reusing it would.
from app.services.payload_builder import normalize_json_value, build_design_job_context, build_design_job_inputs, PayloadBuilderError

from app.models.design_job import DesignJob
from app.models.design_job_image import DesignJobImage
from app.models.design_tool_option import DesignToolOption
from app.models.property_image import PropertyImage


class DesignJobNotFoundError(ValueError):
    """Raised when a referenced entity (Property, Tool, Design Job) does not exist - maps to HTTP 404."""
    pass


class DesignJobValidationError(ValueError):
    """Raised for known business-rule validation failures - maps to HTTP 400."""
    pass


_VALID_OPTION_TYPES = {"select", "multiselect", "boolean", "number", "text", "slider"}


class DesignJobService:

    # ------------------------------------------------------------------
    # STAGE A - CREATE
    # ------------------------------------------------------------------

    def _generate_job_number(self) -> str:
        """
        Design Job business identifier. Distinct from Workflow Execution's
        EXE-WIM-{...} convention (see ai_orchestration_service.py) - a
        Design Job is a persistent business record, not a runtime
        execution attempt, and must never be confused with one.
        """
        return f"DSJ-WIM-{uuid.uuid4().hex[:12].upper()}"

    def create_design_job(self, db: Session, job_in: DesignJobCreate) -> DesignJob:
        """
        Validates, in order:
            1. Property exists (DesignJobNotFoundError -> 404 if not)
            2. Tool exists (DesignJobNotFoundError -> 404 if not)
            3. Tool is active (DesignJobValidationError -> 400 if not)
            4. (project_id, property_id) is a real relationship in
               cre_project_properties, via the existing, unmodified
               crud_project_property.get_multi() (DesignJobValidationError
               -> 400 if not)

        On success, snapshots tool_code/design_type/workflow_code from the
        Tool row (never trusted from the client) and creates the draft Job
        via crud_design_job.create(), which itself defaults status='draft'
        and leaves tool_options_json/effective_context_json/
        submitted_payload_json all NULL.
        """
        prop = crud_property.get(db, job_in.property_id)
        if not prop:
            raise DesignJobNotFoundError(f"Property {job_in.property_id} not found")

        tool = crud_design_tool.get(db, job_in.tool_id)
        if not tool:
            raise DesignJobNotFoundError(f"Tool {job_in.tool_id} not found")
        if tool.status != "active":
            raise DesignJobValidationError(f"Tool '{tool.tool_code}' is not active (status='{tool.status}')")

        _, relationship_count = crud_project_property.get_multi(
            db, project_id=job_in.project_id, property_id=job_in.property_id, limit=1
        )
        if relationship_count == 0:
            raise DesignJobValidationError(
                f"No relationship exists between project '{job_in.project_id}' and property {job_in.property_id}"
            )

        job_number = self._generate_job_number()
        return crud_design_job.create(
            db,
            obj_in=job_in,
            job_number=job_number,
            tool_code=tool.tool_code,
            design_type=tool.design_type,
            workflow_code=tool.workflow_code,
        )

    def get_design_job(self, db: Session, id: int) -> Optional[DesignJob]:
        return crud_design_job.get(db, id)

    def list_design_jobs(
        self, db: Session, *, skip: int = 0, limit: int = 100,
        property_id: Optional[int] = None, project_id: Optional[str] = None,
        tool_id: Optional[int] = None, status: Optional[str] = None
    ) -> Tuple[List[DesignJob], int]:
        return crud_design_job.get_multi(
            db, skip=skip, limit=limit, property_id=property_id, project_id=project_id, tool_id=tool_id, status=status
        )

    # ------------------------------------------------------------------
    # STAGE B1 - CONFIGURE SELECTED IMAGES
    # ------------------------------------------------------------------

    def _build_image_knowledge_snapshot(self, image: PropertyImage) -> Dict[str, Any]:
        """
        Exactly the fields the locked contract specifies - no mutable
        filesystem bytes, no full raw API JSON. This is a point-in-time
        business snapshot, not a live reference.
        """
        return {
            "property_image_id": image.id,
            "image_role": image.image_role,
            "notes": image.notes,
            "ai_prompt": image.ai_prompt,
            "tags": image.tags,
            "constraints": image.constraints,
            "priority": image.priority,
            "is_primary": image.is_primary,
            "status": image.status,
        }

    def set_images(
        self, db: Session, *, job_id: int, images: List[DesignJobConfigureImageItem]
    ) -> Optional[List[DesignJobImage]]:
        """
        Replaces the Design Job's entire selected-image set (never
        appends). Returns None if the Design Job does not exist (router
        maps to 404). Raises DesignJobValidationError for every known
        business-rule violation (router maps to 400):
            - Design Job not in 'draft' status
            - duplicate property_image_id values in the request
            - any requested Property Image ID that does not exist
            - any requested image belonging to a different Property than
              the Design Job's own property_id
            - any requested image that is soft-deleted

        input_role is NOT validated against PropertyImage.image_role -
        the two are intentionally independent (Design Job input context
        vs. the image's own business role). Tool Image Requirement
        min/max validation is explicitly NOT performed here - that is
        Checkpoint 7's SUBMIT-time responsibility.

        CONCURRENCY: the Design Job row is locked FOR UPDATE as the very
        first step, before the draft-status check and before any
        validation - this is the serialization boundary that makes
        Configure safe against a concurrent Submit (Checkpoint 7) racing
        on the same Job. The lock is held for the entire remainder of
        this method; it is only released when the transaction commits or
        rolls back (never released early). The actual replacement (delete
        existing rows + insert the new set) happens only AFTER all
        validation passes, as one atomic transaction using the
        Checkpoint 3 transaction-capable CRUD (commit=False on every
        write, single commit at the end, rollback on any exception) - the
        original selected-image set is guaranteed to remain unchanged if
        anything fails partway through, or if another request holds the
        lock first.
        """
        try:
            job = crud_design_job.lock_for_update(db, job_id)
            if not job:
                return None
            if job.status != "draft":
                raise DesignJobValidationError(
                    f"Design Job {job_id} is not in draft status (status='{job.status}'); images cannot be reconfigured"
                )

            requested_ids = [item.property_image_id for item in images]
            if len(requested_ids) != len(set(requested_ids)):
                raise DesignJobValidationError("Duplicate property_image_id values in the request")

            found_by_id: Dict[int, PropertyImage] = {}
            if requested_ids:
                found_images = crud_property_image.get_by_ids(db, requested_ids)
                found_by_id = {img.id: img for img in found_images}
                missing_ids = [rid for rid in requested_ids if rid not in found_by_id]
                if missing_ids:
                    raise DesignJobValidationError(f"Property Image IDs not found: {missing_ids}")
                for rid in requested_ids:
                    img = found_by_id[rid]
                    if img.property_id != job.property_id:
                        raise DesignJobValidationError(
                            f"Property Image {rid} belongs to Property {img.property_id}, "
                            f"not this Design Job's Property ({job.property_id})"
                        )
                    if img.is_deleted == 1:
                        raise DesignJobValidationError(f"Property Image {rid} is deleted and cannot be selected")

            crud_design_job_image.remove_by_design_job(db, design_job_id=job_id, commit=False)
            new_rows: List[DesignJobImage] = []
            for idx, item in enumerate(images):
                src_image = found_by_id[item.property_image_id]
                snapshot = self._build_image_knowledge_snapshot(src_image)
                obj_in = DesignJobImageCreate(
                    design_job_id=job_id,
                    property_image_id=item.property_image_id,
                    input_role=item.input_role,
                    image_knowledge_snapshot_json=snapshot,
                    display_order=idx + 1,
                )
                row = crud_design_job_image.create(db, obj_in=obj_in, commit=False)
                new_rows.append(row)
            db.commit()
            for row in new_rows:
                db.refresh(row)
            return new_rows
        except Exception:
            db.rollback()
            raise

    def get_images(self, db: Session, *, job_id: int) -> Optional[Tuple[List[DesignJobImage], int]]:
        job = crud_design_job.get(db, job_id)
        if not job:
            return None
        return crud_design_job_image.get_multi(db, design_job_id=job_id, limit=500)

    # ------------------------------------------------------------------
    # STAGE B2 - CONFIGURE TOOL OPTIONS
    # ------------------------------------------------------------------

    def _validate_option_value(self, opt: DesignToolOption, value: Any) -> None:
        option_type = opt.option_type
        allowed = opt.allowed_values_json or []

        if option_type == "select":
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                raise DesignJobValidationError(f"Option '{opt.option_code}' (select) must be a single scalar value")
            if allowed and value not in allowed:
                raise DesignJobValidationError(f"Option '{opt.option_code}' value '{value}' is not an allowed value")
        elif option_type == "multiselect":
            if not isinstance(value, list):
                raise DesignJobValidationError(f"Option '{opt.option_code}' (multiselect) must be a list")
            if allowed:
                invalid = [v for v in value if v not in allowed]
                if invalid:
                    raise DesignJobValidationError(f"Option '{opt.option_code}' contains invalid values: {invalid}")
        elif option_type == "boolean":
            if not isinstance(value, bool):
                raise DesignJobValidationError(f"Option '{opt.option_code}' (boolean) must be true or false, not a string")
        elif option_type == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise DesignJobValidationError(f"Option '{opt.option_code}' (number) must be a number")
        elif option_type == "text":
            if not isinstance(value, str):
                raise DesignJobValidationError(f"Option '{opt.option_code}' (text) must be a string")
        elif option_type == "slider":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise DesignJobValidationError(f"Option '{opt.option_code}' (slider) must be a number")
        else:
            # Defensive only - option_type is itself validated at Tool
            # Option definition time (Checkpoint 4); this should be
            # unreachable in practice.
            raise DesignJobValidationError(f"Option '{opt.option_code}' has an unrecognized option_type '{option_type}'")

    def set_tool_options(self, db: Session, *, job_id: int, tool_options: Dict[str, Any]) -> Optional[DesignJob]:
        """
        Replaces the Design Job's entire draft tool_options_json (never
        merges). Returns None if the Design Job does not exist (router
        maps to 404). Raises DesignJobValidationError (router maps to
        400) if the Job is not 'draft', if any supplied option code is
        unknown or inactive for this Tool, or if any supplied value fails
        its option_type's structural validation.

        Does NOT require every required Tool Option to be present, and
        does NOT materialize default values for options the client didn't
        supply - both are explicitly SUBMIT-time (Checkpoint 7)
        responsibilities. This method only validates what was actually
        sent.

        CONCURRENCY: the Design Job row is locked FOR UPDATE as the very
        first step, before the draft-status check and before loading Tool
        Option definitions - the same serialization boundary set_images()
        uses, so Configure Options can never commit after a concurrent
        Submit (Checkpoint 7) has already frozen the Job. The lock is
        held for the entire method and only released on commit or
        rollback. The update itself uses commit=False, with a single
        explicit commit at the end of this method - not the CRUD layer's
        default commit=True - so the lock-hold window covers the full
        validate-then-write sequence.
        """
        try:
            job = crud_design_job.lock_for_update(db, job_id)
            if not job:
                return None
            if job.status != "draft":
                raise DesignJobValidationError(
                    f"Design Job {job_id} is not in draft status (status='{job.status}'); options cannot be reconfigured"
                )

            option_defs, _ = crud_design_tool_option.get_multi(db, tool_id=job.tool_id, limit=500)
            option_by_code = {opt.option_code: opt for opt in option_defs}

            for code, value in tool_options.items():
                opt = option_by_code.get(code)
                if not opt:
                    raise DesignJobValidationError(f"Unknown Tool Option code: '{code}'")
                if opt.status != "active":
                    raise DesignJobValidationError(f"Tool Option '{code}' is not active")
                self._validate_option_value(opt, value)

            updated = crud_design_job.update(db, db_obj=job, obj_in={"tool_options_json": tool_options}, commit=False)
            db.commit()
            db.refresh(updated)
            return updated
        except Exception:
            db.rollback()
            raise

    # ------------------------------------------------------------------
    # STAGE C - SUBMIT-TIME VALIDATION, DEFAULT RESOLUTION, EFFECTIVE
    # CONTEXT ASSEMBLY, AND submitted_payload_json FREEZE
    #
    # Explicitly stops here: no Workflow Execution, no
    # cre_design_job_executions row, no WACP call. Those are Checkpoint 8.
    # ------------------------------------------------------------------

    def _validate_image_requirements(self, db: Session, *, job: DesignJob, job_images: List[DesignJobImage]) -> None:
        """
        The one point in the whole lifecycle where Tool Image Requirement
        min/max is enforced, per the locked boundary ("Tool requirement
        validation occurs at SUBMIT"). Every selected image's input_role
        must correspond to a role the Tool actually defines - an
        undefined role is rejected just as much as a missing required
        role or an over-supplied role.

        Also enforces allowed_image_roles_json - the requirement's
        constraint on which business image ROLE (not input_role) may
        satisfy it. The image's role is read ONLY from the frozen
        image_knowledge_snapshot_json["image_role"] captured at Configure
        time (Checkpoint 6) - never re-queried from the live
        PropertyImage row, so a PropertyImage.image_role change after
        Configure has no effect on Submit validation. A NULL or empty
        allowed_image_roles_json means any snapshotted image_role is
        permitted for that requirement.
        """
        requirements, _ = crud_design_tool_image_requirement.get_multi(db, tool_id=job.tool_id, limit=500)
        counts_by_role: Dict[str, int] = {}
        for img in job_images:
            counts_by_role[img.input_role] = counts_by_role.get(img.input_role, 0) + 1

        requirements_by_role = {req.input_role: req for req in requirements}
        for role in counts_by_role:
            if role not in requirements_by_role:
                raise DesignJobValidationError(
                    f"Selected images use input_role '{role}', which this Tool has no image requirement defined for"
                )

        for req in requirements:
            count = counts_by_role.get(req.input_role, 0)
            if count < req.min_count:
                raise DesignJobValidationError(
                    f"Tool requires at least {req.min_count} image(s) with input_role '{req.input_role}'; {count} selected"
                )
            if req.max_count is not None and count > req.max_count:
                raise DesignJobValidationError(
                    f"Tool allows at most {req.max_count} image(s) with input_role '{req.input_role}'; {count} selected"
                )

        for img in job_images:
            req = requirements_by_role.get(img.input_role)
            if not req:
                continue  # already rejected above; defensive no-op here
            allowed_roles = req.allowed_image_roles_json
            if not allowed_roles:
                continue  # NULL/empty = any snapshotted image_role permitted
            snapshot = img.image_knowledge_snapshot_json or {}
            snapshotted_role = snapshot.get("image_role")
            if snapshotted_role not in allowed_roles:
                raise DesignJobValidationError(
                    f"Property Image {img.property_image_id} has image_role '{snapshotted_role}' "
                    f"(from its Configure-time snapshot), which is not in the allowed image roles "
                    f"{allowed_roles} for input_role '{img.input_role}'"
                )

    def _resolve_option_default(self, opt: DesignToolOption) -> Any:
        """
        Parses cre_design_tool_options.default_value (VARCHAR(255)) into
        a properly typed JSON value according to opt.option_type. The
        column stays VARCHAR - this is a parse-at-read step, not a
        schema change. Raises DesignJobValidationError for any default
        that cannot be parsed into its declared type; an unparseable
        default is a Tool configuration error, not something to silently
        coerce or pass through as a raw string.
        """
        raw = opt.default_value
        option_type = opt.option_type

        if option_type in ("select", "text"):
            return raw

        if option_type == "boolean":
            normalized = raw.strip().lower() if isinstance(raw, str) else None
            if normalized == "true":
                return True
            if normalized == "false":
                return False
            raise DesignJobValidationError(
                f"Tool Option '{opt.option_code}' has an invalid boolean default_value '{raw}' "
                f"(must be 'true' or 'false')"
            )

        if option_type in ("number", "slider"):
            try:
                int_val = int(raw)
                # Only treat as int if the string round-trips exactly as an
                # integer literal (e.g. "10", not "10.0") - otherwise fall
                # through to float parsing below.
                if str(int_val) == raw.strip():
                    return int_val
            except (ValueError, TypeError):
                pass
            try:
                return float(raw)
            except (ValueError, TypeError):
                raise DesignJobValidationError(
                    f"Tool Option '{opt.option_code}' has a non-numeric default_value '{raw}' "
                    f"for option_type '{option_type}'"
                )

        if option_type == "multiselect":
            try:
                parsed = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                raise DesignJobValidationError(
                    f"Tool Option '{opt.option_code}' has a malformed JSON default_value '{raw}' "
                    f"for option_type 'multiselect'"
                )
            if not isinstance(parsed, list):
                raise DesignJobValidationError(
                    f"Tool Option '{opt.option_code}' default_value must parse to a JSON list "
                    f"for option_type 'multiselect', got {type(parsed).__name__}"
                )
            return parsed

        # Defensive only - option_type is validated at definition time
        # (Checkpoint 4); this should be unreachable in practice.
        raise DesignJobValidationError(
            f"Tool Option '{opt.option_code}' has an unrecognized option_type '{option_type}'"
        )

    def _resolve_tool_options(self, db: Session, *, job: DesignJob) -> Dict[str, Any]:
        """
        Starts from the current draft tool_options_json (never merged
        with anything during Configure). Every key already present is
        FULLY revalidated against the CURRENT Tool Option definitions
        BEFORE any default resolution runs:
            - unknown option_code (no longer defined by the Tool) -> reject
            - option status != 'active' (retired since Configure) -> reject
            - otherwise, its value is revalidated with _validate_option_value()
              against the CURRENT allowed_values_json/option_type (which may
              have changed since Configure was last called)

        Only once every configured key has passed does required/default
        resolution run: any active, required option the client never
        supplied resolves to its default_value via _resolve_option_default()
        (which parses the VARCHAR(255) column into a properly typed JSON
        value per option_type - a boolean default of "true" becomes the
        actual JSON value true, a number default of "10" becomes the
        actual JSON value 10, a multiselect default is parsed as a JSON
        list, etc.), or raises DesignJobValidationError if no
        default_value exists. Every resolved default is then itself run
        through _validate_option_value() before being placed into the
        resolved dict - an invalid Tool Option default (e.g. a select
        default not present in the current allowed_values_json) blocks
        Submit exactly like an invalid client-supplied value would,
        rather than being silently trusted because it came from the Tool
        definition instead of the request body.

        The configured dictionary is never rewritten until the complete
        validation above passes - a stale/invalid configured value never
        silently survives, and an inactive option is never silently
        retained either.
        """
        option_defs, _ = crud_design_tool_option.get_multi(db, tool_id=job.tool_id, limit=500)
        option_by_code = {opt.option_code: opt for opt in option_defs}
        current = dict(job.tool_options_json or {})

        for code, value in current.items():
            opt = option_by_code.get(code)
            if not opt:
                raise DesignJobValidationError(
                    f"Configured Tool Option '{code}' no longer exists on this Tool"
                )
            if opt.status != "active":
                raise DesignJobValidationError(
                    f"Configured Tool Option '{code}' is no longer active"
                )
            self._validate_option_value(opt, value)

        for opt in option_defs:
            if opt.option_code in current:
                continue
            if opt.is_required == 1 and opt.status == "active":
                if opt.default_value is not None:
                    resolved_default = self._resolve_option_default(opt)
                    self._validate_option_value(opt, resolved_default)
                    current[opt.option_code] = resolved_default
                else:
                    raise DesignJobValidationError(
                        f"Required Tool Option '{opt.option_code}' is missing and has no default_value"
                    )

        return current

    def submit_design_job(self, db: Session, *, job_id: int) -> Optional[DesignJob]:
        """
        Full SUBMIT-time validation and freeze sequence. Returns None if
        the Design Job does not exist (router maps to 404). Raises
        DesignJobValidationError for every known business-rule violation
        (router maps to 400): not in draft status, invalid Project/
        Property relationship, Tool Image Requirement violations
        (including allowed_image_roles_json), stale/invalid/missing Tool
        Options, or a required Knowledge Rule scope that has no data to
        satisfy it.

        Effective AI Context assembly is delegated to
        app.services.payload_builder.build_design_job_context() - this
        method remains the lifecycle/orchestration owner (lock -> validate
        relationship -> validate images -> resolve Tool Options -> call
        payload_builder -> normalize -> freeze -> commit), while
        payload_builder.py owns the actual context-assembly business
        logic, per the locked architecture. PayloadBuilderError raised by
        that function is caught here and translated into
        DesignJobValidationError, exactly as build_enterprise_payload()'s
        own callers already do elsewhere in this codebase.

        Selected Image MEDIA INPUT assembly (a separate contract from
        Effective AI Context - "what image should the workflow process"
        vs. "what context should the model know about it") is likewise
        delegated to payload_builder.build_design_job_inputs(), and its
        PayloadBuilderError is translated the same way. inputs.images is
        never gated by Tool Knowledge Rules - every selected DesignJobImage
        is unconditionally a processing input.

        On success, freezes tool_options_json (with defaults resolved),
        effective_context_json, and submitted_payload_json, and
        transitions status 'draft' -> 'submitted' - all in the ONE
        transaction that began with the Design Job row lock, so Configure
        can never race this method (see the Checkpoint 6 lock contract
        fulfilled here).

        Deliberately STOPS after the freeze: no cre_workflow_executions
        row, no cre_design_job_executions row, and no WACP call happen in
        this method - that is Checkpoint 8's responsibility, continuing
        from a Job that is already status='submitted' with a fully frozen
        submitted_payload_json. Checkpoint 8 must NOT rebuild
        submitted_payload_json - it is already frozen by this method.
        """
        try:
            job = crud_design_job.lock_for_update(db, job_id)
            if not job:
                return None
            if job.status != "draft":
                raise DesignJobValidationError(
                    f"Design Job {job_id} is not in draft status (status='{job.status}'); it cannot be submitted"
                )

            # Tool active revalidation: the draft's snapshotted tool_code/
            # design_type/workflow_code are NEVER overwritten here - only
            # the CURRENT Tool row's status gates whether processing may
            # begin. A Tool may be deactivated (not deleted) after a Draft
            # was created against it; Submit must catch that, since
            # deactivation is the Tool Box's documented alternative to
            # deletion for a referenced Tool.
            current_tool = crud_design_tool.get(db, job.tool_id)
            if not current_tool:
                raise DesignJobValidationError(f"Tool {job.tool_id} no longer exists")
            if current_tool.status != "active":
                raise DesignJobValidationError(
                    f"Tool '{job.tool_code}' is not active (status='{current_tool.status}'); Design Job cannot be submitted"
                )

            _, relationship_count = crud_project_property.get_multi(
                db, project_id=job.project_id, property_id=job.property_id, limit=1
            )
            if relationship_count == 0:
                raise DesignJobValidationError(
                    f"No relationship exists between project '{job.project_id}' and property {job.property_id}"
                )

            job_images, _ = crud_design_job_image.get_multi(db, design_job_id=job_id, limit=500)

            self._validate_image_requirements(db, job=job, job_images=job_images)
            resolved_tool_options = self._resolve_tool_options(db, job=job)

            try:
                effective_context = build_design_job_context(db, job=job, job_images=job_images)
            except PayloadBuilderError as e:
                raise DesignJobValidationError(str(e))

            try:
                design_job_inputs = build_design_job_inputs(db, property_id=job.property_id, job_images=job_images)
            except PayloadBuilderError as e:
                raise DesignJobValidationError(str(e))

            effective_context = normalize_json_value(effective_context)
            resolved_tool_options = normalize_json_value(resolved_tool_options)
            design_job_inputs = normalize_json_value(design_job_inputs)

            # --- AI HOME Knowledge Inheritance V1.0 (Step 5) ---------------
            # Additive only, per inheritance_04_backend_implementation.md
            # §12.10's "Compatibility With Current Stored Shape": every
            # existing top-level key below (job_number, tool_code,
            # design_type, workflow_code, project_id, property_id, inputs,
            # tool_options, effective_context) is preserved EXACTLY as it
            # was before this step - confirmed via direct audit that
            # design_job_execution_service.py's _validate_media_url_
            # compatibility() reads submitted_payload_json.inputs.images
            # directly, and that legacy top-level "tool_options" has no
            # other real structural consumer today but is nonetheless kept
            # as the explicitly-required compatibility alias for
            # request_context.tool_options (§12.10) rather than removed.
            #
            # workflow_code stays exactly where it already lives (payload
            # root) - it is NOT moved into business_intent, request_context,
            # or effective_context (inheritance_03 §17.2/§17.4, SP-004).
            #
            # design_style is promoted from the resolved Tool Options into
            # request_context.design_style when present (inheritance_03
            # Decision 3 / SP-006), and left None when the Tool has no such
            # option (SP-007) - Design Style itself remains stored as an
            # ordinary Tool Option; no new column or table is introduced.
            #
            # Knowledge Inheritance Engine Phase 1.2A - final architecture
            # correction: tool_intent is now the canonical key for this
            # object; business_intent is retained as a byte-identical,
            # temporary backward-compatible alias (both built from the
            # SAME dict literal below, never two independently-constructed
            # objects that could drift apart). Removal of the legacy
            # business_intent alias requires its own, separately-approved
            # deprecation phase - not done here. This AIHOME-internal
            # object (a rich Tool/business-context dict, living inside
            # `data`/submitted_payload_json) must never be confused with
            # WACP's own envelope-level `business_intent` field (a plain
            # Optional[str] routing key, living OUTSIDE this payload
            # entirely, matched by DEV-TOOLS' WIM Module V1 against a
            # registered workflow_code) - the two share a name and nothing
            # else; this payload's business_intent/tool_intent keys are
            # never read by anything that builds or interprets the WACP
            # envelope itself.
            EFFECTIVE_CONTEXT_SCHEMA_VERSION = "1.2.0"

            payload_contract_block = {
                "name": "aihome.design_job",
                "version": "1.1",
                "effective_context_version": EFFECTIVE_CONTEXT_SCHEMA_VERSION,
            }
            tool_intent_block = {
                "tool_code": job.tool_code,
                "tool_name": current_tool.tool_name,
                "design_type": job.design_type,
                "business_purpose": current_tool.business_purpose,
                "business_instructions": current_tool.business_instructions,
            }
            request_context_block = {
                "design_style": resolved_tool_options.get("design_style"),
                "tool_options": resolved_tool_options,
                "additional_instructions": None,
                "requested_deliverables": [],
            }
            metadata_block = {
                "design_job_id": job.id,
                "project_id": job.project_id,
                "property_id": job.property_id,
                "tool_id": job.tool_id,
                "selected_image_count": len(job_images),
                "created_from": "AI_HOME_DESIGN_STUDIO",
            }

            effective_context["context_schema_version"] = EFFECTIVE_CONTEXT_SCHEMA_VERSION

            submitted_payload = normalize_json_value({
                "job_number": job.job_number,
                "tool_code": job.tool_code,
                "design_type": job.design_type,
                "workflow_code": job.workflow_code,
                "project_id": job.project_id,
                "property_id": job.property_id,
                "inputs": design_job_inputs,
                "tool_options": resolved_tool_options,
                "effective_context": effective_context,
                "payload_contract": payload_contract_block,
                "tool_intent": tool_intent_block,
                "business_intent": tool_intent_block,
                "request_context": request_context_block,
                "metadata": metadata_block,
            })

            updated = crud_design_job.update(
                db,
                db_obj=job,
                obj_in={
                    "tool_options_json": resolved_tool_options,
                    "effective_context_json": effective_context,
                    "submitted_payload_json": submitted_payload,
                    "status": "submitted",
                },
                commit=False,
            )
            db.commit()
            db.refresh(updated)
            return updated
        except Exception:
            db.rollback()
            raise


design_job_service = DesignJobService()
