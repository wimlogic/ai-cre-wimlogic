"""wacp.client.diagnostics

Connection Testing / Diagnostics: get_meta(), test_connection(), per
10_WACP_PROTOCOL.md §13.1 (GET /wacp/v1/meta) and §13.4 (the locked Meta
Discovery Response Contract) and §20.4 (a client checking a discovered
server's supported protocol versions).

The Meta Discovery response shape is now fully locked in
10_WACP_PROTOCOL.md §13.4 -- this module parses exactly that shape
(`protocol_version`, `protocol_versions_supported`, `sdk_minimum_version`,
`sdk_latest_version`, `deprecated_protocol_versions`, `server_name`,
`server_version`, `timestamp`), all eight fields required, matching what
wacp.server will implement on the other side of this same endpoint in
Phase 3. This replaces the earlier, self-documented assumption that
existed before this contract was locked.

For error responses (non-2xx), this module reuses
wacp.client.errors.parse_wacp_response exactly as every other module
does, since §15's error object shape is endpoint-independent (§13.4:
"there is no meta-specific error format"). Only the *success* body shape
is meta-specific and therefore parsed here rather than through the shared
response translation path -- a success body here is not a WacpResponse
(it has no job_id, no JobStatus-valued `status`), so
wacp.core.serialization.dict_to_response would not apply.

Depends on wacp.client.http (HttpClient, HttpError), wacp.client.errors
(parse_wacp_response, for the error path only), wacp.client.config
(ClientConfig), wacp.core.constants (WACP_META_PATH), wacp.core.errors
(WacpEnvelopeError, WacpInternalError and their codes), and
wacp.core.versioning (is_supported_version, reused rather than
reimplemented). No dependency on wacp.client.builder,
wacp.client.submission, wacp.client.status, wacp.client.results,
wacp.client.callback, wacp.server, DEV-TOOLS, or any Business Application
package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from wacp.client.config import ClientConfig
from wacp.client.errors import parse_wacp_response
from wacp.client.http import HttpClient, HttpError
from wacp.core.constants import WACP_META_PATH
from wacp.core.errors import WACP_101, WACP_901, WacpEnvelopeError, WacpInternalError
from wacp.core.versioning import is_supported_version

#: Every field 10_WACP_PROTOCOL.md §13.4 requires in a successful
#: GET /wacp/v1/meta response. A response missing any of these is a
#: malformed protocol message (WACP-101), per §13.4's own text.
_REQUIRED_META_FIELDS = (
    "protocol_version",
    "protocol_versions_supported",
    "sdk_minimum_version",
    "sdk_latest_version",
    "deprecated_protocol_versions",
    "server_name",
    "server_version",
    "timestamp",
)


@dataclass(frozen=True)
class ServerMeta:
    """Parsed content of a successful GET /wacp/v1/meta response, per the
    locked contract in 10_WACP_PROTOCOL.md §13.4.
    """

    protocol_version: str
    protocol_versions_supported: tuple[str, ...]
    sdk_minimum_version: str
    sdk_latest_version: str
    deprecated_protocol_versions: tuple[str, ...]
    server_name: str
    server_version: str
    timestamp: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConnectionTestResult:
    """Result of test_connection(): a single, non-raising diagnostic call
    suitable for a startup check or a health-check endpoint, so a caller
    doesn't need a try/except just to know whether DEV-TOOLS is reachable
    and speaking a compatible protocol version.
    """

    reachable: bool
    protocol_compatible: Optional[bool]  # None if unreachable / meta could not be parsed
    protocol_version_deprecated: Optional[bool]  # None if unreachable; True if this client's configured version is scheduled for removal
    meta: Optional[ServerMeta]
    error: Optional[str]


class ConnectionDiagnostics:
    """Coordinates HttpClient and the Client Error Handling module into
    get_meta() and test_connection(). Holds no protocol logic of its own
    beyond parsing the locked Meta Discovery contract (§13.4).
    """

    def __init__(self, http_client: HttpClient, config: ClientConfig) -> None:
        self._http = http_client
        self._config = config

    def get_meta(self) -> ServerMeta:
        """Retrieves and parses server metadata: GET /wacp/v1/meta
        (§13.1, §13.4). Raises the appropriate wacp.core.errors exception
        (via parse_wacp_response) if the server returns a non-2xx WACP
        error response. Raises WacpEnvelopeError (WACP-101) if a 2xx
        response is missing any of the eight required fields (§13.4).
        Raises WacpInternalError (WACP-901) if a 2xx response body is not
        valid JSON at all.
        """

        http_response = self._http.get(WACP_META_PATH)

        if not http_response.is_success:
            parse_wacp_response(http_response)  # raises the appropriate wacp.core.errors exception
            raise WacpInternalError(  # pragma: no cover - defensive; parse_wacp_response always raises above
                WACP_901,
                f"Meta endpoint returned HTTP {http_response.status_code} "
                "without a recognizable WACP error body.",
            )

        try:
            payload = http_response.json()
        except HttpError as exc:
            raise WacpInternalError(
                WACP_901, "Meta endpoint returned a response that could not be parsed as JSON."
            ) from exc

        missing = [f for f in _REQUIRED_META_FIELDS if f not in payload]
        if missing:
            raise WacpEnvelopeError(
                WACP_101,
                f"Meta response missing required field(s) per §13.4: {', '.join(missing)}.",
            )

        return ServerMeta(
            protocol_version=payload["protocol_version"],
            protocol_versions_supported=tuple(payload["protocol_versions_supported"]),
            sdk_minimum_version=payload["sdk_minimum_version"],
            sdk_latest_version=payload["sdk_latest_version"],
            deprecated_protocol_versions=tuple(payload["deprecated_protocol_versions"]),
            server_name=payload["server_name"],
            server_version=payload["server_version"],
            timestamp=payload["timestamp"],
            raw=payload,
        )

    def test_connection(self) -> ConnectionTestResult:
        """A single, non-raising connectivity + compatibility check.

        Attempts get_meta() and reports the outcome as data rather than
        an exception, so this method is safe to call from a startup
        health check without additional error handling. Transport
        failures (HttpError) and protocol-level failures (any exception
        from wacp.core.errors.WacpError, e.g. authentication rejected, or
        a malformed meta response) are both caught and reported via
        `reachable=False` and `error`; this is the one place in the
        Client SDK where catching a broad exception type is the intended
        behavior, precisely because this method's contract is "always
        returns, never raises".
        """

        try:
            meta = self.get_meta()
        except HttpError as exc:
            return ConnectionTestResult(
                reachable=False, protocol_compatible=None,
                protocol_version_deprecated=None, meta=None, error=str(exc),
            )
        except Exception as exc:  # noqa: BLE001 - intentional: see docstring
            return ConnectionTestResult(
                reachable=False, protocol_compatible=None,
                protocol_version_deprecated=None, meta=None, error=str(exc),
            )

        compatible = is_supported_version(
            self._config.protocol_version, supported=meta.protocol_versions_supported
        )
        deprecated = self._config.protocol_version in meta.deprecated_protocol_versions

        return ConnectionTestResult(
            reachable=True, protocol_compatible=compatible,
            protocol_version_deprecated=deprecated, meta=meta, error=None,
        )


__all__ = ["ConnectionDiagnostics", "ConnectionTestResult", "ServerMeta"]
