# test_scenarios.py
# ──────────────────────────────────────────────────────────────────
# Step 5: Tests with multi-concern messages.
# Each scenario exercises multiple tools and verifies the agent
# decomposes, handles, and synthesises a unified response.
# ──────────────────────────────────────────────────────────────────

from agent import run_agent


def separator(title: str):
    print(f"\n{'━'*70}")
    print(f"  TEST: {title}")
    print(f"{'━'*70}")


# ══════════════════════════════════════════════════════════════════
# Scenario 1: MULTI-CONCERN — Balance + Payment (normal flow)
# Tests: Tool decomposition + sequential execution + synthesis
# ══════════════════════════════════════════════════════════════════
def test_multi_concern_balance_and_payment():
    separator("Multi-Concern: Balance Check + Payment")
    response = run_agent(
        "Hi, I need two things: first, can you check my balance for account ACC-100001? "
        "And second, please process a $500 payment from ACC-100001 to VENDOR-001 for "
        "'Office supplies'."
    )
    print(f"\n[FINAL RESPONSE]\n{response}")


# ══════════════════════════════════════════════════════════════════
# Scenario 2: ESCALATION — High-value payment triggers hook
# Tests: Programmatic hook intercept → escalation workflow
# ══════════════════════════════════════════════════════════════════
def test_high_value_payment_escalation():
    separator("Escalation Hook: Payment >= $10,000")
    response = run_agent(
        "Please process a payment of $15,000 from account ACC-100001 "
        "to VENDOR-BIG-001 for 'Annual software license'."
    )
    print(f"\n[FINAL RESPONSE]\n{response}")


# ══════════════════════════════════════════════════════════════════
# Scenario 3: VALIDATION ERROR — Insufficient funds
# Tests: Error explanation to user without retry
# ══════════════════════════════════════════════════════════════════
def test_insufficient_funds_error():
    separator("Validation Error: Insufficient Funds")
    response = run_agent(
        "Process a payment of $2000 from account ACC-100002 "
        "to MERCHANT-007 for 'Premium subscription'."
    )
    print(f"\n[FINAL RESPONSE]\n{response}")


# ══════════════════════════════════════════════════════════════════
# Scenario 4: HIGH-VALUE REFUND — Triggers supervisor escalation
# Tests: Refund hook threshold + escalation workflow
# ══════════════════════════════════════════════════════════════════
def test_high_value_refund_escalation():
    separator("Escalation Hook: Refund >= $5,000")
    response = run_agent(
        "I need a refund of $6,000 on transaction TXN-20002 "
        "for account ACC-100002. Reason: defective product."
    )
    print(f"\n[FINAL RESPONSE]\n{response}")


# ══════════════════════════════════════════════════════════════════
# Scenario 5: FULL MULTI-CONCERN — 3 issues in one message
# Tests: Full decomposition + parallel concerns + unified synthesis
# ══════════════════════════════════════════════════════════════════
def test_full_multi_concern():
    separator("Full Multi-Concern: 3 Issues in One Request")
    response = run_agent(
        "I have three issues: "
        "1) Check the balance of account ACC-100001. "
        "2) Process a $300 payment from ACC-100001 to PAYEE-555 for 'Consulting fee'. "
        "3) Issue a $200 refund on transaction TXN-20001 for account ACC-100001, "
        "   reason: 'overcharged'."
    )
    print(f"\n[FINAL RESPONSE]\n{response}")


# ══════════════════════════════════════════════════════════════════
# Scenario 6: FROZEN ACCOUNT — Validation error on frozen account
# ══════════════════════════════════════════════════════════════════
def test_frozen_account_error():
    separator("Validation Error: Frozen Account")
    response = run_agent(
        "Please check balance and make a $100 payment from account ACC-FROZEN "
        "to VENDOR-X for 'test payment'."
    )
    print(f"\n[FINAL RESPONSE]\n{response}")


# ══════════════════════════════════════════════════════════════════
# Scenario 7: HUMAN ESCALATION REQUEST — Customer asks for human
# ══════════════════════════════════════════════════════════════════
def test_manual_human_escalation():
    separator("Manual Escalation: Customer Requests Human Agent")
    response = run_agent(
        "I'm very frustrated. Nothing is working. "
        "I want to speak to a human agent immediately about my account ACC-100001."
    )
    print(f"\n[FINAL RESPONSE]\n{response}")


# ══════════════════════════════════════════════════════════════════
# MAIN — Run all test scenarios
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    test_multi_concern_balance_and_payment()
    test_high_value_payment_escalation()
    test_insufficient_funds_error()
    test_high_value_refund_escalation()
    test_full_multi_concern()
    test_frozen_account_error()
    test_manual_human_escalation()