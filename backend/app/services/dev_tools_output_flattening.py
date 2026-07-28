"""
app/services/dev_tools_output_flattening.py

Shared by result_sync.py and business_report_builder.py. Extracted to its
own module specifically to avoid a circular import between the two (both
need it; neither should import from the other).

This is the ONE place in the entire AIHOME backend that reads DEV-TOOLS'
WIM Module V2 `workflows` structure. Only `workflows` (an array, read
purely to iterate) and each workflow's own `outputs` (also an array) are
ever read here - `role`, `workflow_code`, `execution_order`,
`execution_mode`, `workflow_template_id`, and `workflow_run_id` are never
read, not here and not anywhere downstream. AIHOME's business records
(PropertyAnalysisReport, and any future DesignReport / RenovationPlan /
ContractorPackage) are built entirely from output CONTENT, never from
DEV-TOOLS' own orchestration structure - per the architecture boundary:
DEV-TOOLS is the AI Orchestration Platform, AIHOME is the Business
Application, and AIHOME understands only Job / Job History / Business
Data / Business Report.
"""

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def flatten_dev_tools_outputs(result_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Normalizes a DEV-TOOLS terminal result into a single flat list of
    `{"output_type", "title", "content"}` records (each optionally
    carrying a `"business_intent"` key when the source result identifies
    one - see WACP 1.1 handling below), regardless of which of the
    result shapes DEV-TOOLS returns:

    1. Legacy flat shape: `result_data["outputs"]` already IS the flat
       list - returned as-is (WACP 1.0, single intent, unchanged).

    2. WIM Module V2 nested-workflows shape: one entry in
       `result_data["outputs"]` has `output_type == "json"` and content
       that parses to a dict containing a `workflows` list
       (`{"wim_module_version", "entry_workflow_run_id", "workflows": [...]}`).
       That wrapper entry is never itself a candidate business result -
       its OWN `workflows[].outputs[]` entries are unwrapped and yielded
       in its place instead.

    3. WACP 1.1 multi-Business-Intent shape (backend/wacp/WACP_PROTOCOL_1_1.md):
       a terminal result may instead carry `combined_outputs` and/or
       `workflow_results` at the top level, alongside a backward-compatible
       `outputs` alias. Preference order when more than one is present:

         a. `combined_outputs`, if present and non-empty - preferred
            because the spec states these items "identify their Business
            Intent, workflow code, and Workflow Run" (richer provenance
            than the `outputs` alias), which is exactly what AIHOME needs
            to "display combined workflow results appropriately" (per the
            RC2 upgrade requirements) - each contributing item's own
            `business_intent` field (if present) is preserved onto the
            flattened output's `business_intent` key.
         b. `workflow_results`, if `combined_outputs` is absent/empty -
            "one result per top-level Business Intent" per the spec. Each
            item is treated defensively: if it carries its own nested
            `outputs` list, those are unwrapped (tagged with that item's
            own `business_intent`, if present); otherwise the item itself
            is treated as a single output candidate.
         c. `outputs` (the documented backward-compatible alias) -
            handled by falling through to path 1/2 above, since by
            definition it carries "the historical output collection" in
            the same shape AIHOME already knows how to flatten.

       NEITHER of the uploaded WACP 1.1 documents gives an exact,
       byte-level field schema for `combined_outputs[i]` or
       `workflow_results[i]` (only prose describing what they contain) -
       this function is deliberately defensive rather than assuming a
       rigid schema: missing fields are skipped, not fatal, and this
       should be revalidated against a real DEV-TOOLS WACP 1.1 response
       once available.

    This is the ONE place in the entire AIHOME backend that reads any of
    DEV-TOOLS' orchestration-shaped result structures (`workflows`,
    `combined_outputs`, `workflow_results`). Only these arrays themselves
    (read purely to iterate) and each item's own `business_intent` (a
    plain routing label, not orchestration metadata - AIHOME already
    sends this same value on submission) are ever read here - `role`,
    `workflow_code`, `execution_order`, `execution_mode`,
    `workflow_template_id`, and `workflow_run_id` are never read, not
    here and not anywhere downstream. AIHOME's business records
    (PropertyAnalysisReport, and any future DesignReport / RenovationPlan /
    ContractorPackage) are built entirely from output CONTENT, never from
    DEV-TOOLS' own orchestration structure - per the architecture
    boundary: DEV-TOOLS is the AI Orchestration Platform, AIHOME is the
    Business Application, and AIHOME understands only Job / Job History /
    Business Data / Business Report.

    A non-list `outputs`, a malformed/unparseable wrapper content
    string, or a workflow entry with no `outputs` list of its own is
    skipped with a warning rather than raising - one malformed entry
    must never prevent every other output in the same job from being
    recognized.
    """
    combined_outputs = result_data.get("combined_outputs")
    if isinstance(combined_outputs, list) and combined_outputs:
        return _flatten_combined_outputs(combined_outputs)

    workflow_results = result_data.get("workflow_results")
    if isinstance(workflow_results, list) and workflow_results:
        return _flatten_workflow_results(workflow_results)

    raw_outputs = result_data.get("outputs")
    if not isinstance(raw_outputs, list):
        return []

    flattened: List[Dict[str, Any]] = []
    for output in raw_outputs:
        if not isinstance(output, dict):
            continue

        content = output.get("content")
        parsed_content: Any = None
        if isinstance(content, str):
            try:
                parsed_content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                parsed_content = None

        is_wim_v2_wrapper = isinstance(parsed_content, dict) and isinstance(parsed_content.get("workflows"), list)

        # Agent-run output wrapper, confirmed against a real IMAGE_DESIGN
        # result: some agents (this Design Studio pipeline observed) wrap
        # their real payload one level deeper, as
        # `{"output": "<json string>", "agent_run_id": "<uuid>"}` -
        # `content` parses successfully, but the business fields
        # (design_images, executive_summary, etc.) live inside the
        # STRING value of `output`, requiring a second json.loads(), not
        # inside `parsed_content` directly. Detected narrowly (an
        # `output` key whose value is itself a string that parses to a
        # dict) so a genuinely different, unrelated top-level `output`
        # key is never misinterpreted.
        is_agent_run_wrapper = False
        if not is_wim_v2_wrapper and isinstance(parsed_content, dict):
            inner_output = parsed_content.get("output")
            if isinstance(inner_output, str):
                try:
                    inner_parsed = json.loads(inner_output)
                    if isinstance(inner_parsed, dict):
                        is_agent_run_wrapper = True
                except (json.JSONDecodeError, TypeError):
                    pass

        if is_agent_run_wrapper:
            # Unwrap one level: this output's real content is the INNER
            # json string, not the {"output": ..., "agent_run_id": ...}
            # wrapper string. Downstream consumers (business_report_builder,
            # design_result_service.ingest_image_design_results) never
            # need to know this unwrap happened - they just see a normal
            # {"output_type", "title", "content"} record whose content
            # already IS the real payload.
            flattened.append({
                "output_type": output.get("output_type", "json"),
                "title": output.get("title"),
                "content": parsed_content["output"],
            })
            continue

        if not is_wim_v2_wrapper:
            flattened.append(output)
            continue

        for workflow in parsed_content["workflows"]:
            if not isinstance(workflow, dict):
                continue
            nested_outputs = workflow.get("outputs")
            if not isinstance(nested_outputs, list):
                continue
            for nested_output in nested_outputs:
                if not isinstance(nested_output, dict):
                    continue
                flattened.append({
                    "output_type": nested_output.get("output_type", "json"),
                    "title": nested_output.get("title"),
                    "content": nested_output.get("content"),
                })

    return flattened


def _flatten_combined_outputs(combined_outputs: List[Any]) -> List[Dict[str, Any]]:
    """
    Flattens a WACP 1.1 `combined_outputs` array. Each item is expected
    to be output-shaped (`output_type`/`title`/`content`, the same
    convention every other AIHOME output-consuming path already uses)
    plus an optional `business_intent` provenance field - see the
    defensive-assumption note on flatten_dev_tools_outputs above. An
    item missing `content` entirely is skipped (nothing to classify),
    logged as a warning rather than raising.
    """
    flattened: List[Dict[str, Any]] = []
    for item in combined_outputs:
        if not isinstance(item, dict):
            continue
        if "content" not in item:
            logger.warning("Skipping a combined_outputs entry with no 'content' field: keys=%s", list(item.keys()))
            continue
        entry = {
            "output_type": item.get("output_type", "json"),
            "title": item.get("title"),
            "content": item.get("content"),
        }
        if item.get("business_intent") is not None:
            entry["business_intent"] = item["business_intent"]
        flattened.append(entry)
    return flattened


def _flatten_workflow_results(workflow_results: List[Any]) -> List[Dict[str, Any]]:
    """
    Flattens a WACP 1.1 `workflow_results` array ("one result per
    top-level Business Intent"). Each item is checked, defensively, for
    its own nested `outputs` list to unwrap (tagged with that item's own
    `business_intent` when present); an item with no such list but with
    its own `content` is treated as a single output candidate directly.
    See the defensive-assumption note on flatten_dev_tools_outputs above.

    Per AIHOME_IMAGE_DESIGN_OUTPUT_SPEC.md's "Selecting the IMAGE_DESIGN
    Workflow Result" section: only an entry whose OWN `status` is
    "COMPLETED" is processed - an entry the plan resolved to SKIPPED, or
    one that itself FAILED, must never have its outputs treated as valid
    business content, even if that content happens to be well-formed
    JSON. Its `reason` (if present) is logged so a skipped/failed intent
    in a multi-intent job is visible in AIHOME's own logs, not silently
    dropped.
    """
    flattened: List[Dict[str, Any]] = []
    for item in workflow_results:
        if not isinstance(item, dict):
            continue

        item_status = item.get("status")
        if item_status is not None and item_status != "COMPLETED":
            logger.info(
                "Skipping workflow_results entry (business_intent=%s, workflow_code=%s) "
                "with status=%s (reason=%s) - only COMPLETED entries are processed.",
                item.get("business_intent"), item.get("workflow_code"), item_status, item.get("reason"),
            )
            continue

        item_business_intent = item.get("business_intent")

        nested_outputs = item.get("outputs")
        if isinstance(nested_outputs, list):
            for nested in nested_outputs:
                if not isinstance(nested, dict) or "content" not in nested:
                    continue
                entry = {
                    "output_type": nested.get("output_type", "json"),
                    "title": nested.get("title"),
                    "content": nested.get("content"),
                }
                if item_business_intent is not None:
                    entry["business_intent"] = item_business_intent
                flattened.append(entry)
            continue

        if "content" in item:
            entry = {
                "output_type": item.get("output_type", "json"),
                "title": item.get("title"),
                "content": item.get("content"),
            }
            if item_business_intent is not None:
                entry["business_intent"] = item_business_intent
            flattened.append(entry)
        else:
            logger.warning(
                "Skipping a workflow_results entry with neither its own 'outputs' list "
                "nor a 'content' field: keys=%s", list(item.keys()),
            )
    return flattened
