"""Problem 6 Priority 3 — the ONE trusted, human-operated entry point for a
sensitive action to ever be approved and (simulated-)executed.

This module is NOT an agent tool, is never imported by agent.py, and is
never reachable from any model tool call. It exists to demonstrate, and to
let tests exercise, exactly how a real human operator's decision would flow
into `approval.TrustedApprovalStore`.

In a real deployment, `operator_approves` would come from an actual human
action -- a CLI y/n prompt a person types an answer into, a button a person
clicks in a review UI, a signed approval from an identity-verified reviewer,
etc. It is a plain function parameter here ONLY so this exact decision point
is directly, deterministically testable without needing a live human in a
test run. Nothing upstream of this parameter is ever document content or
model output: this function is called by a human operator's own tooling,
with arguments THEY choose to propose for review, not arguments extracted
automatically from a vendor document or produced by the vendor desk agent
without a human transcribing/confirming them first.

Still simulated end to end: even an "approved" action here only ever reaches
tools.py's logging-only trap implementations, which never send a real email
or approve a real payment, in this homework, by design.
"""

from __future__ import annotations

from typing import Any

import tools
from approval import TrustedApprovalStore


def review_and_execute(
    store: TrustedApprovalStore,
    tool_name: str,
    arguments: dict[str, Any],
    *,
    operator_approves: bool,
) -> dict[str, Any]:
    """The trusted human-operator workflow, in one function:

    1. A proposed sensitive action (tool_name, arguments) is presented for
       human review (outside this function, e.g. printed to an operator's
       screen in a real deployment).
    2. The human operator makes an explicit decision: `operator_approves`.
       This function does not and cannot infer that decision from anything
       else -- it is the one place a real human's yes/no must be supplied.
    3. If approved, a single-use token is issued and immediately consumed to
       execute the (simulated, logging-only) action. If not approved, no
       token is ever issued, and the action is denied.

    Returns a result dict with 'status' ('executed' or 'denied'), 'reason',
    and, if executed, 'tool_result' (tools.py's own string response).
    """
    if tool_name not in ("send_email", "approve_payment"):
        return {"status": "denied", "reason": f"unknown tool: {tool_name}", "tool_result": None}

    if not operator_approves:
        return {
            "status": "denied",
            "reason": "operator explicitly did not approve this action",
            "tool_result": None,
        }

    token = store.issue(tool_name, arguments)
    approved, reason = store.verify_and_consume(tool_name, arguments, token)
    if not approved:
        # Should not happen on the path we just issued for, but never
        # silently proceed if it does.
        return {"status": "denied", "reason": f"verification failed: {reason}", "tool_result": None}

    if tool_name == "send_email":
        result = tools.send_email(**arguments)
    else:
        result = tools.approve_payment(**arguments)

    return {"status": "executed", "reason": "operator approved; token verified", "tool_result": result}
