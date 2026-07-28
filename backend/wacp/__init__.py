"""wacp

WIMLOGIC Application Communication Protocol — Reference SDK.

This package implements 10_WACP_PROTOCOL.md, now at v1.1 (additive,
backward-compatible over the LOCKED v1.0 baseline) per
20_WACP_SDK_ARCHITECTURE.md. SDK 0.3.0 implements WACP protocols 1.0 and
1.1: new envelopes built by this SDK default to 1.1 (ordered multi-Business-
Intent submission via `additional_business_intents`), while parsing and
serializing 1.0 envelopes exactly as SDK 0.2.0 did, unchanged.

This release contains wacp.core and wacp.client. wacp.server and
wacp.compliance are generated in subsequent phases per the locked
implementation order.
"""

from __future__ import annotations

__version__ = "0.3.0"
