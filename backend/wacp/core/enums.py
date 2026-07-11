"""wacp.core.enums

Protocol-level enumerations: `Priority` and `JobStatus`, plus the job
lifecycle transition table from 10_WACP_PROTOCOL.md §12.

The transition table is defined here, as data, rather than as behavior
scattered across client and server code. Both wacp.client (interpreting a
response) and wacp.server (enforcing a transition before it happens) import
this same table, so a lifecycle rule exists in exactly one place
(20_WACP_SDK_ARCHITECTURE.md §4.2).

This module has no dependency on any other wacp module. No dependency on
wacp.client or wacp.server.
"""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet


class Priority(str, Enum):
    """10_WACP_PROTOCOL.md §7.2 — envelope `priority` field.

    Inherits from `str` so instances serialize as their plain string value
    (e.g. `Priority.NORMAL == "NORMAL"`), matching the wire format exactly
    without a custom serializer.
    """

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class JobStatus(str, Enum):
    """10_WACP_PROTOCOL.md §12.1/§12.2 — job lifecycle states."""

    RECEIVED = "RECEIVED"
    VALIDATING = "VALIDATING"
    REJECTED = "REJECTED"
    ACCEPTED = "ACCEPTED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


#: Terminal states per §12.2. A job in one of these states never
#: transitions again; the only route back into execution is a new job via
#: POST /jobs/{job_id}/retry (§13.2), not a mutation of this one.
TERMINAL_JOB_STATUSES: FrozenSet[JobStatus] = frozenset(
    {
        JobStatus.REJECTED,
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
    }
)

#: The valid state transition table from §12.3, transcribed exactly.
#: Keys are the "from" state; values are the set of "to" states legal from
#: that state. No entry means the state is terminal (no outgoing
#: transitions) or, in the case of a status not present as a key at all,
#: that it cannot be a starting point for any further transition.
VALID_TRANSITIONS: dict[JobStatus, FrozenSet[JobStatus]] = {
    JobStatus.RECEIVED: frozenset({JobStatus.VALIDATING}),
    JobStatus.VALIDATING: frozenset({JobStatus.REJECTED, JobStatus.ACCEPTED}),
    JobStatus.ACCEPTED: frozenset({JobStatus.QUEUED}),
    JobStatus.QUEUED: frozenset({JobStatus.RUNNING, JobStatus.CANCELLED}),
    JobStatus.RUNNING: frozenset(
        {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}
    ),
}


def is_terminal(status: JobStatus) -> bool:
    """Returns True if `status` is a terminal state (§12.2)."""

    return status in TERMINAL_JOB_STATUSES


def is_valid_transition(from_status: JobStatus, to_status: JobStatus) -> bool:
    """Returns True if moving from `from_status` to `to_status` is a legal
    transition per the table in §12.3. Terminal states return False for
    every `to_status`, including attempts to "transition" to the same
    state, since a terminal state has no outgoing transitions at all.
    """

    allowed = VALID_TRANSITIONS.get(from_status)
    if allowed is None:
        return False
    return to_status in allowed


__all__ = [
    "Priority",
    "JobStatus",
    "TERMINAL_JOB_STATUSES",
    "VALID_TRANSITIONS",
    "is_terminal",
    "is_valid_transition",
]
