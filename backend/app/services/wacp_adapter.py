"""
AI-CRE WIMLOGIC V1 -- Phase 1A-BE WACP Client SDK Integration

services/wacp_adapter.py

Thin adapter around the official WACP Client SDK (wacp.client.WacpClient).
This is the ONLY module in AI-CRE permitted to import wacp.client or
wacp.core directly. Every other module - ai_orchestration_service.py today,
any future caller after it - talks to this adapter's five functions
(submit_payload, get_job_status, get_job_results, cancel_job, retry_job)
and never touches the SDK, a WacpClient instance, or a WacpResponse object
itself. This is what keeps AI-CRE's business logic portable to any future
WACP-compliant server: swapping servers means repointing WACP_* settings,
not rewriting a caller. This module - not any specific server - is what
"integrating with WACP" means for the rest of AI-CRE.

Named after the protocol, not the server: DEV-TOOLS WIMLOGIC is simply the
WACP-compliant server this deployment happens to point at today.

This module owns:
    - Lazily constructing exactly one WacpClient from application settings
    - Translating this adapter's plain-dict calling convention into the
      SDK's typed submit()/get_status()/get_results()/cancel()/retry()
      calls
    - Translating SDK exceptions (wacp.client.http's HttpError family and
      wacp.core.errors's WacpError family) into AI-CRE's existing
      DevToolsClientError family, so callers written against the old
      hand-rolled client require no exception-handling changes

This module owns NO protocol logic of its own: it never constructs a WACP
envelope, computes a request_id/timestamp, builds an auth header, or
interprets a WACP-xxx error code table - the SDK does all of that
(20_WACP_SDK_ARCHITECTURE.md §1.4: "A Business Application never manually
constructs a WACP envelope..."). It also performs no database access and
contains no business rules - it is a pure transport-and-translation layer.
Mapping a WACP job status onto AI-CRE's own local execution-status
vocabulary is deliberately NOT done here (see `_normalize()`) - that is a
business decision left to ai_orchestration_service.py, which already owns
local status semantics.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from wacp.client.client import WacpClient
from wacp.client.config import ClientConfig
from wacp.client.http import HttpError as _SdkHttpError
from wacp.core.dto import WacpResponse
from wacp.core.enums import Priority
from wacp.core.errors import WacpError as _SdkWacpError

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
#
# Names and hierarchy unchanged from the pre-adapter hand-rolled client, so
# every existing `except ...DevToolsClientError` call site continues to
# work without modification. DevToolsConfigurationError is new - a failure
# category the old client never needed, since it never validated
# credentials before attempting a request.
# ---------------------------------------------------------------------------


class DevToolsClientError(Exception):
    """Base exception for all WACP adapter failures."""


class DevToolsConnectionError(DevToolsClientError):
    """Raised when the WACP server cannot be reached (network/timeout failure)."""


class DevToolsResponseError(DevToolsClientError):
    """Raised when the WACP server returns a protocol-level error response
    (a well-formed WacpResponse whose `error` field is populated)."""


class DevToolsConfigurationError(DevToolsClientError):
    """Raised when required WACP configuration (base URL, application id,
    API key/secret) is missing or invalid. Never raised mid-request - only
    when the client is first constructed, so a misconfigured deployment
    fails clearly on the first actual WACP call rather than with an
    obscure downstream error."""


# ---------------------------------------------------------------------------
# Lazy client construction
# ---------------------------------------------------------------------------

_client: Optional[WacpClient] = None


def _get_client() -> WacpClient:
    """
    Returns the single, lazily-constructed WacpClient for this process.

    Built on first use, never at import time: this module is imported at
    application startup (ai_orchestration_service.py -> the API router ->
    main.py), and WACP_* settings are legitimately empty in a
    freshly-deployed, not-yet-configured AI-CRE instance (AI-CRE is an
    open-source, single-workspace application - see core/config.py).
    Failing at import time would crash the entire backend before an
    operator ever gets a chance to fill in .env; failing only when a WACP
    call is actually attempted, with a clear DevToolsConfigurationError, is
    the correct failure mode.

    `default_company_id` is set once here from WACP_COMPANY_ID - pure WACP
    transport metadata (see core/config.py), never a per-request lookup
    against any AI-CRE business table, since AI-CRE has no Company/Tenant
    entity of its own.
    """
    global _client
    if _client is not None:
        return _client

    if not settings.WACP_BASE_URL:
        raise DevToolsConfigurationError(
            "WACP_BASE_URL is not configured. Set WACP_BASE_URL, "
            "WACP_APPLICATION_ID, WACP_API_KEY, and WACP_API_SECRET "
            "before submitting or polling Enterprise Jobs."
        )

    try:
        config = ClientConfig(
            base_url=settings.WACP_BASE_URL,
            application_id=settings.WACP_APPLICATION_ID,
            api_key=settings.WACP_API_KEY,
            api_secret=settings.WACP_API_SECRET,
            timeout_seconds=float(settings.WACP_TIMEOUT_SECONDS),
            verify_ssl=False,
        )
    except ValueError as exc:
        # ClientConfig validates its own inputs (empty fields, a base_url
        # that isn't "https://", a non-positive timeout, etc.) and raises
        # plain ValueError for configuration problems (wacp/client/config.py)
        # - not a WACP protocol error, so it is translated here rather than
        # left to propagate as a bare ValueError this adapter's callers
        # wouldn't expect.
        raise DevToolsConfigurationError(
            f"Invalid WACP client configuration: {exc}"
        ) from exc

    _client = WacpClient(config, default_company_id=settings.WACP_COMPANY_ID)
    logger.info(
        "WACP client initialized for application_id=%s base_url=%s",
        settings.WACP_APPLICATION_ID,
        settings.WACP_BASE_URL,
    )
    return _client


def reset_client() -> None:
    """Discards the cached WacpClient so the next call rebuilds it from
    current settings. Test-only escape hatch (e.g. reconfiguring WACP_*
    between test cases) - normal request handling never needs this."""
    global _client
    _client = None


# ---------------------------------------------------------------------------
# Priority conversion
# ---------------------------------------------------------------------------

_VALID_PRIORITIES = {p.value for p in Priority}


def _to_priority(priority: Optional[str]) -> Priority:
    """
    Converts AI-CRE's plain-string priority (e.g. "Normal", "High", "Low")
    into the SDK's typed Priority enum. Case-insensitive; falls back to
    Priority.NORMAL (logging a warning) for an empty or unrecognized value
    rather than raising - an unrecognized priority string is not reason
    enough to fail an otherwise-valid submission.
    """
    candidate = (priority or "NORMAL").strip().upper()
    if candidate not in _VALID_PRIORITIES:
        logger.warning("Unrecognized priority '%s'; defaulting to NORMAL.", priority)
        return Priority.NORMAL
    return Priority(candidate)


# ---------------------------------------------------------------------------
# Response translation
# ---------------------------------------------------------------------------


def _normalize(response: WacpResponse) -> Dict[str, Any]:
    """
    Translates a WacpResponse (wacp.core.dto) into this adapter's stable,
    plain-dict shape:

        {"job_id": ..., "status": ..., "result": ..., "raw_response": ...}

    This is the one place in AI-CRE that reads WacpResponse's structure
    (response.wacp.job_id, response.status, response.result). Every caller
    elsewhere reads this normalized shape instead - exactly the same
    contract the pre-adapter hand-rolled client exposed, only the
    internals changed to match WACP's actual response shape (the job
    reference lives at `wacp.job_id`, not a flat top-level `job_id`/`id`).

    `status` is returned as the raw WACP status string (e.g. "RUNNING",
    "COMPLETED") - deliberately un-translated. Mapping WACP's job states
    onto AI-CRE's own local execution-status vocabulary is a business
    decision that belongs to ai_orchestration_service.py; this adapter
    only ever reports protocol truth.

    `raw_response` carries `response.result` (the business result payload,
    populated only once `status == COMPLETED`, per §14.2) - the same thing
    this key was always intended to carry, now read from the correct
    field. Left as an empty dict rather than None when absent, so existing
    callers that do `results_response["raw_response"]` without a None
    check keep working unchanged.
    """
    return {
        "job_id": response.wacp.job_id if response.wacp else None,
        "status": response.status.value if response.status is not None else None,
        "result": response.result,
        "raw_response": response.result or {},
    }


def _invoke(action: str, call: Callable[[], WacpResponse]) -> Dict[str, Any]:
    """
    Shared call/translate wrapper used by every public function below:
    invokes one SDK call and translates any SDK exception into this
    adapter's stable DevToolsClientError family. `action` is a short,
    human-readable phrase used only in the resulting error message (e.g.
    "submitting job", "polling status for job JOB-0001056").
    """
    try:
        response = call()
    except _SdkHttpError as exc:
        raise DevToolsConnectionError(
            f"Failed to reach the WACP server while {action}: {exc}"
        ) from exc
    except _SdkWacpError as exc:
        raise DevToolsResponseError(
            f"WACP server returned an error while {action} ({exc.error_code.code}): {exc.message}"
        ) from exc
    return _normalize(response)


# ---------------------------------------------------------------------------
# Public adapter interface
#
# Every function below is a direct, one-line delegation to the
# corresponding WacpClient method, wrapped only in _invoke()'s exception
# translation - no protocol logic, no HTTP logic, no business logic, and
# no database access, per the adapter's single responsibility.
# ---------------------------------------------------------------------------


def submit_payload(
    data: Dict[str, Any],
    *,
    workflow_code: str,
    project_code: str,
    priority: str = "NORMAL",
    correlation_id: Optional[str] = None,
    callback_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Submits a new Enterprise Job. `data` is the WACP envelope's `data`
    block, as built by payload_builder.build_enterprise_payload(). Every
    other envelope field is either supplied here explicitly by the caller
    (`workflow_code`, `project_code`, `priority`, `correlation_id`,
    `callback_url`) or filled in automatically by the SDK from
    configuration (`application_id`, `company_id` default, `request_id`,
    `timestamp`) - this function never constructs any of that itself.

    `callback_url` defaults to None: AI-CRE does not yet register a
    callback endpoint with signature verification (10_WACP_PROTOCOL.md
    §17.3), so Phase 1A-BE relies on polling (get_job_status) rather than
    callbacks. Passing one through here is supported for when that changes.

    Returns the normalized shape (see `_normalize()`); `job_id` there is
    the value to persist as WorkflowExecution.devtools_execution_id.
    """
    client = _get_client()
    return _invoke(
        f"submitting job (workflow_code={workflow_code})",
        lambda: client.submit(
            workflow_code=workflow_code,
            data=data,
            project_code=project_code,
            priority=_to_priority(priority),
            correlation_id=correlation_id,
            callback_url=callback_url,
        ),
    )


