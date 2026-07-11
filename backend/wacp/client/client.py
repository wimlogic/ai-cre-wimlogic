"""wacp.client.client

WacpClient: the public facade of the WACP Client SDK.

This is the only class a Business Application is expected to import and
use directly. Every lower-level module (config, auth, http, builder,
errors, submission, status, results, callback, diagnostics) remains a
fully usable public class in its own right, but WacpClient composes them
into the simple, stable experience specified for this SDK:

    config = ClientConfig(...)
    client = WacpClient(config)
    client.test_connection()
    job = client.submit(...)
    status = client.wait_for_completion(...)
    results = client.get_results(...)

WacpClient duplicates no logic. Every method on this class is a direct,
one-line delegation to the method on the underlying module that already
implements it, validated in its own right in an earlier phase:

    client.submit(...)             -> JobSubmission.submit(...)
    client.cancel(...)              -> JobSubmission.cancel(...)
    client.retry(...)                -> JobSubmission.retry(...)
    client.get_job(...)               -> JobStatusPoller.get_job(...)
    client.get_status(...)             -> JobStatusPoller.get_status(...)
    client.wait_for_completion(...)     -> JobStatusPoller.wait_for_completion(...)
    client.get_results(...)              -> ResultsRetrieval.get_results(...)
    client.verify_callback(...)           -> CallbackVerifier.verify(...)
    client.get_meta()                      -> ConnectionDiagnostics.get_meta()
    client.test_connection()                -> ConnectionDiagnostics.test_connection()

Depends on every approved wacp.client module and wacp.core (only via
those modules' own public types, e.g. Priority, WacpResponse, for type
signatures). No dependency on wacp.server, DEV-TOOLS, or any Business
Application package.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from wacp.client.builder import PayloadBuilder
from wacp.client.callback import CallbackVerifier
from wacp.client.config import ClientConfig
from wacp.client.diagnostics import ConnectionDiagnostics, ConnectionTestResult, ServerMeta
from wacp.client.http import HttpClient
from wacp.client.results import ResultsRetrieval
from wacp.client.status import JobStatusPoller
from wacp.client.submission import JobSubmission
from wacp.core.dto import WacpResponse
from wacp.core.enums import Priority


class WacpClient:
    """The public facade for one Business Application's connection to one
    DEV-TOOLS deployment. Construct once per (application, deployment)
    pair, typically at application startup, and reuse for every job.

    `default_company_id`/`default_project_code` are passed through to the
    internal PayloadBuilder unchanged (§ builder.py) -- if every job this
    Business Application submits shares the same company/project, set
    them once here rather than repeating them on every submit() call.
    """

    def __init__(
        self,
        config: ClientConfig,
        *,
        default_company_id: Optional[str] = None,
        default_project_code: Optional[str] = None,
    ) -> None:
        self._config = config
        self._http = HttpClient(config)
        self._builder = PayloadBuilder(
            config,
            default_company_id=default_company_id,
            default_project_code=default_project_code,
        )
        self._submission = JobSubmission(self._http, self._builder)
        self._status = JobStatusPoller(self._http)
        self._results = ResultsRetrieval(self._http)
        self._callback = CallbackVerifier(config)
        self._diagnostics = ConnectionDiagnostics(self._http, config)

    # -- Connection Testing / Diagnostics -----------------------------

    def test_connection(self) -> ConnectionTestResult:
        """Non-raising connectivity + protocol-compatibility check.
        Delegates entirely to ConnectionDiagnostics.test_connection()."""

        return self._diagnostics.test_connection()

    def get_meta(self) -> ServerMeta:
        """Raising server metadata retrieval (§13.4). Delegates entirely
        to ConnectionDiagnostics.get_meta()."""

        return self._diagnostics.get_meta()

    # -- Job Submission -------------------------------------------------

    def submit(
        self,
        *,
        workflow_code: str,
        data: dict[str, Any],
        company_id: Optional[str] = None,
        project_code: Optional[str] = None,
        workflow_version: Optional[str] = None,
        priority: Priority = Priority.NORMAL,
        correlation_id: Optional[str] = None,
        callback_url: Optional[str] = None,
        extensions: Optional[dict[str, Any]] = None,
    ) -> WacpResponse:
        """Submits a new job. Delegates entirely to
        JobSubmission.submit()."""

        return self._submission.submit(
            workflow_code=workflow_code,
            data=data,
            company_id=company_id,
            project_code=project_code,
            workflow_version=workflow_version,
            priority=priority,
            correlation_id=correlation_id,
            callback_url=callback_url,
            extensions=extensions,
        )

    def cancel(self, job_id: str) -> WacpResponse:
        """Requests cancellation of a non-terminal job. Delegates
        entirely to JobSubmission.cancel()."""

        return self._submission.cancel(job_id)

    def retry(self, job_id: str) -> WacpResponse:
        """Creates a new job from a FAILED/CANCELLED job. Delegates
        entirely to JobSubmission.retry()."""

        return self._submission.retry(job_id)

    # -- Status -----------------------------------------------------------

    def get_job(self, job_id: str) -> WacpResponse:
        """Full job detail. Delegates entirely to
        JobStatusPoller.get_job()."""

        return self._status.get_job(job_id)

    def get_status(self, job_id: str) -> WacpResponse:
        """Lightweight status check. Delegates entirely to
        JobStatusPoller.get_status()."""

        return self._status.get_status(job_id)

    def wait_for_completion(
        self,
        job_id: str,
        *,
        poll_interval_seconds: float = 2.0,
        timeout_seconds: Optional[float] = None,
        on_progress: Optional[Callable[[WacpResponse], None]] = None,
    ) -> WacpResponse:
        """Polls until the job reaches a terminal state. Delegates
        entirely to JobStatusPoller.wait_for_completion()."""

        return self._status.wait_for_completion(
            job_id,
            poll_interval_seconds=poll_interval_seconds,
            timeout_seconds=timeout_seconds,
            on_progress=on_progress,
        )

    # -- Results --------------------------------------------------------

    def get_results(self, job_id: str) -> WacpResponse:
        """Retrieves a completed job's result. Delegates entirely to
        ResultsRetrieval.get_results()."""

        return self._results.get_results(job_id)

    # -- Callback verification --------------------------------------------

    def verify_callback(self, *, raw_body: bytes, headers: dict[str, str]) -> WacpResponse:
        """Verifies and parses an inbound callback. Delegates entirely to
        CallbackVerifier.verify()."""

        return self._callback.verify(raw_body=raw_body, headers=headers)


__all__ = ["WacpClient"]
