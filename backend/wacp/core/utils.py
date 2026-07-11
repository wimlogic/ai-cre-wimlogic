"""wacp.core.utils

Technology-level helpers with no protocol opinion of their own: request ID
generation (UUIDv7, per 10_WACP_PROTOCOL.md §18.1's "UUIDv7 preferred, or
ULID" — sequential/date-prefixed IDs are prohibited), ISO 8601 UTC
timestamp formatting, and the generic HMAC-SHA256 signing/verification
primitive used by callback construction (server-side sign) and callback
verification (client-side verify), per §17.3.

Generated here once, so wacp.server.callback (sign) and wacp.client.callback
(verify) use the identical implementation rather than two independent HMAC
constructions that could subtly diverge (e.g. differing on what exactly
gets signed).

Depends only on the Python standard library. No dependency on any other
wacp module, wacp.client, or wacp.server.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Request ID generation (10_WACP_PROTOCOL.md §18.1)
# ---------------------------------------------------------------------------


def generate_request_id() -> str:
    """Generates a UUIDv7 string: a time-ordered, RFC 9562 compliant
    identifier, per §18.1's preference. UUIDv7 embeds a 48-bit Unix
    timestamp (milliseconds) in the most significant bits followed by
    random bits, so identifiers generated later sort after identifiers
    generated earlier without leaking a predictable sequence number the
    way a date-prefixed sequential ID would (the exact failure mode §18.1
    prohibits).

    Python's standard `uuid` module does not provide UUIDv7 as of this
    SDK's target versions, so it is implemented directly here per RFC 9562
    §5.7, rather than adding a third-party dependency to wacp.core
    (20_WACP_SDK_ARCHITECTURE.md §4.1 keeps Core minimal).
    """

    unix_ts_ms = int(time.time() * 1000) & 0xFFFFFFFFFFFF  # 48 bits
    rand_bytes = os.urandom(10)  # 80 bits of randomness

    # Layout (RFC 9562 §5.7):
    #   48 bits: unix_ts_ms
    #    4 bits: version (0111 = 7)
    #   12 bits: random
    #    2 bits: variant (10)
    #   62 bits: random
    time_hex = f"{unix_ts_ms:012x}"

    rand_a = int.from_bytes(rand_bytes[0:2], "big") & 0x0FFF  # 12 bits
    rand_a_hex = f"{(0x7000 | rand_a):04x}"  # version nibble = 7

    variant_and_rand_b = int.from_bytes(rand_bytes[2:10], "big")
    # Force the two most significant bits of this 64-bit field to '10'
    # (variant per RFC 9562 §4.1), leaving 62 bits of randomness.
    variant_and_rand_b &= 0x3FFFFFFFFFFFFFFF
    variant_and_rand_b |= 0x8000000000000000
    variant_hex = f"{variant_and_rand_b:016x}"

    return (
        f"{time_hex[0:8]}-{time_hex[8:12]}-{rand_a_hex}-"
        f"{variant_hex[0:4]}-{variant_hex[4:16]}"
    )


def is_valid_request_id(value: str) -> bool:
    """Structural check that `value` is a well-formed UUID (any RFC 4122 /
    9562 version) or a well-formed ULID. §18.1 requires UUIDv7 or ULID
    specifically for *generation*, but this checker is deliberately lenient
    about accepting any syntactically valid UUID on *receipt* — a stricter,
    version-7-only check would reject a still-technically-valid identifier
    from a future SDK revision that generates UUIDv8, for instance. Servers
    that want to strictly enforce v7-only generation should validate at the
    point of their own request_id issuance, not here.
    """

    return _is_valid_uuid(value) or _is_valid_ulid(value)


def _is_valid_uuid(value: str) -> bool:
    parts = value.split("-")
    if len(parts) != 5:
        return False
    lengths = [len(p) for p in parts]
    if lengths != [8, 4, 4, 4, 12]:
        return False
    try:
        int(value.replace("-", ""), 16)
    except ValueError:
        return False
    return True


_ULID_ALPHABET = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")


def _is_valid_ulid(value: str) -> bool:
    if len(value) != 26:
        return False
    return all(ch in _ULID_ALPHABET for ch in value.upper())


# ---------------------------------------------------------------------------
# Timestamps (10_WACP_PROTOCOL.md §7.2, §17.3)
# ---------------------------------------------------------------------------


def current_timestamp() -> str:
    """Returns the current time as an ISO 8601 UTC string with a literal
    'Z' suffix (e.g. "2026-07-08T14:32:00Z"), matching every timestamp
    example in 10_WACP_PROTOCOL.md.
    """

    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def parse_timestamp(value: str) -> datetime:
    """Parses an ISO 8601 timestamp (with a 'Z' or explicit offset suffix)
    into a timezone-aware `datetime`. Raises `ValueError` if `value` is not
    a valid ISO 8601 string — callers that need a WACP-101 on malformed
    input translate that ValueError themselves (core.utils has no
    dependency on core.errors, keeping this module dependency-free).
    """

    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def seconds_since(value: str) -> float:
    """Returns the number of seconds elapsed between the ISO 8601
    timestamp `value` and now. Used by callback replay-window checks
    (§17.3) against CALLBACK_REPLAY_WINDOW_SECONDS.
    """

    then = parse_timestamp(value)
    now = datetime.now(timezone.utc)
    return (now - then).total_seconds()


# ---------------------------------------------------------------------------
# HMAC signing / verification (10_WACP_PROTOCOL.md §17.3)
# ---------------------------------------------------------------------------


def sign_hmac_sha256(secret: str, payload: bytes) -> str:
    """Computes the HMAC-SHA256 signature of `payload`, keyed with
    `secret`, returned as a lowercase hex digest. This is the exact
    computation used both to build X-WACP-Callback-Signature
    (wacp.server.callback) and to verify it (wacp.client.callback) — one
    implementation, so the two sides can never disagree on how the
    signature is constructed.
    """

    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def verify_hmac_sha256(secret: str, payload: bytes, signature: str) -> bool:
    """Verifies `signature` against `payload` signed with `secret`, using a
    constant-time comparison (per the same anti-timing-attack principle
    10_WACP_PROTOCOL.md §16.2 requires for api_secret verification).
    """

    expected = sign_hmac_sha256(secret, payload)
    return hmac.compare_digest(expected, signature)


__all__ = [
    "generate_request_id",
    "is_valid_request_id",
    "current_timestamp",
    "parse_timestamp",
    "seconds_since",
    "sign_hmac_sha256",
    "verify_hmac_sha256",
]
