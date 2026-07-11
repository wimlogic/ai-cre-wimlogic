"""wacp.client

The WACP Client SDK: client-side WACP protocol behavior for every WIMLOGIC
Business Application (AI-CRE, AI-ECOM, AI-HR, AI-LEGAL, and future
products).

Most callers only need `WacpClient` and `ClientConfig`:

    from wacp.client import ClientConfig, WacpClient

    config = ClientConfig(
        base_url="https://dev-tools.wimlogic.com",
        application_id="AI-CRE",
        api_key="...",
        api_secret="...",
    )
    client = WacpClient(config)

    client.test_connection()
    job = client.submit(workflow_code="PROPERTY_ANALYSIS", data={...},
                        company_id="COMPANY-001", project_code="PROJ-EASTGATE")
    result = client.wait_for_completion(job.wacp.job_id)
    results = client.get_results(job.wacp.job_id)

Every lower-level module (auth, http, builder, errors, submission,
status, results, callback, diagnostics) also remains independently
usable and is exported here for callers who need finer-grained control
than the facade provides.

Depends only on wacp.core (20_WACP_SDK_ARCHITECTURE.md §2.2). Never
imports wacp.server, DEV-TOOLS, or any Business Application package --
enforced by tests/test_dependency_direction.py.
"""

from __future__ import annotations

from wacp.client.auth import build_auth_headers, redact_auth_headers
from wacp.client.builder import PayloadBuilder
from wacp.client.callback import CallbackVerificationError, CallbackVerifier
from wacp.client.client import WacpClient
from wacp.client.config import ClientConfig, RetryConfig
from wacp.client.diagnostics import ConnectionDiagnostics, ConnectionTestResult, ServerMeta
from wacp.client.errors import parse_wacp_response, raise_for_error
from wacp.client.http import (
    HttpClient,
    HttpConnectionError,
    HttpError,
    HttpResponse,
    HttpRetriesExhaustedError,
    HttpTimeoutError,
    compute_backoff_seconds,
)
from wacp.client.results import ResultsRetrieval
from wacp.client.status import JobStatusPoller, JobWaitTimeoutError
from wacp.client.submission import JobSubmission

__all__ = [
    # facade (primary public API)
    "WacpClient",
    "ClientConfig",
    "RetryConfig",
    # auth
    "build_auth_headers",
    "redact_auth_headers",
    # builder
    "PayloadBuilder",
    # http
    "HttpClient",
    "HttpResponse",
    "HttpError",
    "HttpTimeoutError",
    "HttpConnectionError",
    "HttpRetriesExhaustedError",
    "compute_backoff_seconds",
    # errors (client-side translation)
    "parse_wacp_response",
    "raise_for_error",
    # submission
    "JobSubmission",
    # status
    "JobStatusPoller",
    "JobWaitTimeoutError",
    # results
    "ResultsRetrieval",
    # callback
    "CallbackVerifier",
    "CallbackVerificationError",
    # diagnostics
    "ConnectionDiagnostics",
    "ConnectionTestResult",
    "ServerMeta",
]
