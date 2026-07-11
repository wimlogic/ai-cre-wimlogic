"""wacp.core

Protocol-level components only: DTOs, enumerations, error codes,
constants, versioning, serialization, validation, and shared utilities.

Per 20_WACP_SDK_ARCHITECTURE.md §2.2, wacp.core depends on nothing else in
this repository, and nothing in wacp.core may import from wacp.client or
wacp.server. Every symbol re-exported below is a direct implementation of
something 10_WACP_PROTOCOL.md already specifies -- no consumer-specific
behavior lives here.
"""

from __future__ import annotations

from wacp.core.constants import (
    CALLBACK_MAX_DELIVERY_ATTEMPTS,
    CALLBACK_RETRY_BACKOFF_SECONDS,
    CALLBACK_REPLAY_WINDOW_SECONDS,
    CONTENT_TYPE,
    CURRENT_PROTOCOL_VERSION,
    HEADER_API_KEY,
    HEADER_API_SECRET,
    HEADER_APPLICATION_ID,
    HEADER_CALLBACK_SIGNATURE,
    HEADER_CALLBACK_TIMESTAMP,
    HEADER_PROTOCOL_VERSION,
    JOB_CANCEL_PATH,
    JOB_DETAIL_PATH,
    JOB_RESULTS_PATH,
    JOB_RETRY_PATH,
    JOB_STATUS_PATH,
    JOBS_COLLECTION_PATH,
    MAX_ENVELOPE_SIZE_BYTES,
    SUPPORTED_PROTOCOL_VERSIONS,
    WACP_API_PREFIX,
    WACP_META_PATH,
    WORKFLOW_SCHEMA_PATH,
)
from wacp.core.dto import WacpEnvelope, WacpErrorDetail, WacpResponse, WacpResponseMeta
from wacp.core.enums import (
    TERMINAL_JOB_STATUSES,
    VALID_TRANSITIONS,
    JobStatus,
    Priority,
    is_terminal,
    is_valid_transition,
)
from wacp.core.errors import (
    ERROR_CODE_TABLE,
    FieldError,
    WacpAuthenticationError,
    WacpEnvelopeError,
    WacpError,
    WacpErrorCode,
    WacpInternalError,
    WacpLifecycleError,
    WacpValidationError,
    WacpWorkflowError,
    exception_for_code,
    lookup_error_code,
)
from wacp.core.serialization import (
    dict_to_envelope,
    dict_to_response,
    envelope_to_dict,
    envelope_to_json,
    json_to_envelope,
    json_to_response,
    response_to_dict,
    response_to_json,
)
from wacp.core.utils import (
    current_timestamp,
    generate_request_id,
    is_valid_request_id,
    parse_timestamp,
    seconds_since,
    sign_hmac_sha256,
    verify_hmac_sha256,
)
from wacp.core.validation import is_envelope_valid, validate_envelope
from wacp.core.versioning import (
    SemanticVersion,
    is_same_major,
    is_supported_version,
    parse_version,
    require_supported_version,
)

__all__ = [
    # constants
    "CALLBACK_MAX_DELIVERY_ATTEMPTS",
    "CALLBACK_RETRY_BACKOFF_SECONDS",
    "CALLBACK_REPLAY_WINDOW_SECONDS",
    "CONTENT_TYPE",
    "CURRENT_PROTOCOL_VERSION",
    "HEADER_API_KEY",
    "HEADER_API_SECRET",
    "HEADER_APPLICATION_ID",
    "HEADER_CALLBACK_SIGNATURE",
    "HEADER_CALLBACK_TIMESTAMP",
    "HEADER_PROTOCOL_VERSION",
    "JOB_CANCEL_PATH",
    "JOB_DETAIL_PATH",
    "JOB_RESULTS_PATH",
    "JOB_RETRY_PATH",
    "JOB_STATUS_PATH",
    "JOBS_COLLECTION_PATH",
    "MAX_ENVELOPE_SIZE_BYTES",
    "SUPPORTED_PROTOCOL_VERSIONS",
    "WACP_API_PREFIX",
    "WACP_META_PATH",
    "WORKFLOW_SCHEMA_PATH",
    # dto
    "WacpEnvelope",
    "WacpErrorDetail",
    "WacpResponse",
    "WacpResponseMeta",
    # enums
    "TERMINAL_JOB_STATUSES",
    "VALID_TRANSITIONS",
    "JobStatus",
    "Priority",
    "is_terminal",
    "is_valid_transition",
    # errors
    "ERROR_CODE_TABLE",
    "FieldError",
    "WacpAuthenticationError",
    "WacpEnvelopeError",
    "WacpError",
    "WacpErrorCode",
    "WacpInternalError",
    "WacpLifecycleError",
    "WacpValidationError",
    "WacpWorkflowError",
    "exception_for_code",
    "lookup_error_code",
    # serialization
    "dict_to_envelope",
    "dict_to_response",
    "envelope_to_dict",
    "envelope_to_json",
    "json_to_envelope",
    "json_to_response",
    "response_to_dict",
    "response_to_json",
    # utils
    "current_timestamp",
    "generate_request_id",
    "is_valid_request_id",
    "parse_timestamp",
    "seconds_since",
    "sign_hmac_sha256",
    "verify_hmac_sha256",
    # validation
    "is_envelope_valid",
    "validate_envelope",
    # versioning
    "SemanticVersion",
    "is_same_major",
    "is_supported_version",
    "parse_version",
    "require_supported_version",
]
