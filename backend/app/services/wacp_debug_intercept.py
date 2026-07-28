"""
app/services/wacp_debug_intercept.py

TEMPORARY DEBUGGING FEATURE - routing verification.

Pauses the outbound POST to /wacp/v1/jobs immediately before transmission
so the EXACT request body can be inspected in a browser modal before an
operator chooses to send it. Built entirely as an AIHOME-owned monkeypatch
around wacp.client.http.HttpClient.post - it does not edit a single line
inside the vendored wacp/ package, per the platform boundary (WACP/SDK are
published platform artifacts AIHOME must not modify).

Gated behind settings.WACP_DEBUG_INTERCEPT (default False). To remove this
feature entirely once the routing issue it exists to diagnose is
resolved: delete this file, app/api/wacp_debug.py, the
WACP_DEBUG_INTERCEPT setting in app/core/config.py, the one conditional
call in app/main.py, and the frontend WacpDebugModal component + its one
mount point. Nothing else in the codebase depends on any of it - normal
job submission behaves identically whether this feature exists or not,
since with the flag off, install() is never called and
HttpClient.post is never touched.

This module NEVER reconstructs, rebuilds, or re-derives the request body.
It captures the literal `json_body` argument already built by the SDK's
own PayloadBuilder + envelope_to_dict, at the one point it is about to be
handed to the HTTP client, and passes that SAME object through unchanged
once released.
"""

import json
import logging
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_pending: Dict[str, Dict[str, Any]] = {}
_release_events: Dict[str, threading.Event] = {}
_installed = False
_original_post = None

#: Never hangs a real request thread indefinitely if no operator responds -
#: this is a debugging aid, not a permanent human-in-the-loop gate.
DEBUG_RELEASE_TIMEOUT_SECONDS = 300


def install() -> None:
    """
    Monkeypatches wacp.client.http.HttpClient.post so that any POST to a
    path ending in "/jobs" (the job-submission endpoint,
    10_WACP_PROTOCOL.md §13.1) is intercepted: the exact `json_body`
    argument is captured and logged (pretty-printed, 2-space indent),
    then the calling thread blocks until release(request_id) is called
    (via POST /api/v1/wacp-debug/pending/{request_id}/continue) or the
    timeout elapses. Every other HTTP call (status polling, results
    retrieval, PUT/DELETE) passes through completely untouched - this
    only ever intercepts new job submissions.

    Idempotent - calling this more than once (e.g. module reimport
    during tests) has no additional effect after the first call.
    """
    global _installed, _original_post
    if _installed:
        return

    import wacp.client.http as http_module
    _original_post = http_module.HttpClient.post

    def _debug_post(self, path, *, json_body=None, extra_headers=None):
        if json_body is None or not path.rstrip("/").endswith("jobs"):
            return _original_post(self, path, json_body=json_body, extra_headers=extra_headers)

        request_id: Optional[str] = None
        wacp_block = json_body.get("wacp")
        if isinstance(wacp_block, dict):
            request_id = wacp_block.get("request_id")
        if not request_id:
            request_id = f"unkeyed-{time.time_ns()}"

        pretty = json.dumps(json_body, indent=2)
        logger.info(
            "WACP_DEBUG_INTERCEPT - exact outbound request body for request_id=%s "
            "(path=%s), paused pending manual confirmation:\n%s",
            request_id, path, pretty,
        )

        event = threading.Event()
        with _lock:
            _pending[request_id] = {"path": path, "json_body": json_body, "pretty": pretty}
            _release_events[request_id] = event

        released = event.wait(timeout=DEBUG_RELEASE_TIMEOUT_SECONDS)
        if not released:
            logger.warning(
                "WACP_DEBUG_INTERCEPT - request_id=%s received no Continue Sending "
                "confirmation within %ss; sending anyway rather than hanging indefinitely.",
                request_id, DEBUG_RELEASE_TIMEOUT_SECONDS,
            )

        with _lock:
            _pending.pop(request_id, None)
            _release_events.pop(request_id, None)

        # The SAME json_body object captured above - never rebuilt,
        # never re-serialized, never mutated in between - is what
        # actually gets transmitted.
        return _original_post(self, path, json_body=json_body, extra_headers=extra_headers)

    http_module.HttpClient.post = _debug_post
    _installed = True
    logger.warning(
        "WACP_DEBUG_INTERCEPT is ENABLED - every job submission will pause until "
        "manually confirmed. This is a temporary debugging feature; set "
        "WACP_DEBUG_INTERCEPT=false before deploying to production."
    )


def list_pending() -> Dict[str, Dict[str, Any]]:
    """Returns {request_id: {"path": ..., "pretty": ...}} for every
    currently-blocked submission. `pretty` is the exact captured JSON,
    already 2-space-indented - the frontend renders this string
    verbatim, never re-serializing it."""
    with _lock:
        return {rid: {"path": v["path"], "pretty": v["pretty"]} for rid, v in _pending.items()}


def release(request_id: str) -> bool:
    """Unblocks the submission waiting on `request_id`. Returns False if
    no such pending request exists (already sent, timed out, or a typo)."""
    with _lock:
        event = _release_events.get(request_id)
    if event is None:
        return False
    event.set()
    return True
