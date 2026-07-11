"""wacp.client.http

A generic, reusable HTTP request pipeline: GET/POST/PUT/DELETE, timeout
handling, retry with exponential backoff, authentication header
injection, and transport-level error translation.

This module knows nothing about jobs, status, results, or workflows. It
has no knowledge of the WACP envelope or response shapes at all -- it
sends and receives plain HTTP requests/responses with JSON-encodable
bodies. wacp.client.builder, wacp.client.submission, wacp.client.polling,
wacp.client.results, and wacp.client.diagnostics (all later modules) sit
on top of this pipeline and are the ones that know what a "job" is.

Retry applies only to what 10_WACP_PROTOCOL.md §18.3 identifies as
transient: connection failures, timeouts, HTTP 429, and HTTP 503. Every
other HTTP status (2xx, 4xx other than 429) is returned as a normal
HttpResponse without retrying and without raising -- interpreting a
non-2xx WACP response body (e.g. parsing a §14.3 error object) is a
protocol-aware concern that belongs in a higher module, not here.

Depends on wacp.client.auth (header injection) and wacp.client.config
(ClientConfig, RetryConfig). Uses only the Python standard library --
consistent with wacp.core's own "minimal, no unnecessary third-party
dependency" approach (20_WACP_SDK_ARCHITECTURE.md §4.1's spirit extended
to Client). No dependency on wacp.server, DEV-TOOLS, or any Business
Application package.
"""

from __future__ import annotations

import json as json_module
import random
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional

from wacp.client.auth import build_auth_headers
from wacp.client.config import ClientConfig, RetryConfig

#: HTTP statuses treated as transient/retryable, per §18.3 and §19.1
#: (429 rate limiting, 503 Workflow Runtime / service unavailable).
_RETRYABLE_STATUS_CODES = frozenset({429, 503})


# ---------------------------------------------------------------------------
# Exceptions -- transport-level only. These are deliberately NOT WacpError
# subclasses: a connection timeout is not a protocol fact the server
# communicated (there is no WACP-xxx code for "the request never arrived"),
# it is a fact about the transport attempt itself. Higher-level modules
# translate a *received* WACP error response body into the wacp.core.errors
# hierarchy; this module only ever fails to receive one.
# ---------------------------------------------------------------------------


class HttpError(Exception):
    """Base class for every exception this module raises."""


class HttpTimeoutError(HttpError):
    """The request did not complete within `config.timeout_seconds`."""


class HttpConnectionError(HttpError):
    """The request could not reach the server at all (DNS failure,
    connection refused, TLS handshake failure, etc.), as distinct from a
    timeout or a received-but-unsuccessful HTTP response.
    """


class HttpRetriesExhaustedError(HttpError):
    """Every configured retry attempt failed. Wraps the final underlying
    HttpError (timeout or connection error) as `__cause__`, or is raised
    directly if the final attempt returned a retryable status code with
    no further attempts remaining.
    """


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


@dataclass
class HttpResponse:
    """A completed HTTP exchange: the pipeline successfully sent the
    request and received *some* response, regardless of status code. A
    404 or 422 is just as much a valid HttpResponse as a 200 -- deciding
    what a given status code *means* in WACP terms is a higher-level
    module's job.
    """

    status_code: int
    headers: dict[str, str]
    body: bytes

    def text(self) -> str:
        return self.body.decode("utf-8")

    def json(self) -> Any:
        """Parses the response body as JSON. Raises `HttpError` (not a
        bare json.JSONDecodeError) if the body is not valid JSON, so
        callers catching this module's exceptions don't also need to
        catch stdlib JSON exceptions separately.
        """

        try:
            return json_module.loads(self.body)
        except json_module.JSONDecodeError as exc:
            raise HttpError(f"Response body is not valid JSON: {exc}") from exc

    @property
    def is_retryable_status(self) -> bool:
        return self.status_code in _RETRYABLE_STATUS_CODES

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300


# ---------------------------------------------------------------------------
# Backoff computation
# ---------------------------------------------------------------------------


def compute_backoff_seconds(attempt_number: int, retry: RetryConfig) -> float:
    """Computes the delay before retry attempt `attempt_number` (1-indexed:
    the delay before the *second* overall attempt is attempt_number=1),
    using exponential backoff capped at `retry.max_backoff_seconds`, with
    optional jitter (§18.3: "exponential backoff with jitter").
    """

    raw = retry.initial_backoff_seconds * (retry.backoff_multiplier ** (attempt_number - 1))
    capped = min(raw, retry.max_backoff_seconds)
    if not retry.jitter:
        return capped
    # Full jitter: uniform random value between 0 and the capped delay,
    # per the standard "full jitter" backoff strategy -- avoids every
    # retrying client waking up at exactly the same instant.
    return random.uniform(0, capped)


