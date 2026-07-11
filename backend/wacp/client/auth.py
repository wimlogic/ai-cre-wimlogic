"""wacp.client.auth

Builds the HTTP headers that authenticate a WACP request, per
10_WACP_PROTOCOL.md §8 (Header Fields) and §16.1 (Authentication model).
This module produces headers only -- it never contacts the network and
never validates credentials against a server (that is the receiving
DEV-TOOLS Server SDK's job, per §16.2). Its only responsibility is: given
a ClientConfig, construct the exact header set the protocol requires.

Depends on wacp.core.constants (the canonical header names and content
type) and wacp.client.config (ClientConfig). No dependency on any other
wacp.client module, wacp.server, or any Business Application package.
"""

from __future__ import annotations

from wacp.client.config import ClientConfig
from wacp.core.constants import (
    CONTENT_TYPE,
    HEADER_API_KEY,
    HEADER_API_SECRET,
    HEADER_APPLICATION_ID,
    HEADER_PROTOCOL_VERSION,
)


def build_auth_headers(config: ClientConfig) -> dict[str, str]:
    """Builds the complete header set for an authenticated WACP request.

    Returns Content-Type plus the three required X-WACP-* credential
    headers (§8) and the optional X-WACP-Protocol-Version pin, set from
    `config.protocol_version` -- pinning explicitly rather than omitting
    it, so a DEV-TOOLS deployment supporting multiple protocol versions
    always knows unambiguously which version this client is speaking
    (§20.4), rather than inferring it from the envelope body alone.

    This function never inspects or logs `config.api_secret` beyond
    placing it in the header value -- it does not persist, echo, or
    include it in any exception message, per §16.4 ("Key and secret
    values are never logged").
    """

    return {
        "Content-Type": CONTENT_TYPE,
        HEADER_APPLICATION_ID: config.application_id,
        HEADER_API_KEY: config.api_key,
        HEADER_API_SECRET: config.api_secret,
        HEADER_PROTOCOL_VERSION: config.protocol_version,
    }


def redact_auth_headers(headers: dict[str, str]) -> dict[str, str]:
    """Returns a copy of a header dict with the API key and secret values
    replaced by a fixed redaction marker. Intended for use by
    wacp.client.logging (a later module) so that diagnostic output can
    show *that* auth headers were present and well-formed without ever
    printing their actual values -- the same "never logged" requirement
    build_auth_headers itself honors (§16.4).
    """

    redacted = dict(headers)
    for header_name in (HEADER_API_KEY, HEADER_API_SECRET):
        if header_name in redacted:
            redacted[header_name] = "***REDACTED***"
    return redacted


__all__ = ["build_auth_headers", "redact_auth_headers"]
