"""wacp.core.validation

Envelope-shape validation only, per 10_WACP_PROTOCOL.md §7/§18/§20 and
20_WACP_SDK_ARCHITECTURE.md §4.2: are required fields present, are types
correct, is request_id a well-formed UUIDv7/ULID, is timestamp valid ISO
8601, is the protocol version supported.

This module NEVER validates business `data` content against a workflow
schema. That is DEV-TOOLS's Schema Registry responsibility
(10_WACP_PROTOCOL.md §10) and is intentionally out of SDK scope entirely --
not merely out of wacp.core, but out of the SDK altogether. No function
here inspects the *contents* of `data`, only that it is present as a
mapping (already enforced structurally at deserialization time in
wacp.core.serialization).

wacp.core.serialization already performs basic structural decoding
(required fields present, correct block types). This module adds the
additional checks that go beyond "does it parse": well-formed request_id,
well-formed timestamp, and supported protocol version -- checks that
require values to be semantically well-formed, not just present.

Depends on wacp.core.dto, wacp.core.errors, wacp.core.utils, and
wacp.core.versioning. No dependency on wacp.client or wacp.server.
"""

from __future__ import annotations

from typing import Sequence

from wacp.core.constants import SUPPORTED_PROTOCOL_VERSIONS
from wacp.core.dto import WacpEnvelope
from wacp.core.errors import WACP_101, WACP_102, WacpEnvelopeError
from wacp.core.utils import is_valid_request_id, parse_timestamp
from wacp.core.versioning import require_supported_version


def validate_envelope(
    envelope: WacpEnvelope,
    *,
    supported_protocol_versions: Sequence[str] = SUPPORTED_PROTOCOL_VERSIONS,
) -> None:
    """Validates an already-deserialized WacpEnvelope's field values
    beyond structural presence/type (which wacp.core.serialization already
    enforces at decode time). Raises WacpEnvelopeError on the first
    problem found:

    - WACP-101 if request_id is not a well-formed UUIDv7/ULID (§18.1)
    - WACP-101 if timestamp is not valid ISO 8601 (§7.2)
    - WACP-101 if any of application_id/company_id/project_code/
      workflow_code is an empty string (present per serialization, but
      structurally meaningless if blank)
    - WACP-102 if version is not a protocol version this SDK supports
      (§20.4)

    `supported_protocol_versions` defaults to this SDK release's own
    SUPPORTED_PROTOCOL_VERSIONS (unchanged from prior behavior -- every
    existing caller continues to work identically), but accepts an
    override so a deployment-specific supported set (e.g. a DEV-TOOLS
    deployment temporarily accepting an additional minor version) can
    flow through this check too. This mirrors the same override already
    supported by wacp.core.versioning.require_supported_version and
    wacp.server.protocol.validate_protocol_version, so the SDK still
    defines protocol behavior while a deployment decides its own policy.
    """

    if not envelope.application_id:
        raise WacpEnvelopeError(WACP_101, "application_id must not be empty.")
    if not envelope.company_id:
        raise WacpEnvelopeError(WACP_101, "company_id must not be empty.")
    if not envelope.project_code:
        raise WacpEnvelopeError(WACP_101, "project_code must not be empty.")
    if not envelope.workflow_code:
        raise WacpEnvelopeError(WACP_101, "workflow_code must not be empty.")

    if not is_valid_request_id(envelope.request_id):
        raise WacpEnvelopeError(
            WACP_101, f"request_id is not a well-formed UUIDv7/ULID: {envelope.request_id!r}."
        )

    try:
        parse_timestamp(envelope.timestamp)
    except ValueError as exc:
        raise WacpEnvelopeError(
            WACP_101, f"timestamp is not valid ISO 8601: {envelope.timestamp!r}."
        ) from exc

    # WACP-102, not WACP-101: an otherwise well-formed envelope speaking an
    # unsupported protocol version is a version problem, not a shape
    # problem (§15.2 distinguishes these deliberately).
    require_supported_version(envelope.version, supported=tuple(supported_protocol_versions))

    if envelope.callback_url is not None and not envelope.callback_url.startswith("https://"):
        raise WacpEnvelopeError(
            WACP_101, "callback_url must be an HTTPS URL (§16.3 transport requirement)."
        )


def is_envelope_valid(
    envelope: WacpEnvelope,
    *,
    supported_protocol_versions: Sequence[str] = SUPPORTED_PROTOCOL_VERSIONS,
) -> bool:
    """Non-raising convenience wrapper around validate_envelope, for
    callers that want a boolean rather than a caught exception.
    """

    try:
        validate_envelope(envelope, supported_protocol_versions=supported_protocol_versions)
        return True
    except WacpEnvelopeError:
        return False


__all__ = ["validate_envelope", "is_envelope_valid"]
