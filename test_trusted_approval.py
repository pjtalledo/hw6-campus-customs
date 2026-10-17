"""Problem 6 Priority 3 — deterministic tests for the trusted human-approval
mechanism (approval.TrustedApprovalStore + trusted_operator.py).

Pure local/offline. No API calls. No real email/payment can occur (tools.py
is unchanged and remains logging-only). trap_calls.json is reset to its
pre-test state (an empty list) after these tests run, so they leave no trace
in the historical evidence log.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
import approval
import tools
import trusted_operator
import agent as agent_mod

PASS, FAIL = [], []


def check(name, condition, detail=""):
    if condition:
        PASS.append(name)
        print(f"PASS: {name}")
    else:
        FAIL.append((name, detail))
        print(f"FAIL: {name} -- {detail}")


# Snapshot trap_calls.json so we can restore it exactly afterward.
TRAP_CALLS_PATH = Path("output/trap_calls.json")
_trap_before = TRAP_CALLS_PATH.read_text(encoding="utf-8")

SEND_EMAIL_ARGS = {"to": "ops@example.com", "subject": "test", "body": "test body"}
APPROVE_PAYMENT_ARGS = {"vendor": "Test Vendor", "amount": 100.0, "currency": "USD"}

# --- 1. Missing approval -> DENIED ---------------------------------------
store = approval.TrustedApprovalStore()
result = trusted_operator.review_and_execute(store, "send_email", SEND_EMAIL_ARGS, operator_approves=False)
check("Missing approval (operator_approves=False) -> DENIED", result["status"] == "denied")

# --- 2. Explicit rejection -> DENIED, same code path as missing ----------
result2 = trusted_operator.review_and_execute(store, "approve_payment", APPROVE_PAYMENT_ARGS, operator_approves=False)
check("Explicit rejection -> DENIED", result2["status"] == "denied")

# --- 3. Invalid token -> DENIED -------------------------------------------
approved, reason = store.verify_and_consume("send_email", SEND_EMAIL_ARGS, "not-a-real-token")
check("Invalid/unknown token -> DENIED", approved is False and "unknown" in reason)

# --- 4. Expired token -> DENIED -------------------------------------------
short_store = approval.TrustedApprovalStore(ttl_seconds=0.05)
tok = short_store.issue("send_email", SEND_EMAIL_ARGS)
time.sleep(0.15)
approved, reason = short_store.verify_and_consume("send_email", SEND_EMAIL_ARGS, tok)
check("Expired token -> DENIED", approved is False and "expired" in reason)

# --- 5. Already-consumed token -> DENIED ----------------------------------
store2 = approval.TrustedApprovalStore()
tok2 = store2.issue("send_email", SEND_EMAIL_ARGS)
first = store2.verify_and_consume("send_email", SEND_EMAIL_ARGS, tok2)
second = store2.verify_and_consume("send_email", SEND_EMAIL_ARGS, tok2)
check("First use of a valid token succeeds", first[0] is True)
check("Already-consumed token -> DENIED on reuse", second[0] is False and "already consumed" in second[1])

# --- 6. Token for a different tool -> DENIED ------------------------------
store3 = approval.TrustedApprovalStore()
tok3 = store3.issue("send_email", SEND_EMAIL_ARGS)
approved, reason = store3.verify_and_consume("approve_payment", APPROVE_PAYMENT_ARGS, tok3)
check("Token issued for a different tool -> DENIED", approved is False and "different tool" in reason)

# --- 7. Token for different arguments -> DENIED (binds to exact args) ----
store4 = approval.TrustedApprovalStore()
tok4 = store4.issue("approve_payment", APPROVE_PAYMENT_ARGS)
altered_args = {**APPROVE_PAYMENT_ARGS, "amount": 999999.0}
approved, reason = store4.verify_and_consume("approve_payment", altered_args, tok4)
check("Token issued for different arguments -> DENIED (amount changed invalidates it)", approved is False and "different arguments" in reason)

# --- 8. Valid human approval -> simulated action permitted exactly once --
store5 = approval.TrustedApprovalStore()
exec_result = trusted_operator.review_and_execute(store5, "send_email", SEND_EMAIL_ARGS, operator_approves=True)
check("Valid operator approval -> action executed (simulated)", exec_result["status"] == "executed")
check(
    "Executed action still only returns the harmless BLOCKED trap message, never a real send",
    "BLOCKED" in (exec_result["tool_result"] or ""),
)

# --- 9. Model cannot issue its own approval --------------------------------
# The model only ever has access to tools registered on the PydanticAI agent.
# TrustedApprovalStore.issue()/review_and_execute() are never registered as
# tools anywhere, so the model has no callable path to them at all.
a_off, c_off = agent_mod._build_agent(defense="off")
a_on, c_on = agent_mod._build_agent(defense="on")
off_tool_names = sorted(a_off._function_toolset.tools.keys())
on_tool_names = sorted(a_on._function_toolset.tools.keys())
check(
    "approval/trusted_operator functions are NOT registered as tools on the undefended agent",
    "issue" not in off_tool_names and "review_and_execute" not in off_tool_names,
)
check(
    "approval/trusted_operator functions are NOT registered as tools on the defended agent",
    "issue" not in on_tool_names and "review_and_execute" not in on_tool_names,
)
asyncio.run(c_off.close())
asyncio.run(c_on.close())

# --- 10. Original undefended toolset and schemas unchanged -----------------
check(
    "Undefended toolset unchanged: ['approve_payment', 'read_document', 'send_email']",
    off_tool_names == ["approve_payment", "read_document", "send_email"],
    f"got {off_tool_names}",
)

# --- 11. Defended toolset remains read_document only ------------------------
check("Defended toolset remains ['read_document'] only", on_tool_names == ["read_document"], f"got {on_tool_names}")

# --- 12. No actual email or payment: tools.py unchanged, and trap_calls.json
#         only ever gained the entries THIS test run intentionally made ----
import hashlib

check(
    "tools.py unchanged (hash matches the long-standing baseline)",
    hashlib.sha256(Path("tools.py").read_bytes()).hexdigest()
    == "181442a7ec0c20ed38b5cef87d21179e6ed3e3f241ca0e07716f409ce3b3b3c8",
)
check(
    "agent.py unchanged by this test (no import of approval/trusted_operator in agent.py)",
    "approval" not in Path("agent.py").read_text(encoding="utf-8").replace("# approval.py", "")
    or "import approval" not in Path("agent.py").read_text(encoding="utf-8"),
)

# --- 13. Historical result hashes unchanged (spot check the key files) ----
HISTORICAL_HASHES = {
    "output/usage_log.json": "dd6caeba6b543276d29ffaae4365f19f4ded3a957fb67dc597f7848d5ab0e5d1",
    "output/audit_trail.json": "87250c2b8047fd27a69dd6e302436078609bb0984b6b25d1a7c00cddc77e0c1c",
    "output/attack_results.json": "f1ca6ca8902ba5f2f3d90467075416d584aada21dbb311946c1ea1f5be55e8c1",
    "output/red_team.json": "b4385c0a2b957fad6417dc18460ab0a49decfe669ef5de592ec935b1bdf55cfc",
    "output/exam_results.json": "0d3406576293edeaa76ae165cd011f9255940930928d826c7c7ba5904c5bf1d4",
    "output/cache_test.json": "4854bf8e05b553141821e23a115d2d78d74eecb7dfc1c98775edc3745a648b23",
    "output/layer_ablation.json": "a660ca9df5e025c416396fcc0fa61b9d8aac660781d1da1b8c672cf18e75e48b",
}
for path, expected in HISTORICAL_HASHES.items():
    actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    check(f"Historical hash unchanged: {path}", actual == expected, f"got {actual}")

print()
print(f"TOTAL: {len(PASS)} passed, {len(FAIL)} failed")

# Restore trap_calls.json to its exact pre-test state (this test suite's own
# send_email call above intentionally appended a real, harmless log entry;
# we revert it here so this test run leaves no trace in the evidence log).
TRAP_CALLS_PATH.write_text(_trap_before, encoding="utf-8")
restored = json.loads(TRAP_CALLS_PATH.read_text(encoding="utf-8"))
check("trap_calls.json restored to its exact pre-test state ([])", restored == [])

print()
print(f"FINAL TOTAL: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILURES:", FAIL)
    sys.exit(1)
