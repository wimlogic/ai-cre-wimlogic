"""
app/api/wacp_debug.py

TEMPORARY DEBUGGING FEATURE. See app/services/wacp_debug_intercept.py for
the full removal instructions - delete this file too when the routing
issue is resolved. Every endpoint here 404s when
settings.WACP_DEBUG_INTERCEPT is False, so simply leaving the flag off
(the default) makes this entire router inert without needing to remove
the route registration itself.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.services import wacp_debug_intercept

router = APIRouter()


def _require_debug_enabled() -> None:
    if not settings.WACP_DEBUG_INTERCEPT:
        raise HTTPException(status_code=404, detail="WACP debug intercept is not enabled.")


@router.get("/pending")
def list_pending_wacp_requests() -> Dict[str, List[Dict[str, Any]]]:
    """Every currently-blocked outbound job submission, awaiting a
    Continue Sending confirmation. The frontend polls this to detect a
    paused request and render the debug modal."""
    _require_debug_enabled()
    items = [
        {"request_id": request_id, "path": data["path"], "pretty": data["pretty"]}
        for request_id, data in wacp_debug_intercept.list_pending().items()
    ]
    return {"items": items}


@router.post("/pending/{request_id}/continue")
def continue_wacp_request(request_id: str) -> Dict[str, Any]:
    """Releases the block on the given request_id, letting AIHOME's
    already-built, unmodified request proceed to DEV-TOOLS exactly as
    captured."""
    _require_debug_enabled()
    released = wacp_debug_intercept.release(request_id)
    if not released:
        raise HTTPException(
            status_code=404,
            detail=f"No pending request with id {request_id!r} (already sent, timed out, or never existed).",
        )
    return {"released": True, "request_id": request_id}
