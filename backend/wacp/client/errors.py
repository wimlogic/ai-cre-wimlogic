"""wacp.client.errors

Client-side error handling: translates a raw HttpResponse (from
wacp.client.http, which has no protocol awareness) into either a parsed
WacpResponse (success or a still-informative non-2xx-but-well-formed
response) or the correct typed exception from wacp.core.errors, per
10_WACP_PROTOCOL.md §14.3 and §15.

This is the single place a WACP error response body is decoded and raised
as an exception. wacp.client.submission, wacp.client.polling, and
wacp.client.results (later modules) all call into this module rather than
each independently parsing `error.code` -- exactly the kind of shared
logic that keeps those modules thin orchestration layers rather than each
re-deriving response interpretation.

Depends on wacp.client.http (HttpResponse, HttpError -- reading the
transport result only, never sending a request itself) and wacp.core
(serialization, errors). No dependency on wacp.client.config,
wacp.client.builder, wacp.server, or any Business Application package.
"""

from __future__ import annotations

from typing import NoReturn

from wacp.client.http import HttpError, HttpResponse
from wacp.core.dto import WacpErrorDetail, WacpResponse
from wacp.core.errors import (
    WACP_901,
    WacpErrorCode,
    WacpInternalError,
    exception_for_code,
    lookup_error_code,
)
from wacp.core.serialization import dict_to_response


def parse_wacp_response(http_response: HttpResponse) -> WacpResponse:
    """Parses `http_response.body` as a WacpResponse (§14.1).

    - If the body is not valid JSON at all, raises WacpInternalError
      (WACP-901) -- this is not a WACP protocol error the server reported,
      it is DEV-TOOLS (or an intermediary, e.g. a proxy error page)
      failing to speak the protocol at all.
    - If the body is valid JSON but not a structurally valid WacpResponse,
      `wacp.core.serialization.dict_to_response` already raises
      WacpEnvelopeError (WACP-101); that propagates unchanged.
    - If the body is a well-formed WacpResponse whose `error` field is
      populated, raises the correctly typed exception via
      `raise_for_error` rather than returning it as data -- callers work
      with try/except, matching how a transport failure (HttpError) is
      already surfaced.
    - Otherwise (a well-formed WacpResponse with no `error`), returns the
      parsed WacpResponse normally.
    """

    try:
        payload = http_response.json()
    except HttpError as exc:
        raise WacpInternalError(
            WACP_901,
            f"Server returned a response that could not be parsed as JSON "
            f"(HTTP {http_response.status_code}).",
        ) from exc

    response = dict_to_response(payload)  # raises WacpEnvelopeError (WACP-101) if malformed

    if response.error is not None:
        raise_for_error(response.error, http_status=http_response.status_code)

    return response


def raise_for_error(error: WacpErrorDetail, *, http_status: int) -> NoReturn:
    """Raises the wacp.core.errors exception appropriate for `error.code`.

    If `error.code` is not recognized by this SDK release's error table
    (§20.2 -- a newer server minor version may have added a code this SDK
    predates), a WacpErrorCode is constructed on the fly from the
    observed HTTP status and the server-supplied message, rather than
    silently swallowing an error this SDK simply doesn't have a row for.
    The exception's category (and therefore its Python type) still comes
    from the code's own prefix via `exception_for_code`, so even an
    unrecognized *specific* code is still caught correctly by category
    (e.g. an unrecognized WACP-3xx code still raises WacpValidationError).
    """

    exc_type = exception_for_code(error.code)
    code_info = lookup_error_code(error.code)
    if code_info is None:
        code_info = WacpErrorCode(error.code, error.message, http_status)

    raise exc_type(
        code_info,
        error.message,
        details=error.details,
        field_errors=error.field_errors,
    )


__all__ = ["parse_wacp_response", "raise_for_error"]
