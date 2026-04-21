# error_handler.py
# ──────────────────────────────────────────────────────────────────
# Step 3: Structured error responses with errorCategory,
# isRetryable boolean, and human-readable descriptions.
# ──────────────────────────────────────────────────────────────────

import json
import random
from config import ERROR_TRANSIENT, ERROR_VALIDATION, ERROR_PERMISSION


def make_error(error_category: str, code: str, message: str, is_retryable: bool) -> dict:
    """
    Factory for structured error responses.

    All tool errors must include:
      - errorCategory: 'transient' | 'validation' | 'permission'
      - isRetryable: bool
      - errorCode: machine-readable code
      - message: human-readable description

    Reference: Anthropic tool-use best practices — tool results
    should be parseable by Claude to determine next action.
    """
    return {
        "success": False,
        "errorCategory": error_category,
        "errorCode": code,
        "isRetryable": is_retryable,
        "message": message
    }


# ── Pre-built Errors by Category ──────────────────────────────────

ERRORS = {

    # TRANSIENT: temporary, infrastructure failures → RETRY
    "db_timeout": make_error(
        ERROR_TRANSIENT,
        "DB_TIMEOUT",
        "Database connection timed out. This is a temporary issue — please retry.",
        is_retryable=True
    ),
    "service_unavailable": make_error(
        ERROR_TRANSIENT,
        "SERVICE_UNAVAILABLE",
        "The payment service is temporarily unavailable (503). Retry in a few moments.",
        is_retryable=True
    ),

    # VALIDATION: bad inputs → EXPLAIN TO USER, do NOT retry
    "insufficient_funds": make_error(
        ERROR_VALIDATION,
        "INSUFFICIENT_FUNDS",
        "The account does not have sufficient funds to complete this payment.",
        is_retryable=False
    ),
    "invalid_account": make_error(
        ERROR_VALIDATION,
        "INVALID_ACCOUNT",
        "The account ID provided does not exist or is malformed.",
        is_retryable=False
    ),
    "account_frozen": make_error(
        ERROR_VALIDATION,
        "ACCOUNT_FROZEN",
        "This account is currently frozen and cannot process transactions.",
        is_retryable=False
    ),
    "negative_amount": make_error(
        ERROR_VALIDATION,
        "NEGATIVE_AMOUNT",
        "Amount must be a positive number greater than zero.",
        is_retryable=False
    ),
    "transaction_not_found": make_error(
        ERROR_VALIDATION,
        "TRANSACTION_NOT_FOUND",
        "The original transaction ID was not found. Cannot process refund.",
        is_retryable=False
    ),

    # PERMISSION: requires human approval → ESCALATE
    "high_value_transaction": make_error(
        ERROR_PERMISSION,
        "HIGH_VALUE_TRANSACTION",
        "This transaction exceeds the automated processing threshold and requires manager approval.",
        is_retryable=False
    ),
    "fraud_flag": make_error(
        ERROR_PERMISSION,
        "FRAUD_FLAG",
        "This transaction has been flagged for fraud review by our security system.",
        is_retryable=False
    ),
}


def inject_transient_error_randomly(probability: float = 0.15) -> bool:
    """Simulate transient failures at a given probability rate."""
    return random.random() < probability