def _retry_after_seconds(response: HttpResponse) -> Optional[float]:
    """Extracts and parses a Retry-After header (§19.1) if present.
    Returns None if absent or unparseable as a plain integer/float number
    of seconds (HTTP-date form is not supported by this SDK release).
    """

    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------


class HttpClient:
    """A generic, retrying, authenticated HTTP client bound to one
    ClientConfig. This is the sole transport foundation for every
    higher-level Client module (builder, submission, polling, results,
    diagnostics) -- none of them open a socket or construct a URL
    themselves.
    """

    def __init__(self, config: ClientConfig) -> None:
        self._config = config
        self._ssl_context = (
            ssl.create_default_context() if config.verify_ssl else ssl._create_unverified_context()
        )

    def get(
        self, path: str, *, query: Optional[dict[str, str]] = None,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> HttpResponse:
        return self.request("GET", path, query=query, extra_headers=extra_headers)

    def post(
        self, path: str, *, json_body: Optional[dict[str, Any]] = None,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> HttpResponse:
        return self.request("POST", path, json_body=json_body, extra_headers=extra_headers)

    def put(
        self, path: str, *, json_body: Optional[dict[str, Any]] = None,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> HttpResponse:
        return self.request("PUT", path, json_body=json_body, extra_headers=extra_headers)

    def delete(
        self, path: str, *, extra_headers: Optional[dict[str, str]] = None,
    ) -> HttpResponse:
        return self.request("DELETE", path, extra_headers=extra_headers)

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[dict[str, str]] = None,
        json_body: Optional[dict[str, Any]] = None,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> HttpResponse:
        """Sends one logical request, retrying transparently on
        connection failure, timeout, or a retryable status code (429,
        503), per §18.3. Any other outcome (success, or a non-retryable
        error status) is returned/raised immediately on the first
        attempt.

        Raises HttpRetriesExhaustedError if every attempt fails to
        connect/complete. Returns the last HttpResponse (even if its
        status is still 429/503) if retries are exhausted but the server
        was at least reachable on the final attempt -- the caller can
        still inspect that response's body and headers.
        """

        url = self._build_url(path, query)
        last_exception: Optional[HttpError] = None
        last_response: Optional[HttpResponse] = None

        for attempt in range(1, self._config.retry.max_attempts + 1):
            try:
                response = self._send_once(method, url, json_body, extra_headers)
            except (HttpTimeoutError, HttpConnectionError) as exc:
                last_exception = exc
                last_response = None
            else:
                last_response = response
                last_exception = None
                if not response.is_retryable_status:
                    return response

            is_final_attempt = attempt == self._config.retry.max_attempts
            if is_final_attempt:
                break

            if last_response is not None:
                delay = _retry_after_seconds(last_response)
                if delay is None:
                    delay = compute_backoff_seconds(attempt, self._config.retry)
            else:
                delay = compute_backoff_seconds(attempt, self._config.retry)
            time.sleep(delay)

        if last_response is not None:
            return last_response
        raise HttpRetriesExhaustedError(
            f"All {self._config.retry.max_attempts} attempt(s) failed for {method} {url}."
        ) from last_exception

    def _build_url(self, path: str, query: Optional[dict[str, str]]) -> str:
        url = f"{self._config.base_url}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        return url

    def _send_once(
        self,
        method: str,
        url: str,
        json_body: Optional[dict[str, Any]],
        extra_headers: Optional[dict[str, str]],
    ) -> HttpResponse:
        headers = build_auth_headers(self._config)
        if extra_headers:
            headers.update(extra_headers)

        data: Optional[bytes] = None
        if json_body is not None:
            data = json_module.dumps(json_body).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(
                req, timeout=self._config.timeout_seconds, context=self._ssl_context
            ) as resp:
                return HttpResponse(
                    status_code=resp.status,
                    headers=dict(resp.headers.items()),
                    body=resp.read(),
                )
        except urllib.error.HTTPError as exc:
            # A completed exchange with a non-2xx status is still a valid
            # HttpResponse, not a transport failure -- urllib raises this
            # as an exception, so it is translated back into a normal
            # response here rather than propagated as an error.
            return HttpResponse(
                status_code=exc.code,
                headers=dict(exc.headers.items()) if exc.headers else {},
                body=exc.read() or b"",
            )
        except socket.timeout as exc:
            raise HttpTimeoutError(f"Request to {url} timed out.") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, socket.timeout):
                raise HttpTimeoutError(f"Request to {url} timed out.") from exc
            raise HttpConnectionError(f"Could not reach {url}: {exc.reason}") from exc
        except ssl.SSLError as exc:
            raise HttpConnectionError(f"TLS error contacting {url}: {exc}") from exc


__all__ = [
    "HttpClient",
    "HttpResponse",
    "HttpError",
    "HttpTimeoutError",
    "HttpConnectionError",
    "HttpRetriesExhaustedError",
    "compute_backoff_seconds",
]
