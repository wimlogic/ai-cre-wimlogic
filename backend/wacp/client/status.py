"""wacp.client.status

Status: get_job(), get_status(), and wait_for_completion(), per
10_WACP_PROTOCOL.md §13.1 (GET /jobs/{job_id}, GET /jobs/{job_id}/status)
and §12 (job lifecycle).

Like wacp.client.submission, this module is a thin orchestration layer.
Every HTTP call goes through the already-approved HttpClient, and every
response is decoded through the already-approved
wacp.client.errors.parse_wacp_response -- this module adds no transport
logic, no response parsing, no validation, and no exception translation
of its own. Its only added value is the wait_for_completion() polling
loop, which uses wacp.core.enums.is_terminal (already-defined protocol
data, not a new lifecycle rule) to decide when to stop polling.

Depends on wacp.client.http (HttpClient), wacp.client.errors
(parse_wacp_response), wacp.core.constants (REST path templates),
wacp.core.dto (WacpResponse), and wacp.core.enums (is_terminal). No
dependency on wacp.client.builder (Status never builds a request
envelope), wacp.server, DEV-TOOLS, or any Business Application package.
"""

from __future__ import annotations

import time
from typing import Callable, Optional

from wacp.client.errors import parse_wacp_response
from wacp.client.http import HttpClient
from wacp.core.constants import JOB_DETAIL_PATH, JOB_STATUS_PATH
from wacp.core.dto import WacpResponse
from wacp.core.enums import is_terminal


class JobWaitTimeoutError(Exception):
    """Raised by wait_for_completion() when `timeout_seconds` elapses
    before the job reaches a terminal state.

    This is deliberately NOT a wacp.core.errors.WacpError subclass: it is
    not a protocol fact DEV-TOOLS reported (there is no WACP-xxx code for
    "the caller got tired of waiting"), it is a client-side waiting
    policy outcome -- the same reasoning that keeps
    wacp.client.http.HttpRetriesExhaustedError outside the WacpError
    hierarchy. `last_response` carries whatever status was last observed,
    so a caller can inspect it (e.g. to decide whether to keep polling
    manually) rather than losing that information.
    """

    def __init__(self, job_id: str, elapsed_seconds: float, last_response: WacpResponse) -> None:
        self.job_id = job_id
        self.elapsed_seconds = elapsed_seconds
        self.last_response = last_response
        super().__init__(
            f"Job {job_id} did not reach a terminal state within "
            f"{elapsed_seconds:.1f}s (last observed status: {last_response.status})."
        )


class JobStatusPoller:
    """Coordinates HttpClient and the Client Error Handling module into a
    get_job()/get_status()/wait_for_completion() API. Holds no protocol
    logic and no HTTP logic of its own.
    """

    def __init__(self, http_client: HttpClient) -> None:
        self._http = http_client

    def get_job(self, job_id: str) -> WacpResponse:
        """Full job detail: GET /wacp/v1/jobs/{job_id} (§13.1). Returns
        the complete response, including `result` once terminal.
        """

        http_response = self._http.get(JOB_DETAIL_PATH.format(job_id=job_id))
        return parse_wacp_response(http_response)

    def get_status(self, job_id: str) -> WacpResponse:
        """Lightweight status check: GET /wacp/v1/jobs/{job_id}/status
        (§13.1). Intended for frequent polling without the cost of
        transferring a possibly-large `result` payload on every check.
        """

        http_response = self._http.get(JOB_STATUS_PATH.format(job_id=job_id))
        return parse_wacp_response(http_response)

    def wait_for_completion(
        self,
        job_id: str,
        *,
        poll_interval_seconds: float = 2.0,
        timeout_seconds: Optional[float] = None,
        on_progress: Optional[Callable[[WacpResponse], None]] = None,
    ) -> WacpResponse:
        """Polls get_status() at `poll_interval_seconds` intervals until
        the job reaches a terminal state (§12.2:
        COMPLETED/FAILED/CANCELLED/REJECTED), then returns the final
        WacpResponse.

        `on_progress`, if supplied, is called once per poll (including
        the poll that observes the terminal state) with the current
        WacpResponse -- purely a caller-supplied hook for progress
        reporting; this method does not interpret or act on its return
        value.

        Raises JobWaitTimeoutError if `timeout_seconds` is set and
        elapses before a terminal state is observed. If `timeout_seconds`
        is None (the default), polls indefinitely.
        """

        start = time.monotonic()

        while True:
            response = self.get_status(job_id)

            if on_progress is not None:
                on_progress(response)

            if is_terminal(response.status):
                return response

            elapsed = time.monotonic() - start
            if timeout_seconds is not None and elapsed >= timeout_seconds:
                raise JobWaitTimeoutError(
                    job_id=job_id, elapsed_seconds=elapsed, last_response=response
                )

            time.sleep(poll_interval_seconds)


__all__ = ["JobStatusPoller", "JobWaitTimeoutError"]
