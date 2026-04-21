# tool_executor.py
# ──────────────────────────────────────────────────────────────────
# Step 4 (core): The programmatic hook that INTERCEPTS all tool calls
# before execution to enforce business rules.
#
# Pattern: Interceptor / Pre-execution Hook
# Reference: Anthropic docs — "Programmatic tool calling" and
#            "The tool-use contract" (tool execution in application layer)
# ──────────────────────────────────────────────────────────────────

import json
import uuid
import random
from config import PAYMENT_ESCALATION_THRESHOLD, REFUND_ESCALATION_THRESHOLD
from error_handler import ERRORS, inject_transient_error_randomly
from escalation import create_escalation_ticket

# ── Simulated Database (in-memory for demo) ────────────────────────
MOCK_ACCOUNTS = {
    "ACC-100001": {"balance": 25000.00, "status": "active", "currency": "USD"},
    "ACC-100002": {"balance": 800.00, "status": "active", "currency": "USD"},
    "ACC-100003": {"balance": 15000.00, "status": "frozen", "currency": "USD"},
    "ACC-FROZEN": {"balance": 5000.00, "status": "frozen", "currency": "USD"},
}

MOCK_TRANSACTIONS = {
    "TXN-20001": {"account_id": "ACC-100001", "amount": 250.00, "refundable": True},
    "TXN-20002": {"account_id": "ACC-100002", "amount": 6000.00, "refundable": True},
    "TXN-99999": {"account_id": "ACC-100001", "amount": 100.00, "refundable": False},
}


# ══════════════════════════════════════════════════════════════════
# PROGRAMMATIC HOOK — The Business Rule Interceptor
# ══════════════════════════════════════════════════════════════════

def business_rule_hook(tool_name: str, tool_input: dict) -> dict | None:
    """
    Pre-execution interceptor for all tool calls.

    This hook runs BEFORE any tool simulator executes.
    If a business rule is violated, it returns an escalation result
    immediately, bypassing the actual tool execution entirely.

    Returns:
        dict: Escalation result (short-circuit) if rule triggered
        None: Pass-through — proceed with normal execution

    Business Rules Enforced:
        1. Payments >= $10,000 → Manager escalation
        2. Refunds >= $5,000  → Supervisor escalation
        3. Fraud-flagged accounts → Security escalation
    """

    # ── Rule 1: High-Value Payment Check ──────────────────────────
    if tool_name == "process_payment":
        amount = tool_input.get("amount", 0)
        account_id = tool_input.get("account_id", "UNKNOWN")

        if amount >= PAYMENT_ESCALATION_THRESHOLD:
            return create_escalation_ticket(
                account_id=account_id,
                tool_name=tool_name,
                tool_input=tool_input,
                rule_triggered="HIGH_VALUE_PAYMENT",
                amount=amount
            )

    # ── Rule 2: High-Value Refund Check ───────────────────────────
    elif tool_name == "process_refund":
        amount = tool_input.get("amount", 0)
        account_id = tool_input.get("account_id", "UNKNOWN")

        if amount >= REFUND_ESCALATION_THRESHOLD:
            return create_escalation_ticket(
                account_id=account_id,
                tool_name=tool_name,
                tool_input=tool_input,
                rule_triggered="HIGH_VALUE_REFUND",
                amount=amount
            )

    # ── No rule triggered → proceed normally ──────────────────────
    return None


# ══════════════════════════════════════════════════════════════════
# TOOL SIMULATORS — Fake implementations for demo
# ══════════════════════════════════════════════════════════════════

def _sim_get_account_balance(inputs: dict) -> dict:
    """Simulate account balance lookup."""
    account_id = inputs.get("account_id", "")

    if account_id not in MOCK_ACCOUNTS:
        return ERRORS["invalid_account"]

    # Inject transient error ~10% of the time
    if inject_transient_error_randomly(0.10):
        return ERRORS["db_timeout"]

    acct = MOCK_ACCOUNTS[account_id]
    return {
        "success": True,
        "account_id": account_id,
        "balance": acct["balance"],
        "account_status": acct["status"],
        "currency": acct["currency"],
        "last_updated": "2026-04-21T13:39:55Z"
    }


