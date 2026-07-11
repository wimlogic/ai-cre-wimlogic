"""wacp.core.errors

The full WACP-1xx..WACP-9xx error code table from 10_WACP_PROTOCOL.md §15,
each code's default message and mapped HTTP status, and the exception
hierarchy both wacp.client and wacp.server raise and catch.

Depends only on the Python standard library. No dependency on any other
wacp module, wacp.client, or wacp.server.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class WacpErrorCode:
    """A single row of the §15 error code table."""

    code: str
    default_message: str
    http_status: int


# ---------------------------------------------------------------------------
# WACP-1xx — Envelope errors (§15.2)
# ---------------------------------------------------------------------------
WACP_101 = WacpErrorCode("WACP-101", "Invalid envelope.", 400)
WACP_102 = WacpErrorCode("WACP-102", "Unsupported protocol version.", 400)
WACP_103 = WacpErrorCode("WACP-103", "Duplicate request.", 409)
WACP_104 = WacpErrorCode("WACP-104", "Payload exceeds maximum size.", 413)

# ---------------------------------------------------------------------------
# WACP-2xx — Authentication / authorization errors (§15.2)
# ---------------------------------------------------------------------------
WACP_201 = WacpErrorCode("WACP-201", "Application mismatch.", 403)
WACP_202 = WacpErrorCode("WACP-202", "Unauthorized.", 401)
WACP_203 = WacpErrorCode("WACP-203", "Application suspended or inactive.", 403)
WACP_204 = WacpErrorCode("WACP-204", "Rate limit exceeded.", 429)

# ---------------------------------------------------------------------------
# WACP-3xx — Schema / business data validation errors (§15.2)
# ---------------------------------------------------------------------------
WACP_301 = WacpErrorCode(
    "WACP-301", "Workflow schema not found for workflow_code/workflow_version.", 404
)
WACP_302 = WacpErrorCode("WACP-302", "Business data missing required field(s).", 422)
WACP_303 = WacpErrorCode("WACP-303", "Business data field type mismatch.", 422)
WACP_304 = WacpErrorCode("WACP-304", "Business data failed custom schema rule.", 422)
WACP_305 = WacpErrorCode(
    "WACP-305", "Business data failed schema validation.", 422
)

# ---------------------------------------------------------------------------
# WACP-4xx — Workflow / routing errors (§15.2)
# ---------------------------------------------------------------------------
WACP_401 = WacpErrorCode("WACP-401", "Workflow not found.", 404)
WACP_402 = WacpErrorCode("WACP-402", "Workflow version not found.", 404)
WACP_403 = WacpErrorCode("WACP-403", "Invalid state for requested operation.", 409)

# ---------------------------------------------------------------------------
# WACP-5xx — Job lifecycle errors (§15.2)
# ---------------------------------------------------------------------------
WACP_501 = WacpErrorCode("WACP-501", "Job not found.", 404)
WACP_502 = WacpErrorCode("WACP-502", "Job already in a terminal state.", 409)

# ---------------------------------------------------------------------------
# WACP-9xx — Internal errors (§15.2)
# ---------------------------------------------------------------------------
WACP_901 = WacpErrorCode("WACP-901", "Internal error.", 500)
WACP_902 = WacpErrorCode("WACP-902", "Workflow Runtime unavailable.", 503)


#: Every defined code, keyed by its string, for lookup from a wire-format
#: error object (§14.3) back to its HTTP status / default message.
ERROR_CODE_TABLE: dict[str, WacpErrorCode] = {
    c.code: c
    for c in (
        WACP_101,
        WACP_102,
        WACP_103,
        WACP_104,
        WACP_201,
        WACP_202,
        WACP_203,
        WACP_204,
        WACP_301,
        WACP_302,
        WACP_303,
        WACP_304,
        WACP_305,
        WACP_401,
        WACP_402,
        WACP_403,
        WACP_501,
        WACP_502,
        WACP_901,
        WACP_902,
    )
}


def lookup_error_code(code: str) -> Optional[WacpErrorCode]:
    """Returns the `WacpErrorCode` for a wire-format code string (e.g.
    "WACP-305"), or None if the code is not recognized by this SDK version.
    An unrecognized code is not necessarily invalid — a newer server minor
    version may have added a code this SDK predates (§20.2); callers should
    treat None as "unknown to this SDK", not "malformed".
    """

    return ERROR_CODE_TABLE.get(code)


# ---------------------------------------------------------------------------
# Exception hierarchy (§9.4 of 20_WACP_SDK_ARCHITECTURE.md)
# ---------------------------------------------------------------------------


@dataclass
class FieldError:
    """10_WACP_PROTOCOL.md §14.3 — a single entry in `field_errors`."""

    path: str
    message: str


class WacpError(Exception):
    """Root of every exception this SDK raises. Carries the originating
    WacpErrorCode so callers can catch by class (category) or inspect
    `.error_code.code` (specific WACP-xxx value) as needed.
    """

    def __init__(
        self,
        error_code: WacpErrorCode,
        message: Optional[str] = None,
        *,
        details: Optional[list[str]] = None,
        field_errors: Optional[list[FieldError]] = None,
    ) -> None:
        self.error_code = error_code
        self.message = message or error_code.default_message
        self.details = details or []
        self.field_errors = field_errors or []
        super().__init__(self.message)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"{type(self).__name__}({self.error_code.code}: {self.message!r})"


class WacpEnvelopeError(WacpError):
    """WACP-1xx — malformed envelope, unsupported version, duplicate
    request, oversize payload (§15.2)."""


class WacpAuthenticationError(WacpError):
    """WACP-2xx — authentication/authorization failures (§15.2, §16.3)."""


class WacpValidationError(WacpError):
    """WACP-3xx — schema/business data validation failures (§15.2)."""


class WacpWorkflowError(WacpError):
    """WACP-4xx — workflow/routing errors (§15.2)."""


class WacpLifecycleError(WacpError):
    """WACP-5xx — job lifecycle errors (§15.2)."""


class WacpInternalError(WacpError):
    """WACP-9xx — internal errors (§15.2)."""


#: Maps each error code's category prefix to the exception class that
#: should wrap it. Used by serialization/response-building code that turns
#: a wire-format `error.code` string into the correct typed exception,
#: rather than every caller re-implementing this dispatch themselves.
_CATEGORY_EXCEPTION_MAP: dict[str, type[WacpError]] = {
    "WACP-1": WacpEnvelopeError,
    "WACP-2": WacpAuthenticationError,
    "WACP-3": WacpValidationError,
    "WACP-4": WacpWorkflowError,
    "WACP-5": WacpLifecycleError,
    "WACP-9": WacpInternalError,
}


def exception_for_code(code: str) -> type[WacpError]:
    """Returns the exception class appropriate for a given WACP-xxx code's
    category (first digit after "WACP-"). Falls back to the base
    `WacpError` for a code whose category prefix is unrecognized (forward
    compatibility with a future minor version's new category), rather than
    raising a lookup error while the caller is already handling an error
    condition.
    """

    for prefix, exc_type in _CATEGORY_EXCEPTION_MAP.items():
        if code.startswith(prefix):
            return exc_type
    return WacpError


__all__ = [
    "WacpErrorCode",
    "WACP_101",
    "WACP_102",
    "WACP_103",
    "WACP_104",
    "WACP_201",
    "WACP_202",
    "WACP_203",
    "WACP_204",
    "WACP_301",
    "WACP_302",
    "WACP_303",
    "WACP_304",
    "WACP_305",
    "WACP_401",
    "WACP_402",
    "WACP_403",
    "WACP_501",
    "WACP_502",
    "WACP_901",
    "WACP_902",
    "ERROR_CODE_TABLE",
    "lookup_error_code",
    "FieldError",
    "WacpError",
    "WacpEnvelopeError",
    "WacpAuthenticationError",
    "WacpValidationError",
    "WacpWorkflowError",
    "WacpLifecycleError",
    "WacpInternalError",
    "exception_for_code",
]
