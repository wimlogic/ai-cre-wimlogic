"""wacp.client.callback

Callback Verification: verifies an inbound callback per
10_WACP_PROTOCOL.md §17.3 -- HMAC-SHA256 signature check (constant-time),
replay-window timestamp check, and envelope shape validation.

This module performs zero cryptographic implementation of its own. The
HMAC construction and its constant-time comparison already exist as
wacp.core.utils.sign_hmac_sha256 / verify_hmac_sha256 (approved in Phase
1) -- this module only calls them with the right inputs (the receiving
application's own api_secret, keyed the same way DEV-TOOLS's Server SDK
keys it when building the callback). Likewise, timestamp parsing reuses
wacp.core.utils.parse_timestamp/seconds_since, and envelope shape
decoding reuses wacp.core.serialization.dict_to_response -- nothing here
re-implements what Core already validates.

This is the last protocol-sensitive Client module: it depends only on
wacp.core (constants, utils, serialization, dto) and wacp.client.config
(for the receiving application's api_secret). No dependency on
wacp.client.http, wacp.client.builder, wacp.client.submission,
wacp.client.status, wacp.client.results, wacp.server, DEV-TOOLS, or any
Business Application package -- verifying a callback never involves
sending an HTTP request.
"""

from __future__ import annotations

import json as json_module

from wacp.client.config import ClientConfig
from wacp.core.constants import (
    CALLBACK_REPLAY_WINDOW_SECONDS,
    HEADER_CALLBACK_SIGNATURE,
    HEADER_CALLBACK_TIMESTAMP,
)
from wacp.core.dto import WacpResponse
from wacp.core.errors import WACP_101, WacpEnvelopeError
from wacp.core.serialization import dict_to_response
from wacp.core.utils import seconds_since, verify_hmac_sha256


class CallbackVerificationError(Exception):
    """Raised when an inbound callback fails signature, replay-window, or
    timestamp-format verification.

    Deliberately NOT a wacp.core.errors.WacpError subclass, for the same
    reason wacp.client.http.HttpRetriesExhaustedError and
    wacp.client.status.JobWaitTimeoutError are not: this is not a
    WACP-xxx protocol fact DEV-TOOLS reported about a *request* -- it is
    this Business Application's own local security judgment about an
    *inbound* callback it received, e.g. from a party impersonating
    DEV-TOOLS or replaying an old callback. There is no WACP-xxx code for
    "I don't trust this callback"; that determination is made entirely on
    the receiving side.
    """


class CallbackVerifier:
    """Verifies inbound WACP callbacks for one Business Application,
    keyed with that application's own api_secret -- the same secret used
    to build the outgoing X-WACP-Api-Secret authentication header
    (§16.1), per the callback contract's design (§17.3: the signature is
    keyed with the *receiving application's* api_secret, not a separate
    value).
    """

    def __init__(self, config: ClientConfig) -> None:
        self._config = config

    def verify(
        self,
        *,
        raw_body: bytes,
        headers: dict[str, str],
    ) -> WacpResponse:
        """Verifies and parses an inbound callback.

        Performs, in order:

        1. Header extraction -- requires both HEADER_CALLBACK_SIGNATURE
           and HEADER_CALLBACK_TIMESTAMP to be present.
        2. Timestamp format validation -- reuses
           wacp.core.utils.seconds_since (which itself reuses
           parse_timestamp), rather than re-parsing ISO 8601 here.
        3. Replay protection -- rejects a callback whose timestamp is
           older than CALLBACK_REPLAY_WINDOW_SECONDS (§17.3), using
           Core's own constant rather than a locally redefined value.
        4. Signature verification -- reuses
           wacp.core.utils.verify_hmac_sha256 (constant-time comparison
           already built in; not reimplemented here), keyed with this
           Business Application's own api_secret, computed over the exact
           raw request body bytes.
        5. Envelope shape validation -- reuses
           wacp.core.serialization.dict_to_response, which raises
           WacpEnvelopeError (WACP-101) on structural problems; that
           exception propagates unchanged, exactly as it does everywhere
           else a WacpResponse is decoded.

        Raises CallbackVerificationError for any header, replay, or
        signature failure (steps 1-4). Raises WacpEnvelopeError (from
        Core) for a malformed or structurally invalid body (step 5),
        matching how every other WACP body decode failure is surfaced
        across this SDK.

        Returns the parsed WacpResponse only once every check has passed.
        """

        signature = headers.get(HEADER_CALLBACK_SIGNATURE)
        timestamp = headers.get(HEADER_CALLBACK_TIMESTAMP)

        if not signature:
            raise CallbackVerificationError(
                f"Missing required header: {HEADER_CALLBACK_SIGNATURE}."
            )
        if not timestamp:
            raise CallbackVerificationError(
                f"Missing required header: {HEADER_CALLBACK_TIMESTAMP}."
            )

        try:
            age_seconds = seconds_since(timestamp)
        except ValueError as exc:
            raise CallbackVerificationError(
                f"{HEADER_CALLBACK_TIMESTAMP} is not a valid ISO 8601 timestamp: "
                f"{timestamp!r}."
            ) from exc

        if age_seconds > CALLBACK_REPLAY_WINDOW_SECONDS:
            raise CallbackVerificationError(
                f"Callback timestamp is {age_seconds:.0f}s old, exceeding the "
                f"{CALLBACK_REPLAY_WINDOW_SECONDS}s replay window (§17.3)."
            )
        if age_seconds < -CALLBACK_REPLAY_WINDOW_SECONDS:
            # A timestamp far in the future is just as suspicious as one
            # far in the past -- neither is a legitimate clock-skew case
            # within the replay window.
            raise CallbackVerificationError(
                f"Callback timestamp is {-age_seconds:.0f}s in the future, "
                f"outside the {CALLBACK_REPLAY_WINDOW_SECONDS}s replay window (§17.3)."
            )

        if not verify_hmac_sha256(self._config.api_secret, raw_body, signature):
            raise CallbackVerificationError(
                "Callback signature verification failed: computed HMAC-SHA256 "
                "does not match the provided signature."
            )

        try:
            payload = json_module.loads(raw_body)
        except json_module.JSONDecodeError as exc:
            raise WacpEnvelopeError(WACP_101, "Callback body is not valid JSON.") from exc

        return dict_to_response(payload)  # raises WacpEnvelopeError on structural problems


__all__ = ["CallbackVerifier", "CallbackVerificationError"]
