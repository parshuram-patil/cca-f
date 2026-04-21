# config.py
# ──────────────────────────────────────────────────────────────────
# Central configuration for the Multi-Tool Agent system
# ──────────────────────────────────────────────────────────────────

# MODEL = "claude-opus-4-7"          # Latest flagship model (Apr 2026)
MAX_TOKENS = 4096
MAX_RETRIES = 3                    # Max retries for transient errors

# ── Business Rule Threshold ────────────────────────────────────────
PAYMENT_ESCALATION_THRESHOLD = 10_000.00   # $10,000 USD
REFUND_ESCALATION_THRESHOLD  =  5_000.00   # $5,000 USD

# ── Error Categories ───────────────────────────────────────────────
ERROR_TRANSIENT   = "transient"    # Retry automatically
ERROR_VALIDATION  = "validation"   # Explain to user, no retry
ERROR_PERMISSION  = "permission"   # Escalate to human agent