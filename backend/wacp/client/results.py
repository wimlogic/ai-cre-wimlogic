"""wacp.client.results

Results Retrieval: get_results(), per 10_WACP_PROTOCOL.md §13.1
(GET /jobs/{job_id}/results; 409 if the job is not yet terminal).

Like wacp.client.submission and wacp.client.status, this module adds no
logic beyond wiring together the already-approved HttpClient and
wacp.client.errors.parse_wacp_response. The "not yet terminal" case is
not special-cased here: whatever WACP-xxx error DEV-TOOLS returns in that
situation is already translated into the correct wacp.core.errors
exception by parse_wacp_response, exactly as it is for every other
endpoint -- there is nothing results-specific to add.

Depends on wacp.client.http (HttpClient), wacp.client.errors
(parse_wacp_response), wacp.core.constants (JOB_RESULTS_PATH), and
wacp.core.dto (WacpResponse). No dependency on wacp.client.builder,
wacp.client.status, wacp.server, DEV-TOOLS, or any Business Application
package.
"""

from __future__ import annotations

from wacp.client.errors import parse_wacp_response
from wacp.client.http import HttpClient
from wacp.core.constants import JOB_RESULTS_PATH
from wacp.core.dto import WacpResponse


class ResultsRetrieval:
    """Coordinates HttpClient and the Client Error Handling module into a
    get_results() API. Holds no protocol logic and no HTTP logic of its
    own.
    """

    def __init__(self, http_client: HttpClient) -> None:
        self._http = http_client

    def get_results(self, job_id: str) -> WacpResponse:
        """Retrieves a job's result: GET /wacp/v1/jobs/{job_id}/results
        (§13.1).

        If the job has not yet reached a terminal state, DEV-TOOLS
        returns 409 with a WACP-xxx error body; parse_wacp_response
        raises the corresponding wacp.core.errors exception exactly as it
        does for any other endpoint's error response -- callers catch
        that exception (rather than checking a status code) to detect
        "not ready yet".

        On success, `response.result` carries the job's output
        (§14.2: populated only when status == COMPLETED).
        """

        http_response = self._http.get(JOB_RESULTS_PATH.format(job_id=job_id))
        return parse_wacp_response(http_response)


__all__ = ["ResultsRetrieval"]
