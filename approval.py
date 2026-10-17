"""Problem 6 — Design-level defense: a separate human-approval boundary.

In DEFENDED mode, the vendor-analysis agent (the model that reads an
untrusted document and produces a VendorRecommendation) is never given the
`send_email` / `approve_payment` tools at all — see agent.py's
`_build_agent(defense="on")`. There is therefore no code path by which text
inside a vendor document can cause those tools to be invoked directly; the
model that reads untrusted content literally has no handle to them.

IMPORTANT ARCHITECTURAL BOUNDARY (Problem 6 Priority 3, functional approval
mechanism): this module's mechanisms are NOT wired into `agent.py`'s
`--defense off` (undefended) tool registration, and never will be, by
deliberate constraint — Problem 5 and Problem 7's historical results were
generated against the undefended agent's original, unmodified tool-calling
behavior, and must remain exactly reproducible. `agent.py`, `tools.py`, and
both prompt files are untouched by this module. `--defense off` registers
`tools.send_email`/`tools.approve_payment` directly, exactly as it always
has; this module's approval boundary does **not** gate that path and does
**not** protect it. See `output/harness.md` for what this mechanism does and
does not protect.

Two mechanisms live here:

1. `request_action()` (original, Problem 6) — a simple demonstration that a
   boolean-gated call site is possible. Kept for historical continuity with
   earlier audits that reference it; superseded in rigor by (2) below.
2. `TrustedApprovalStore` (Problem 6 Priority 3) — a genuine, testable,
   capability-token-based mechanism. A token is issued ONLY by
   `TrustedApprovalStore.issue()`, which must be called from
   `trusted_operator.review_and_execute()` — the one trusted, human-operated
   entry point in this project (see trusted_operator.py) — and ONLY after an
   explicit, real operator decision. The token: is bound to the exact tool
   name AND a hash of the exact arguments (changing either invalidates it);
   expires after a fixed TTL; can be consumed exactly once; and is never
   passed into any LLM's context or derivable from document content, so no
   model and no vendor document can ever produce, guess, or reuse one. This
   is NEVER exposed as an agent tool (nothing in `agent.py` calls `issue()`),
   per the explicit instruction not to expose approval issuance as an agent
   tool.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Any

import tools

DEFAULT_TOKEN_TTL_SECONDS = 300  # 5 minutes


class ApprovalRequiredError(PermissionError):
    """Raised when a sensitive action is requested without human approval."""


def request_action(tool_name: str, arguments: dict[str, Any], *, human_approved: bool = False) -> str:
    """ORIGINAL (Problem 6) demonstration boundary. Kept unchanged for
    historical continuity with earlier audits that reference it by name.

    Raises ApprovalRequiredError unless `human_approved=True` is passed
    explicitly by a caller. Superseded in rigor by TrustedApprovalStore below
    (this boolean, unlike a capability token, has no binding to specific
    arguments, no expiry, and no one-time-use guarantee).
    """
    if tool_name not in ("send_email", "approve_payment"):
        raise ValueError(f"Unknown sensitive action: {tool_name}")
    if not human_approved:
        raise ApprovalRequiredError(
            f"Action '{tool_name}' requires explicit human_approved=True; "
            "no vendor-document content can set this flag."
        )
    if tool_name == "send_email":
        return tools.send_email(**arguments)
    return tools.approve_payment(**arguments)


@dataclass
class _IssuedToken:
    tool_name: str
    args_hash: str
    issued_at: float
    expires_at: float
    consumed: bool = False


class TrustedApprovalStore:
    """In-process, trusted-code-only capability-token store.

    `issue()` is the ONLY way a token comes into existence, and it must only
    ever be called from a genuinely human-operated path (see
    `trusted_operator.review_and_execute()`). Nothing about a token is ever
    derived from, or exposed to, document content or model output: the
    caller of `issue()` supplies the tool name and arguments directly, in
    trusted Python code, not from any LLM response.

    `verify_and_consume()` is the ONLY way a token is ever checked, and does
    so by construction: it denies by default for every failure mode (no
    token, unknown token, already-consumed token, expired token, wrong tool,
    or mismatched arguments), and consumes the token (one-time use) on the
    single success path.
    """

    def __init__(self, ttl_seconds: float = DEFAULT_TOKEN_TTL_SECONDS) -> None:
        self._tokens: dict[str, _IssuedToken] = {}
        self._ttl_seconds = ttl_seconds

    @staticmethod
    def _hash_arguments(arguments: dict[str, Any]) -> str:
        canonical = json.dumps(arguments, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def issue(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Issues a new, single-use capability token for exactly this
        (tool_name, arguments) pair. MUST only be called after a real,
        explicit human approval decision -- this function itself does not
        ask for one; the caller (trusted_operator.py) is responsible for
        obtaining it from an actual human before calling this.
        """
        token = secrets.token_urlsafe(32)
        now = time.monotonic()
        self._tokens[token] = _IssuedToken(
            tool_name=tool_name,
            args_hash=self._hash_arguments(arguments),
            issued_at=now,
            expires_at=now + self._ttl_seconds,
        )
        return token

    def verify_and_consume(self, tool_name: str, arguments: dict[str, Any], token: str | None) -> tuple[bool, str]:
        """Returns (approved, reason). Denies by default for every failure
        mode; the only way to get `approved=True` is a valid, matching,
        unexpired, unconsumed token for the exact (tool_name, arguments).
        """
        if not token:
            return False, "no token provided"
        record = self._tokens.get(token)
        if record is None:
            return False, "unknown/invalid token"
        if record.consumed:
            return False, "token already consumed"
        if time.monotonic() > record.expires_at:
            return False, "token expired"
        if record.tool_name != tool_name:
            return False, "token issued for a different tool"
        if record.args_hash != self._hash_arguments(arguments):
            return False, "token issued for different arguments"
        record.consumed = True
        return True, "approved"
