"""wacp.core.serialization

Encodes WacpEnvelope / WacpResponse DTOs to the exact JSON shape defined in
10_WACP_PROTOCOL.md §7 and §14, and decodes incoming JSON back into those
DTOs. This is the only place envelope JSON shape is defined; neither
wacp.client nor wacp.server re-implements field name mapping independently
(20_WACP_SDK_ARCHITECTURE.md §4.2).

Decoding raises wacp.core.errors.WacpEnvelopeError (WACP-101) on structural
problems -- missing required fields, wrong types -- rather than a bare
KeyError/TypeError, so callers can catch one exception type regardless of
what specifically was wrong with the input.

Depends on wacp.core.dto, wacp.core.enums, and wacp.core.errors. No
dependency on wacp.client or wacp.server.
"""

from __future__ import annotations

import json
from typing import Any

from wacp.core.dto import WacpEnvelope, WacpErrorDetail, WacpResponse, WacpResponseMeta
from wacp.core.enums import JobStatus, Priority
from wacp.core.errors import WACP_101, FieldError, WacpEnvelopeError

_REQUIRED_ENVELOPE_FIELDS = (
    "version",
    "request_id",
    "timestamp",
    "application_id",
    "company_id",
    "project_code",
)


# ---------------------------------------------------------------------------
# WacpEnvelope <-> dict / JSON
# ---------------------------------------------------------------------------


def envelope_to_dict(envelope: WacpEnvelope) -> dict[str, Any]:
    """Encodes a WacpEnvelope into the exact §7.1 wire structure:
    a top-level `wacp` metadata block and a top-level `data` block.
    """

    wacp_block: dict[str, Any] = {
        "version": envelope.version,
        "request_id": envelope.request_id,
        "timestamp": envelope.timestamp,
        "application_id": envelope.application_id,
        "company_id": envelope.company_id,
        "project_code": envelope.project_code,
        "priority": Priority(envelope.priority).value,
        "extensions": envelope.extensions,
    }
    if envelope.business_intent is not None:
        wacp_block["business_intent"] = envelope.business_intent
    if envelope.workflow_code is not None:
        wacp_block["workflow_code"] = envelope.workflow_code
    if envelope.workflow_version is not None:
        wacp_block["workflow_version"] = envelope.workflow_version
    if envelope.correlation_id is not None:
        wacp_block["correlation_id"] = envelope.correlation_id
    if envelope.callback_url is not None:
        wacp_block["callback_url"] = envelope.callback_url

    return {"wacp": wacp_block, "data": envelope.data}


def envelope_to_json(envelope: WacpEnvelope) -> str:
    """Encodes a WacpEnvelope to a JSON string (§19.3 content type)."""

    return json.dumps(envelope_to_dict(envelope))


def dict_to_envelope(payload: dict[str, Any]) -> WacpEnvelope:
    """Decodes a raw wire-format dict into a WacpEnvelope.

    Raises WacpEnvelopeError (WACP-101) if the top-level `wacp`/`data`
    blocks are missing, if any required field (§6 of 10_WACP_PROTOCOL.md)
    is absent, or if `priority` is not a recognized value.
    """

    if not isinstance(payload, dict) or "wacp" not in payload or "data" not in payload:
        raise WacpEnvelopeError(
            WACP_101, "Envelope must contain top-level 'wacp' and 'data' objects."
        )

    wacp_block = payload["wacp"]
    if not isinstance(wacp_block, dict):
        raise WacpEnvelopeError(WACP_101, "'wacp' block must be an object.")

    data_block = payload["data"]
    if not isinstance(data_block, dict):
        raise WacpEnvelopeError(WACP_101, "'data' block must be an object.")

    missing = [f for f in _REQUIRED_ENVELOPE_FIELDS if f not in wacp_block]
    if missing:
        raise WacpEnvelopeError(
            WACP_101, f"Envelope missing required field(s): {', '.join(missing)}."
        )

    priority_raw = wacp_block.get("priority", Priority.NORMAL.value)
    try:
        priority = Priority(priority_raw)
    except ValueError as exc:
        raise WacpEnvelopeError(
            WACP_101, f"Invalid priority value: {priority_raw!r}."
        ) from exc

    return WacpEnvelope(
        version=wacp_block["version"],
        request_id=wacp_block["request_id"],
        timestamp=wacp_block["timestamp"],
        application_id=wacp_block["application_id"],
        company_id=wacp_block["company_id"],
        project_code=wacp_block["project_code"],
        data=data_block,
        business_intent=wacp_block.get("business_intent"),
        workflow_code=wacp_block.get("workflow_code"),
        workflow_version=wacp_block.get("workflow_version"),
        priority=priority,
        correlation_id=wacp_block.get("correlation_id"),
        callback_url=wacp_block.get("callback_url"),
        extensions=wacp_block.get("extensions", {}) or {},
    )


