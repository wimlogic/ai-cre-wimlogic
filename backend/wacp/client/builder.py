"""wacp.client.builder

The Payload Builder: assembles a complete, protocol-correct WacpEnvelope
from a Business Application's inputs, per 10_WACP_PROTOCOL.md §7. This is
the module that makes "a Business Application never manually constructs a
WACP envelope" (20_WACP_SDK_ARCHITECTURE.md §1.4) actually true in code --
a caller never sets `request_id` or `timestamp` themselves, and there is
no field for `schema_id`/`schema_version` to set at all (§10.1).

This module builds and validates envelope *shape* (via
wacp.core.validation), and additionally validates that `data` is
JSON-serializable up front -- a cheap, useful check that saves a round
trip to DEV-TOOLS for something that would fail immediately anyway. It
does not, and cannot, validate `data` against a workflow schema; that
remains DEV-TOOLS's Schema Registry responsibility, entirely outside SDK
scope (§10).

Depends on wacp.core (dto, enums, utils, validation) and wacp.client.config
(for application_id/company_id defaults sourced from the client's own
configuration, where convenient). No dependency on wacp.client.http,
wacp.server, or any Business Application package.
"""

from __future__ import annotations

import json as json_module
from typing import Any, Optional

from wacp.client.config import ClientConfig
from wacp.core.dto import WacpEnvelope
from wacp.core.enums import Priority
from wacp.core.errors import WACP_101, WacpEnvelopeError
from wacp.core.utils import current_timestamp, generate_request_id
from wacp.core.validation import validate_envelope


class PayloadBuilder:
    """Builds WacpEnvelope instances for one Business Application.

    Bound to a `ClientConfig` so `application_id` (and, optionally, a
    default `company_id`/`project_code` a caller commonly repeats) never
    needs to be retyped on every call. New callers route with
    `business_intent`; `workflow_code` remains available for compatibility.
    """

    def __init__(
        self,
        config: ClientConfig,
        *,
        default_company_id: Optional[str] = None,
        default_project_code: Optional[str] = None,
    ) -> None:
        self._config = config
        self._default_company_id = default_company_id
        self._default_project_code = default_project_code

    def build(
        self,
        *,
        data: dict[str, Any],
        business_intent: Optional[str] = None,
        workflow_code: Optional[str] = None,
        company_id: Optional[str] = None,
        project_code: Optional[str] = None,
        workflow_version: Optional[str] = None,
        priority: Priority = Priority.NORMAL,
        correlation_id: Optional[str] = None,
        callback_url: Optional[str] = None,
        extensions: Optional[dict[str, Any]] = None,
    ) -> WacpEnvelope:
        """Builds and validates a WacpEnvelope. `request_id` and
        `timestamp` are always generated here, never accepted as
        parameters -- a caller cannot construct a colliding or
        non-time-ordered request_id through this API (§18.1).

        `company_id`/`project_code` fall back to the builder's configured
        defaults when omitted; at least one source (call-site argument or
        configured default) must resolve to a non-empty value, or
        WacpEnvelopeError (WACP-101) is raised.

        Raises WacpEnvelopeError (WACP-101) if `data` is not
        JSON-serializable, or if the assembled envelope fails shape
        validation (wacp.core.validation.validate_envelope).
        """

        resolved_company_id = company_id or self._default_company_id
        resolved_project_code = project_code or self._default_project_code

        if not resolved_company_id:
            raise WacpEnvelopeError(
                WACP_101, "company_id must be provided (no call-site value or configured default)."
            )
        if not resolved_project_code:
            raise WacpEnvelopeError(
                WACP_101, "project_code must be provided (no call-site value or configured default)."
            )

        self._assert_json_serializable(data)

        envelope = WacpEnvelope(
            version=self._config.protocol_version,
            request_id=generate_request_id(),
            timestamp=current_timestamp(),
            application_id=self._config.application_id,
            company_id=resolved_company_id,
            project_code=resolved_project_code,
            data=data,
            business_intent=business_intent,
            workflow_code=workflow_code,
            workflow_version=workflow_version,
            priority=priority,
            correlation_id=correlation_id,
            callback_url=callback_url,
            extensions=extensions or {},
        )

        validate_envelope(envelope)
        return envelope

    @staticmethod
    def _assert_json_serializable(data: dict[str, Any]) -> None:
        try:
            json_module.dumps(data)
        except (TypeError, ValueError) as exc:
            raise WacpEnvelopeError(
                WACP_101, f"data is not JSON-serializable: {exc}"
            ) from exc


__all__ = ["PayloadBuilder"]
