# tools.py
# ──────────────────────────────────────────────────────────────────
# Step 1: Define 3–4 MCP tools with DETAILED, DIFFERENTIATING
# descriptions. Critical: process_payment vs process_refund are
# deliberately similar — their descriptions MUST prevent confusion.
# ──────────────────────────────────────────────────────────────────

TOOLS = [

    # ── Tool 1: Account Balance Inquiry ───────────────────────────
    {
        "name": "get_account_balance",
        "description": (
            "Retrieves the CURRENT balance and account status for a customer account. "
            "Use this tool ONLY to READ/QUERY account information — it performs NO financial "
            "transactions and has NO side effects. "
            "Boundary: This tool cannot initiate payments, refunds, or any money movement. "
            "Input: account_id (string, format 'ACC-XXXXXX'). "
            "Returns: balance (float, USD), account_status ('active'|'frozen'|'closed'), "
            "currency (string), and last_updated (ISO-8601 timestamp). "
            "Call this BEFORE process_payment or process_refund to confirm sufficient funds "
            "or eligibility."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Customer account ID in format ACC-XXXXXX (e.g., ACC-123456)"
                }
            },
            "required": ["account_id"]
        }
    },

    # ── Tool 2: Process Payment (DEBIT / CHARGE) ───────────────────
    # ⚠️  Similar to process_refund — description carefully
    #     differentiates DIRECTION of money flow.
    {
        "name": "process_payment",
        "description": (
            "Initiates a DEBIT transaction — money flows OUT of the customer's account "
            "to a merchant or payee. "
            "Use this ONLY when the customer wants to PAY, CHARGE, PURCHASE, or SEND money. "
            "Do NOT use for refunds, credits, or reversals — use process_refund instead. "
            "IMPORTANT boundary: Payments >= $10,000 USD require manager approval and "
            "will be automatically intercepted for escalation. "
            "Input: account_id (string), amount (float, positive USD), "
            "payee_id (string), description (string). "
            "Returns: transaction_id (string), status ('success'|'pending'|'failed'), "
            "new_balance (float)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Source account ID (ACC-XXXXXX)"
                },
                "amount": {
                    "type": "number",
                    "description": "Positive dollar amount to DEBIT from account"
                },
                "payee_id": {
                    "type": "string",
                    "description": "Recipient/merchant identifier"
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable payment description"
                }
            },
            "required": ["account_id", "amount", "payee_id", "description"]
        }
    },

    # ── Tool 3: Process Refund (CREDIT / REVERSE) ─────────────────
    # ⚠️  Similar to process_payment — description carefully
    #     differentiates DIRECTION of money flow.
    {
        "name": "process_refund",
        "description": (
            "Initiates a CREDIT transaction — money flows INTO the customer's account "
            "as a reversal or reimbursement. "
            "Use this ONLY when reversing a prior charge, issuing a reimbursement, "
            "or crediting the customer. "
            "Do NOT use for new purchases or payments — use process_payment instead. "
            "IMPORTANT boundary: Refunds >= $5,000 USD require supervisor approval and "
            "will be automatically intercepted for escalation. "
            "Requires original_transaction_id to verify refund eligibility. "
            "Input: account_id (string), amount (float, positive USD), "
            "original_transaction_id (string), reason (string). "
            "Returns: refund_id (string), status ('success'|'pending'|'failed'), "
            "new_balance (float)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Customer account ID to CREDIT (ACC-XXXXXX)"
                },
                "amount": {
                    "type": "number",
                    "description": "Positive dollar amount to CREDIT back to account"
                },
                "original_transaction_id": {
                    "type": "string",
                    "description": "Transaction ID of the original charge being refunded"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for refund (e.g., 'duplicate charge', 'item not received')"
                }
            },
            "required": ["account_id", "amount", "original_transaction_id", "reason"]
        }
    },

    # ── Tool 4: Escalate to Human Agent ───────────────────────────
    {
        "name": "escalate_to_human_agent",
        "description": (
            "Creates an escalation ticket and routes the case to a human specialist. "
            "Use this tool when: (1) the customer explicitly requests to speak to a human, "
            "(2) an error with errorCategory='permission' is returned by another tool, "
            "(3) the situation requires judgment beyond automated handling. "
            "Do NOT use as a fallback for transient errors — retry those instead. "
            "Input: account_id (string), reason (string), priority ('low'|'medium'|'high'|'urgent'), "
            "context (string — brief summary of the conversation so far). "
            "Returns: ticket_id (string), estimated_wait_minutes (int), assigned_team (string)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Customer account ID"
                },
                "reason": {
                    "type": "string",
                    "description": "Clear reason for escalation"
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Escalation priority level"
                },
                "context": {
                    "type": "string",
                    "description": "Summary of conversation context for the human agent"
                }
            },
            "required": ["account_id", "reason", "priority", "context"]
        }
    }
]