def json_to_envelope(raw: str) -> WacpEnvelope:
    """Decodes a JSON string into a WacpEnvelope. Raises WacpEnvelopeError
    (WACP-101) for both malformed JSON and structurally invalid envelopes,
    so callers handle one exception type regardless of which failed.
    """

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WacpEnvelopeError(WACP_101, "Envelope is not valid JSON.") from exc
    return dict_to_envelope(payload)


# ---------------------------------------------------------------------------
# WacpResponse <-> dict / JSON
# ---------------------------------------------------------------------------


def response_to_dict(response: WacpResponse) -> dict[str, Any]:
    """Encodes a WacpResponse into the exact §14.1 wire structure."""

    error_dict = None
    if response.error is not None:
        error_dict = {
            "code": response.error.code,
            "message": response.error.message,
            "details": response.error.details,
            "field_errors": [
                {"path": fe.path, "message": fe.message}
                for fe in response.error.field_errors
            ],
        }

    return {
        "wacp": {
            "version": response.wacp.version,
            "request_id": response.wacp.request_id,
            "response_id": response.wacp.response_id,
            "job_id": response.wacp.job_id,
            "correlation_id": response.wacp.correlation_id,
            "timestamp": response.wacp.timestamp,
        },
        "status": JobStatus(response.status).value,
        "message": response.message,
        "result": response.result,
        "error": error_dict,
    }


def response_to_json(response: WacpResponse) -> str:
    """Encodes a WacpResponse to a JSON string."""

    return json.dumps(response_to_dict(response))


_REQUIRED_RESPONSE_META_FIELDS = (
    "version",
    "request_id",
    "response_id",
    "job_id",
    "timestamp",
)


def dict_to_response(payload: dict[str, Any]) -> WacpResponse:
    """Decodes a raw wire-format dict into a WacpResponse.

    Raises WacpEnvelopeError (WACP-101) on structural problems: a missing
    `wacp` block, a missing required meta field, or an unrecognized
    `status` value.
    """

    if not isinstance(payload, dict) or "wacp" not in payload:
        raise WacpEnvelopeError(WACP_101, "Response must contain a top-level 'wacp' object.")

    wacp_block = payload["wacp"]
    if not isinstance(wacp_block, dict):
        raise WacpEnvelopeError(WACP_101, "'wacp' block must be an object.")

    missing = [f for f in _REQUIRED_RESPONSE_META_FIELDS if f not in wacp_block]
    if missing:
        raise WacpEnvelopeError(
            WACP_101, f"Response 'wacp' block missing required field(s): {', '.join(missing)}."
        )

    if "status" not in payload:
        raise WacpEnvelopeError(WACP_101, "Response missing required field: status.")

    try:
        status = JobStatus(payload["status"])
    except ValueError as exc:
        raise WacpEnvelopeError(
            WACP_101, f"Invalid status value: {payload['status']!r}."
        ) from exc

    error_obj = None
    error_raw = payload.get("error")
    if error_raw is not None:
        if not isinstance(error_raw, dict) or "code" not in error_raw or "message" not in error_raw:
            raise WacpEnvelopeError(WACP_101, "'error' object must contain 'code' and 'message'.")
        error_obj = WacpErrorDetail(
            code=error_raw["code"],
            message=error_raw["message"],
            details=error_raw.get("details", []) or [],
            field_errors=[
                FieldError(path=fe["path"], message=fe["message"])
                for fe in (error_raw.get("field_errors") or [])
            ],
        )

    return WacpResponse(
        wacp=WacpResponseMeta(
            version=wacp_block["version"],
            request_id=wacp_block["request_id"],
            response_id=wacp_block["response_id"],
            job_id=wacp_block["job_id"],
            timestamp=wacp_block["timestamp"],
            correlation_id=wacp_block.get("correlation_id"),
        ),
        status=status,
        message=payload.get("message", ""),
        result=payload.get("result"),
        error=error_obj,
    )


def json_to_response(raw: str) -> WacpResponse:
    """Decodes a JSON string into a WacpResponse. Raises WacpEnvelopeError
    (WACP-101) for both malformed JSON and structurally invalid responses.
    """

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WacpEnvelopeError(WACP_101, "Response is not valid JSON.") from exc
    return dict_to_response(payload)


__all__ = [
    "envelope_to_dict",
    "envelope_to_json",
    "dict_to_envelope",
    "json_to_envelope",
    "response_to_dict",
    "response_to_json",
    "dict_to_response",
    "json_to_response",
]