def get_job_status(job_id: str) -> Dict[str, Any]:
    """Lightweight status check for an existing job (no `result` payload
    transferred). Returns the normalized shape (see `_normalize()`)."""
    client = _get_client()
    return _invoke(
        f"polling status for job {job_id}", lambda: client.get_status(job_id)
    )


def get_job_results(job_id: str) -> Dict[str, Any]:
    """Retrieves a job's completed result. Returns the normalized shape
    (see `_normalize()`); `raw_response` carries the business result
    content once the job has reached COMPLETED."""
    client = _get_client()
    return _invoke(
        f"retrieving results for job {job_id}", lambda: client.get_results(job_id)
    )


def cancel_job(job_id: str) -> Dict[str, Any]:
    """Requests cancellation of a non-terminal job. Returns the normalized
    shape (see `_normalize()`)."""
    client = _get_client()
    return _invoke(f"cancelling job {job_id}", lambda: client.cancel(job_id))


def retry_job(job_id: str) -> Dict[str, Any]:
    """Creates a new job from a FAILED or CANCELLED job's original
    envelope. Returns the normalized shape (see `_normalize()`); the
    returned `job_id` is a NEW job id, distinct from the one passed in."""
    client = _get_client()
    return _invoke(f"retrying job {job_id}", lambda: client.retry(job_id))