def _sim_process_payment(inputs: dict) -> dict:
    """Simulate payment processing (post-hook)."""
    account_id = inputs.get("account_id", "")
    amount = inputs.get("amount", 0)
    payee_id = inputs.get("payee_id", "")
    description = inputs.get("description", "")

    if amount <= 0:
        return ERRORS["negative_amount"]

    if account_id not in MOCK_ACCOUNTS:
        return ERRORS["invalid_account"]

    acct = MOCK_ACCOUNTS[account_id]

    if acct["status"] == "frozen":
        return ERRORS["account_frozen"]

    if acct["balance"] < amount:
        return ERRORS["insufficient_funds"]

    # Simulate transient failure
    if inject_transient_error_randomly(0.15):
        return ERRORS["service_unavailable"]

    # Execute payment
    MOCK_ACCOUNTS[account_id]["balance"] -= amount
    txn_id = f"TXN-{uuid.uuid4().hex[:5].upper()}"

    return {
        "success": True,
        "transaction_id": txn_id,
        "status": "success",
        "amount_debited": amount,
        "payee_id": payee_id,
        "description": description,
        "new_balance": MOCK_ACCOUNTS[account_id]["balance"]
    }


def _sim_process_refund(inputs: dict) -> dict:
    """Simulate refund processing (post-hook)."""
    account_id = inputs.get("account_id", "")
    amount = inputs.get("amount", 0)
    orig_txn_id = inputs.get("original_transaction_id", "")
    reason = inputs.get("reason", "")

    if amount <= 0:
        return ERRORS["negative_amount"]

    if account_id not in MOCK_ACCOUNTS:
        return ERRORS["invalid_account"]

    if orig_txn_id not in MOCK_TRANSACTIONS:
        return ERRORS["transaction_not_found"]

    txn = MOCK_TRANSACTIONS[orig_txn_id]
    if txn["account_id"] != account_id:
        return ERRORS["invalid_account"]

    # Simulate transient failure
    if inject_transient_error_randomly(0.10):
        return ERRORS["db_timeout"]

    # Execute refund
    MOCK_ACCOUNTS[account_id]["balance"] += amount
    refund_id = f"REF-{uuid.uuid4().hex[:5].upper()}"

    return {
        "success": True,
        "refund_id": refund_id,
        "status": "success",
        "amount_credited": amount,
        "original_transaction_id": orig_txn_id,
        "reason": reason,
        "new_balance": MOCK_ACCOUNTS[account_id]["balance"]
    }


def _sim_escalate_to_human_agent(inputs: dict) -> dict:
    """Simulate human agent escalation ticket creation."""
    ticket_id = f"HUM-{uuid.uuid4().hex[:6].upper()}"
    return {
        "success": True,
        "ticket_id": ticket_id,
        "status": "created",
        "assigned_team": "Customer Success Team",
        "estimated_wait_minutes": 20,
        "message": (
            f"Escalation ticket {ticket_id} created successfully. "
            f"A human agent will review your case shortly."
        )
    }


# ── Tool Dispatcher ────────────────────────────────────────────────
TOOL_SIMULATORS = {
    "get_account_balance": _sim_get_account_balance,
    "process_payment": _sim_process_payment,
    "process_refund": _sim_process_refund,
    "escalate_to_human_agent": _sim_escalate_to_human_agent,
}


# ══════════════════════════════════════════════════════════════════
# MAIN EXECUTOR — Hook + Dispatch + Error Handling
# ══════════════════════════════════════════════════════════════════

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """
    Primary entry point for all tool executions.

    Flow:
        1. Run business_rule_hook (pre-execution interceptor)
        2. If hook fires → return escalation result
        3. Else dispatch to tool simulator
        4. Return JSON-serialised result for Claude

    The result is always a JSON string (tool_result content).
    """
    print(f"\n[TOOL EXECUTOR] ⚙️  Executing: {tool_name}")
    print(f"  Inputs: {json.dumps(tool_input, indent=2)}")

    # ── Step 1: Pre-execution business rule hook ───────────────────
    hook_result = business_rule_hook(tool_name, tool_input)
    if hook_result is not None:
        print(f"  [HOOK] 🚨 INTERCEPTED — escalation triggered")
        return json.dumps(hook_result)

    # ── Step 2: Dispatch to tool simulator ────────────────────────
    simulator = TOOL_SIMULATORS.get(tool_name)
    if not simulator:
        return json.dumps({
            "success": False,
            "errorCategory": "validation",
            "errorCode": "UNKNOWN_TOOL",
            "isRetryable": False,
            "message": f"Unknown tool: {tool_name}"
        })

    result = simulator(tool_input)
    print(f"  Result: {json.dumps(result, indent=2)}")
    return json.dumps(result)