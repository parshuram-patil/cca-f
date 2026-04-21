# escalation.py
# ──────────────────────────────────────────────────────────────────
# Step 4: Escalation workflow triggered by programmatic hook.
# When business rules are violated (e.g., amount >= threshold),
# this module intercepts the call and redirects it.
# ──────────────────────────────────────────────────────────────────

import uuid
from datetime import datetime


def create_escalation_ticket(
        account_id: str,
        tool_name: str,
        tool_input: dict,
        rule_triggered: str,
        amount: float | None = None
) -> dict:
    """
    Creates a human-escalation ticket for high-value or flagged operations.

    This is called by the programmatic hook BEFORE the tool executes,
    short-circuiting the normal flow and redirecting to human review.

    Returns a structured result that Claude can use to inform the user.
    """
    ticket_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"

    escalation_details = {
        "success": False,  # Did NOT complete automatically
        "escalated": True,
        "ticket_id": ticket_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "account_id": account_id,
        "tool_attempted": tool_name,
        "rule_triggered": rule_triggered,
        "amount_flagged": amount,
        "assigned_team": _assign_team(tool_name, amount),
        "estimated_wait_minutes": _estimate_wait(rule_triggered),
        "message": (
            f"Your request has been escalated for human review. "
            f"Ticket ID: {ticket_id}. "
            f"Reason: {rule_triggered}. "
            f"A specialist will contact you within "
            f"{_estimate_wait(rule_triggered)} minutes."
        ),
        "next_steps": [
            f"Reference ticket ID {ticket_id} in future communications.",
            "A specialist will review and contact you shortly.",
            "You can also call our priority line quoting your ticket ID."
        ]
    }

    # Audit log (in production this would go to a logging service)
    print(f"\n[ESCALATION HOOK] 🚨 Intercepted: {tool_name}")
    print(f"  Account  : {account_id}")
    print(f"  Amount   : ${amount:,.2f}" if amount else "  Amount  : N/A")
    print(f"  Rule     : {rule_triggered}")
    print(f"  Ticket   : {ticket_id}")

    return escalation_details


def _assign_team(tool_name: str, amount: float | None) -> str:
    """Route to appropriate human team based on tool and amount."""
    if tool_name == "process_payment":
        return "Payments & Treasury Team" if amount and amount >= 50_000 else "Payments Team"
    elif tool_name == "process_refund":
        return "Refunds & Disputes Team"
    return "General Operations Team"


def _estimate_wait(rule_triggered: str) -> int:
    """Estimate wait time in minutes based on escalation type."""
    wait_map = {
        "HIGH_VALUE_PAYMENT": 15,
        "HIGH_VALUE_REFUND": 20,
        "FRAUD_FLAG": 5,  # Urgent
        "MANUAL_ESCALATION": 30
    }
    return wait_map.get(rule_triggered, 30)