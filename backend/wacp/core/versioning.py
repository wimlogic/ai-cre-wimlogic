"""wacp.core.versioning

Protocol version constants live in wacp.core.constants; this module adds
the behavior around them: parsing/comparing semantic versions and checking
whether a given protocol version is supported, per 10_WACP_PROTOCOL.md
§20 and §20.4.

Used by wacp.client.diagnostics (checking a discovered server's supported
versions against this SDK's own) and wacp.server.protocol (rejecting an
incoming request's wacp.version as WACP-102 if unsupported).

Depends on wacp.core.constants and wacp.core.errors. No dependency on
wacp.client or wacp.server.
"""

from __future__ import annotations

from dataclasses import dataclass

from wacp.core.constants import SUPPORTED_PROTOCOL_VERSIONS
from wacp.core.errors import WACP_102, WacpEnvelopeError


@dataclass(frozen=True, order=True)
class SemanticVersion:
    """A parsed MAJOR.MINOR[.PATCH] version, per 10_WACP_PROTOCOL.md §20.2.

    Protocol versions are transmitted as MAJOR.MINOR (§20.2); PATCH
    defaults to 0 when absent, since a patch difference never affects
    wire-format compatibility.
    """

    major: int
    minor: int
    patch: int = 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


def parse_version(value: str) -> SemanticVersion:
    """Parses a version string like "1.0" or "1.0.3" into a
    SemanticVersion. Raises WacpEnvelopeError (WACP-102) if `value` is not
    a well-formed MAJOR.MINOR[.PATCH] string, since a malformed version
    string is, in practice, always encountered while checking protocol
    version support.
    """

    parts = value.split(".")
    if len(parts) not in (2, 3):
        raise WacpEnvelopeError(WACP_102, f"Malformed protocol version: {value!r}.")
    try:
        numeric_parts = [int(p) for p in parts]
    except ValueError as exc:
        raise WacpEnvelopeError(
            WACP_102, f"Malformed protocol version: {value!r}."
        ) from exc

    major, minor = numeric_parts[0], numeric_parts[1]
    patch = numeric_parts[2] if len(numeric_parts) == 3 else 0
    return SemanticVersion(major=major, minor=minor, patch=patch)


def is_supported_version(
    value: str, supported: tuple[str, ...] = SUPPORTED_PROTOCOL_VERSIONS
) -> bool:
    """Returns True if `value` (e.g. "1.0") is among `supported` protocol
    versions. Per §20.2, minor versions are additive-only, so a client
    built for 1.0 remains compatible with a server advertising 1.1+; this
    function still checks against an explicit `supported` set rather than
    assuming that forward compatibility automatically, since the actual
    compatibility guarantee is a property of the two SDKs involved, not of
    version numbers alone (see 20_WACP_SDK_ARCHITECTURE.md §8.3
    compatibility matrix, which governs this in practice).
    """

    return value in supported


def is_same_major(a: str, b: str) -> bool:
    """Returns True if versions `a` and `b` share the same MAJOR
    component, i.e. are expected to be wire-compatible per §20.2's rule
    that only MAJOR bumps may break compatibility.
    """

    return parse_version(a).major == parse_version(b).major


def require_supported_version(
    value: str, supported: tuple[str, ...] = SUPPORTED_PROTOCOL_VERSIONS
) -> None:
    """Raises WacpEnvelopeError (WACP-102) if `value` is not in
    `supported`. Used by wacp.server.protocol to reject an unsupported
    wacp.version before any further processing (§20.4).
    """

    if not is_supported_version(value, supported):
        raise WacpEnvelopeError(
            WACP_102,
            f"Unsupported protocol version: {value!r}. Supported: {list(supported)}.",
        )


__all__ = [
    "SemanticVersion",
    "parse_version",
    "is_supported_version",
    "is_same_major",
    "require_supported_version",
]
