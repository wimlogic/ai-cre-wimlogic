"""wacp.client.config

`ClientConfig`: everything a WACP Client instance needs to know about how
to reach a DEV-TOOLS deployment and how to behave while doing so --
base URL, credentials, timeouts, retry behavior, and SSL verification.

This is the natural first Client module: every other Client module
(auth header construction, the HTTP pipeline, job submission, polling,
callback verification) takes a `ClientConfig` as an input, but this module
itself depends on nothing Client-specific -- only on protocol-level
constants and version support checking already defined in wacp.core.

This module validates *configuration values themselves* (is base_url a
valid HTTPS URL, is timeout_seconds positive) -- not the WACP envelope or
wire format, which is wacp.core.validation's job. Configuration errors are
programmer/deployment errors, not protocol errors, so they raise plain
`ValueError`/`TypeError` rather than a `WacpError` subclass -- a
malformed `base_url` is never something a DEV-TOOLS server response could
plausibly signal back with a WACP-xxx code.

Depends on wacp.core.constants (default protocol version, backoff
defaults) and wacp.core.versioning (validating the configured protocol
version is one this SDK understands). No dependency on any other
wacp.client module, wacp.server, or any Business Application package.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from wacp.core.constants import CURRENT_PROTOCOL_VERSION
from wacp.core.versioning import is_supported_version


@dataclass(frozen=True)
class RetryConfig:
    """Client-side retry behavior for transient failures (429, 503,
    connection errors), per 10_WACP_PROTOCOL.md §18.3. This governs HTTP
    transport-level retries -- it is distinct from, and unrelated to,
    server-side callback delivery retries (§17.4), which are a DEV-TOOLS
    concern the Client SDK has no control over.
    """

    max_attempts: int = 5
    initial_backoff_seconds: float = 0.5
    max_backoff_seconds: float = 30.0
    backoff_multiplier: float = 2.0
    jitter: bool = True

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")
        if self.initial_backoff_seconds <= 0:
            raise ValueError("initial_backoff_seconds must be positive.")
        if self.max_backoff_seconds < self.initial_backoff_seconds:
            raise ValueError(
                "max_backoff_seconds must be >= initial_backoff_seconds."
            )
        if self.backoff_multiplier <= 1.0:
            raise ValueError("backoff_multiplier must be greater than 1.0.")


@dataclass(frozen=True)
class ClientConfig:
    """Configuration for a single WACP Client instance, i.e. a single
    Business Application's connection to a single DEV-TOOLS deployment.

    `application_id`, `api_key`, and `api_secret` are the same credential
    triple used to build the `X-WACP-*` authentication headers
    (10_WACP_PROTOCOL.md §8, §16.1) and, for `api_secret`, to verify
    inbound callback signatures (§17.3) -- one secret serves both roles,
    matching the protocol's own design (the callback signature is keyed
    with the *receiving application's* api_secret, not a separate value).
    """

    base_url: str
    application_id: str
    api_key: str
    api_secret: str
    protocol_version: str = CURRENT_PROTOCOL_VERSION
    timeout_seconds: float = 30.0
    verify_ssl: bool = True
    retry: RetryConfig = field(default_factory=RetryConfig)

    def __post_init__(self) -> None:
        if not self.base_url:
            raise ValueError("base_url must not be empty.")
        if not self.base_url.startswith("https://"):
            raise ValueError(
                "base_url must be an HTTPS URL "
                "(10_WACP_PROTOCOL.md §16.3 transport requirement)."
            )
        if self.base_url.endswith("/"):
            # Stored without a trailing slash so every Client module can
            # safely do f"{base_url}{path}" without producing "//".
            object.__setattr__(self, "base_url", self.base_url.rstrip("/"))

        if not self.application_id:
            raise ValueError("application_id must not be empty.")
        if not self.api_key:
            raise ValueError("api_key must not be empty.")
        if not self.api_secret:
            raise ValueError("api_secret must not be empty.")

        if not is_supported_version(self.protocol_version):
            raise ValueError(
                f"protocol_version {self.protocol_version!r} is not supported "
                "by this SDK release."
            )

        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")

        if not self.verify_ssl:
            # Disabling TLS verification directly contradicts
            # 10_WACP_PROTOCOL.md §16.3 ("TLS 1.2 or higher is mandatory").
            # This is not blocked outright -- a local/dev DEV-TOOLS
            # instance behind a self-signed cert is a legitimate,
            # narrow case -- but it must be an explicit, visible choice,
            # not a silent default, so it is surfaced as a warning rather
            # than silently accepted.
            import warnings

            warnings.warn(
                "verify_ssl=False disables TLS certificate verification. "
                "10_WACP_PROTOCOL.md §16.3 requires TLS 1.2+ for all WACP "
                "traffic; only use this for local development against a "
                "self-signed DEV-TOOLS instance, never in production.",
                stacklevel=2,
            )


__all__ = ["ClientConfig", "RetryConfig"]
