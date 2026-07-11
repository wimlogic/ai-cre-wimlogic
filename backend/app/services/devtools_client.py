"""
AI-CRE WIMLOGIC V1 -- Phase 4 DEV-TOOLS Integration

devtools_client.py

Thin REST client for the external DEV-TOOLS WIMLOGIC AI Workflow
Orchestrator. This module's only responsibility is transporting JSON over
HTTP to/from DEV-TOOLS - it contains no orchestration logic, no database
access, and never communicates with Workflow Runtime, Agent Execution, or
AI Providers directly (those are exclusively DEV-TOOLS' responsibility).

Responsibilities (Single Responsibility Principle):
    - submit_payload()    POST  a built Enterprise Payload, returns the job reference
    - get_job_status()    GET   current status for a DEV-TOOLS job
    - get_job_results()   GET   completed result JSON for a DEV-TOOLS job
    - cancel_job()        POST  a cancellation request for a queued/running job

Follows the same sync `httpx` + typed-exception conventions already used in
services/property_image_import_service.py, rather than introducing a new
HTTP style.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DevToolsClientError(Exception):
    """Base exception for all DEV-TOOLS REST client failures."""


class DevToolsConnectionError(DevToolsClientError):
    """Raised when DEV-TOOLS cannot be reached (network/timeout failure)."""


class DevToolsResponseError(DevToolsClientError):
    """Raised when DEV-TOOLS responds with a non-2xx HTTP status."""


def _headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.DEVTOOLS_API_KEY:
        headers["Authorization"] = f"Bearer {settings.DEVTOOLS_API_KEY}"
    return headers


def _request(method: str, path: str, *, json_body: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Shared low-level request helper. Not part of the public single-purpose
    API (submit_payload/get_job_status/get_job_results/cancel_job) - just
    factors out the repeated httpx call/error-handling boilerplate.
    """
    url = f"{settings.DEVTOOLS_API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"

    try:
        response = httpx.request(
            method,
            url,
            json=json_body,
            headers=_headers(),
            timeout=settings.DEVTOOLS_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("DEV-TOOLS returned HTTP error for %s %s: %s", method, url, exc)
        raise DevToolsResponseError(
            f"DEV-TOOLS returned an error status for {method} {path}: {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        logger.error("DEV-TOOLS request failed for %s %s: %s", method, url, exc)
        raise DevToolsConnectionError(f"Failed to reach DEV-TOOLS at '{url}': {exc}") from exc

    if not response.content:
        return {}

    try:
        return response.json()
    except ValueError as exc:
        logger.error("DEV-TOOLS returned non-JSON response for %s %s: %s", method, url, exc)
        raise DevToolsResponseError(f"DEV-TOOLS returned a non-JSON response for {method} {path}") from exc


def _normalize(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wraps any raw DEV-TOOLS response into one consistent internal shape:

        {"job_id": ..., "status": ..., "raw_response": {...raw...}}

    This is the only place in AI-CRE that reads DEV-TOOLS' exact response
    keys. Every caller elsewhere (ai_orchestration_service, result_sync)
    reads this normalized shape instead, so if DEV-TOOLS' actual field
    names change, only this function needs updating.

    Accepts either `job_id` or `id` for the job reference until the
    DEV-TOOLS API contract is finalized.
    """
    return {
        "job_id": raw.get("job_id") or raw.get("id"),
        "status": raw.get("status"),
        "raw_response": raw,
    }


def submit_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Submits a built Enterprise Payload (from payload_builder.build_enterprise_payload)
    to DEV-TOOLS for execution. Returns the normalized internal response
    shape - see `_normalize()`.
    """
    logger.info(
        "Submitting payload to DEV-TOOLS (workflow_intent=%s)",
        payload.get("header", {}).get("workflow_intent", "unknown"),
    )
    raw = _request("POST", "/jobs", json_body=payload)
    return _normalize(raw)


def get_job_status(devtools_job_id: str) -> Dict[str, Any]:
    """Returns the normalized internal response shape for a DEV-TOOLS job's
    current status - see `_normalize()`."""
    raw = _request("GET", f"/jobs/{devtools_job_id}/status")
    return _normalize(raw)


def get_job_results(devtools_job_id: str) -> Dict[str, Any]:
    """Returns the normalized internal response shape for a DEV-TOOLS job's
    completed results - see `_normalize()`. The full results payload is
    always available under `raw_response` regardless of top-level shape."""
    raw = _request("GET", f"/jobs/{devtools_job_id}/results")
    return _normalize(raw)


def cancel_job(devtools_job_id: str) -> Dict[str, Any]:
    """Requests cancellation of a queued or running DEV-TOOLS job. Returns
    the normalized internal response shape - see `_normalize()`."""
    raw = _request("POST", f"/jobs/{devtools_job_id}/cancel")
    return _normalize(raw)
