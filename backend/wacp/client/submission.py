"""wacp.client.submission

Job Submission: submit(), cancel(), and retry(), per 10_WACP_PROTOCOL.md
§13.1 (POST /jobs, POST /jobs/{job_id}/cancel, POST /jobs/{job_id}/retry)
and §13.2 (retry semantics).

This module is a thin orchestration layer only. It coordinates four
already-approved components and adds no logic of its own beyond wiring
them together:

    PayloadBuilder.build(...)        -- construct + validate the envelope
        |
        v
    wacp.core.serialization.envelope_to_dict(...)  -- encode to wire dict
        |
        v
    HttpClient.post(...)             -- send, retry transient failures
        |
        v
    wacp.client.errors.parse_wacp_response(...)    -- decode + raise/return
        |
        v
    WacpResponse

Envelope validation is PayloadBuilder's job (already done before this
module ever sees the envelope). Response decoding and error-to-exception
translation is wacp.client.errors's job. This module does not re-validate
anything and does not re-implement response parsing -- it only decides
which HTTP verb and path correspond to which caller-facing method.

Depends on wacp.client.builder (PayloadBuilder), wacp.client.http
(HttpClient), wacp.client.errors (parse_wacp_response), wacp.core.dto
(WacpResponse, for the type signature), wacp.core.enums (Priority), and
wacp.core.constants (REST path templates). No dependency on wacp.server,
DEV-TOOLS, or any Business Application package.
"""

from __future__ import annotations

from typing import Any, Optional

from wacp.client.builder import PayloadBuilder
from wacp.client.errors import parse_wacp_response
from wacp.client.http import HttpClient
from wacp.core.constants import JOB_CANCEL_PATH, JOB_RETRY_PATH, JOBS_COLLECTION_PATH
from wacp.core.dto import WacpResponse
from wacp.core.enums import Priority
from wacp.core.serialization import envelope_to_dict


class JobSubmission:
    """Coordinates PayloadBuilder, HttpClient, and the Client Error
    Handling module into a submit()/cancel()/retry() API. Holds no
    protocol logic and no HTTP logic of its own -- both already exist in
    the modules it composes.
    """

    def __init__(self, http_client: HttpClient, builder: PayloadBuilder) -> None:
        self._http = http_client
        self._builder = builder

    def submit(
        self,
        *,
        data: dict[str, Any],
        business_intent: Optional[str] = None,
        workflow_code: Optional[str] = None,
        company_id: Optional[str] = None,
        project_code: Optional[str] = None,
        workflow_version: Optional[str] = None,
        priority: Priority = Priority.NORMAL,
        correlation_id: Optional[str] = None,
        callback_url: Optional[str] = None,
        extensions: Optional[dict[str, Any]] = None,
    ) -> WacpResponse:
        """Submits a new job: POST /wacp/v1/jobs (§13.1).

        Raises WacpEnvelopeError (WACP-101) before any network call if
        PayloadBuilder.build(...) rejects the inputs (e.g. missing
        company_id/project_code with no configured default, non-HTTPS
        callback_url, non-JSON-serializable data) -- an invalid request is
        never sent.

        Raises the appropriate wacp.core.errors exception (via
        wacp.client.errors.parse_wacp_response) if DEV-TOOLS itself
        rejects the request (e.g. WACP-305 schema validation failure).
        """

        envelope = self._builder.build(
            data=data,
            business_intent=business_intent,
            workflow_code=workflow_code,
            company_id=company_id,
            project_code=project_code,
            workflow_version=workflow_version,
            priority=priority,
            correlation_id=correlation_id,
            callback_url=callback_url,
            extensions=extensions,
        )
        envelope_dict = envelope_to_dict(envelope)
        http_response = self._http.post(JOBS_COLLECTION_PATH, json_body=envelope_dict)
        return parse_wacp_response(http_response)

    def cancel(self, job_id: str) -> WacpResponse:
        """Requests cancellation of a non-terminal job: POST
        /wacp/v1/jobs/{job_id}/cancel (§13.1). If the job is already
        terminal, DEV-TOOLS returns WACP-502, which
        parse_wacp_response raises as WacpLifecycleError.
        """

        http_response = self._http.post(JOB_CANCEL_PATH.format(job_id=job_id))
        return parse_wacp_response(http_response)

    def retry(self, job_id: str) -> WacpResponse:
        """Creates a new job from a FAILED or CANCELLED job's original
        envelope: POST /wacp/v1/jobs/{job_id}/retry (§13.2). Retrying a
        COMPLETED job is rejected by DEV-TOOLS as WACP-403, which
        parse_wacp_response raises as WacpWorkflowError.
        """

        http_response = self._http.post(JOB_RETRY_PATH.format(job_id=job_id))
        return parse_wacp_response(http_response)


__all__ = ["JobSubmission"]
