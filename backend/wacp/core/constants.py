"""wacp.core.constants

Fixed, literal values defined by 10_WACP_PROTOCOL.md. Every value in this
module is a direct transcription of something the protocol specification
already locks — header names (§8), REST path templates (§13), operational
limits (§19), callback retry timing (§17.4), and the content type (§19.3).

This module intentionally contains no logic, no classes, and no behavior.
Its sole purpose is to be the one place a header name, path template, or
limit is spelled out, so that wacp.client and wacp.server never each hard-
code their own copy and drift apart.

Per 20_WACP_SDK_ARCHITECTURE.md §2.2, this module has no dependency on any
other wacp module — it is the first and most dependency-free Core module.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Protocol identity (10_WACP_PROTOCOL.md §7.2, §20.2)
# ---------------------------------------------------------------------------

#: The WACP protocol version implemented by this SDK release. This is a
#: statement about what this copy of wacp.core speaks, not a claim about
#: what any particular DEV-TOOLS deployment supports — that is discovered
#: at runtime via the meta endpoint (see WACP_META_PATH below).
CURRENT_PROTOCOL_VERSION: str = "1.0"

#: Protocol versions this SDK release is able to construct and parse.
#: A single-element tuple today; grows only when this SDK is deliberately
#: updated to support an additional protocol version (20_WACP_SDK_ARCHITECTURE
#: .md §8.2 — SDK version and protocol version are independent axes).
SUPPORTED_PROTOCOL_VERSIONS: tuple[str, ...] = ("1.0",)


# ---------------------------------------------------------------------------
# HTTP headers (10_WACP_PROTOCOL.md §8, §17.3)
# ---------------------------------------------------------------------------

#: Required. Must equal wacp.application_id in the envelope body exactly
#: (§8, §16.2 step 5). A mismatch is WACP-201.
HEADER_APPLICATION_ID: str = "X-WACP-Application-Id"

#: Required. The Business Application's API key (§16.1).
HEADER_API_KEY: str = "X-WACP-Api-Key"

#: Required. The Business Application's API secret (§16.1).
HEADER_API_SECRET: str = "X-WACP-Api-Secret"

#: Optional explicit protocol version pin; if present, must match
#: wacp.version in the envelope body (§8).
HEADER_PROTOCOL_VERSION: str = "X-WACP-Protocol-Version"

#: Present on callback requests only. HMAC-SHA256 signature of the raw
#: callback request body, keyed with the receiving application's api_secret
#: (§17.3).
HEADER_CALLBACK_SIGNATURE: str = "X-WACP-Callback-Signature"

#: Present on callback requests only. ISO 8601 UTC timestamp the callback
#: was sent; receivers should reject callbacks older than
#: CALLBACK_REPLAY_WINDOW_SECONDS (§17.3).
HEADER_CALLBACK_TIMESTAMP: str = "X-WACP-Callback-Timestamp"

#: Required content type for every WACP request, response, and callback
#: body (§19.3). Requests with any other Content-Type are rejected as
#: WACP-101.
CONTENT_TYPE: str = "application/json; charset=utf-8"


# ---------------------------------------------------------------------------
# REST path templates (10_WACP_PROTOCOL.md §13.1)
# ---------------------------------------------------------------------------
#
# These are templates, not URLs — {job_id}, {workflow_code}, and
# {workflow_version} are placeholders a caller fills in. They are provided
# as plain str.format-style templates rather than a routing library
# abstraction, since wacp.core must stay independent of any particular HTTP
# client or web framework (20_WACP_SDK_ARCHITECTURE.md §4.1).

WACP_API_PREFIX: str = "/wacp/v1"

#: POST — submit a new job. Returns 202 Accepted with a Location header
#: pointing at JOB_DETAIL_PATH (§13.3).
JOBS_COLLECTION_PATH: str = f"{WACP_API_PREFIX}/jobs"

#: GET — full job detail, including status and result if terminal.
JOB_DETAIL_PATH: str = f"{WACP_API_PREFIX}/jobs/{{job_id}}"

#: GET — status only (lightweight polling).
JOB_STATUS_PATH: str = f"{WACP_API_PREFIX}/jobs/{{job_id}}/status"

#: GET — result payload; 409 if not yet terminal.
JOB_RESULTS_PATH: str = f"{WACP_API_PREFIX}/jobs/{{job_id}}/results"

#: POST — request cancellation of a non-terminal job.
JOB_CANCEL_PATH: str = f"{WACP_API_PREFIX}/jobs/{{job_id}}/cancel"

#: POST — create a new job from a FAILED or CANCELLED job's original
#: envelope (§13.2). Rejected as WACP-403 if the source job is COMPLETED.
JOB_RETRY_PATH: str = f"{WACP_API_PREFIX}/jobs/{{job_id}}/retry"

#: GET — retrieve the schema bound to a workflow version, for optional
#: client-side pre-validation (§10.3). Advisory only; DEV-TOOLS always
#: re-validates server-side.
WORKFLOW_SCHEMA_PATH: str = (
    f"{WACP_API_PREFIX}/workflows/{{workflow_code}}/versions/{{workflow_version}}/schema"
)

#: GET — server metadata: supported protocol versions, deprecation notices
#: (§13.1, §20.4).
WACP_META_PATH: str = f"{WACP_API_PREFIX}/meta"


# ---------------------------------------------------------------------------
# Operational limits (10_WACP_PROTOCOL.md §19)
# ---------------------------------------------------------------------------

#: Maximum total envelope size in bytes (§19.2). A deployment may advertise
#: a different effective limit via the meta endpoint; this is the protocol
#: default, not a hard client-side ceiling the SDK silently enforces on its
#: own authority.
MAX_ENVELOPE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB

#: How old a callback's X-WACP-Callback-Timestamp may be before a receiver
#: should reject it as a possible replay (§17.3).
CALLBACK_REPLAY_WINDOW_SECONDS: int = 5 * 60  # 5 minutes

#: Maximum number of callback delivery attempts before the callback is
#: marked undelivered (§17.4). Attempt 1 is the immediate delivery at
#: t=0 upon reaching a terminal workflow state; attempts 2-5 are retries
#: after a failed delivery, per the locked callback retry policy.
CALLBACK_MAX_DELIVERY_ATTEMPTS: int = 5

#: Backoff delays, in seconds, before each retry following a failed
#: delivery (§17.4, locked callback retry policy). The initial delivery
#: attempt is immediate and is NOT part of this schedule, so this tuple
#: has exactly CALLBACK_MAX_DELIVERY_ATTEMPTS - 1 entries:
#:   index 0 -> delay before attempt 2 (30 seconds)
#:   index 1 -> delay before attempt 3 (2 minutes)
#:   index 2 -> delay before attempt 4 (10 minutes)
#:   index 3 -> delay before attempt 5 (1 hour)
CALLBACK_RETRY_BACKOFF_SECONDS: tuple[int, ...] = (30, 120, 600, 3600)


__all__ = [
    "CURRENT_PROTOCOL_VERSION",
    "SUPPORTED_PROTOCOL_VERSIONS",
    "HEADER_APPLICATION_ID",
    "HEADER_API_KEY",
    "HEADER_API_SECRET",
    "HEADER_PROTOCOL_VERSION",
    "HEADER_CALLBACK_SIGNATURE",
    "HEADER_CALLBACK_TIMESTAMP",
    "CONTENT_TYPE",
    "WACP_API_PREFIX",
    "JOBS_COLLECTION_PATH",
    "JOB_DETAIL_PATH",
    "JOB_STATUS_PATH",
    "JOB_RESULTS_PATH",
    "JOB_CANCEL_PATH",
    "JOB_RETRY_PATH",
    "WORKFLOW_SCHEMA_PATH",
    "WACP_META_PATH",
    "MAX_ENVELOPE_SIZE_BYTES",
    "CALLBACK_REPLAY_WINDOW_SECONDS",
    "CALLBACK_MAX_DELIVERY_ATTEMPTS",
    "CALLBACK_RETRY_BACKOFF_SECONDS",
]
