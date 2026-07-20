"""wacp.core.dto

The WACP Envelope, Response Envelope, and Error Object exactly as specified
in 10_WACP_PROTOCOL.md §7 and §14. These are pure data shapes: no HTTP
calls, no I/O, no business-data typing. The `data` field of WacpEnvelope is
carried opaquely (a plain dict) per §9 — wacp.core never knows or
constrains what a Business Application puts there.

Depends on wacp.core.enums (Priority, JobStatus) and wacp.core.errors
(FieldError). No dependency on wacp.client or wacp.server.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from wacp.core.enums import JobStatus, Priority
from wacp.core.errors import FieldError


@dataclass
class WacpEnvelope:
    """10_WACP_PROTOCOL.md §7.1/§7.2 — the request envelope.

    `data` is an opaque dict owned entirely by the Business Application
    (§9); this DTO does not validate its contents beyond it being present
    as a mapping. Business-data schema validation is a DEV-TOOLS Schema
    Registry responsibility (§10), explicitly outside SDK scope.
    """

    version: str
    request_id: str
    timestamp: str
    application_id: str
    company_id: str
    project_code: str
    data: dict[str, Any]
    business_intent: Optional[str] = None
    workflow_code: Optional[str] = None
    workflow_version: Optional[str] = None
    priority: Priority = Priority.NORMAL
    correlation_id: Optional[str] = None
    callback_url: Optional[str] = None
    extensions: dict[str, Any] = field(default_factory=dict)


@dataclass
class WacpErrorDetail:
    """10_WACP_PROTOCOL.md §14.3 — the `error` object of a response.

    `field_errors` is populated only when the failure is traceable to a
    specific field in `data`; omitted (empty list) for non-field-scoped
    errors such as authentication failures (§14.3).
    """

    code: str
    message: str
    details: list[str] = field(default_factory=list)
    field_errors: list[FieldError] = field(default_factory=list)


@dataclass
class WacpResponseMeta:
    """10_WACP_PROTOCOL.md §14.1 — the `wacp` block of a response.

    `correlation_id` equals the `correlation_id` supplied in the
    originating request envelope (§7.2), completing the cross-system
    tracing capability `correlation_id` is defined for (§6). `None` when
    the originating request did not supply one -- this amendment was
    locked after the original v1.0 draft omitted it entirely, leaving
    `correlation_id` with no way to reach a response or callback despite
    being defined expressly for cross-system tracing.
    """

    version: str
    request_id: str
    response_id: str
    job_id: str
    timestamp: str
    correlation_id: Optional[str] = None


@dataclass
class WacpResponse:
    """10_WACP_PROTOCOL.md §14.1/§14.2 — the full response envelope.

    `result` is populated only when `status == JobStatus.COMPLETED`;
    `error` is populated only when `status` is `REJECTED` or `FAILED`.
    Both default to None, matching the wire format's explicit `null` for
    whichever one does not apply (§14.2).
    """

    wacp: WacpResponseMeta
    status: JobStatus
    message: str
    result: Optional[dict[str, Any]] = None
    error: Optional[WacpErrorDetail] = None


__all__ = [
    "WacpEnvelope",
    "WacpErrorDetail",
    "WacpResponseMeta",
    "WacpResponse",
]
