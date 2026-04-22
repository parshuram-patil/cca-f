# config.py
# ──────────────────────────────────────────────────────────────────
# Central configuration for the Structured Data Extraction Pipeline
# ──────────────────────────────────────────────────────────────────

import os
from dotenv import load_dotenv
load_dotenv()

# ── Model ──────────────────────────────────────────────────────────
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")

# ── Tokens ─────────────────────────────────────────────────────────
MAX_TOKENS         = 4096
MAX_RETRY_TOKENS   = 2048

# ── Validation-Retry ───────────────────────────────────────────────
MAX_VALIDATION_RETRIES = 3          # Max re-tries per document on validation failure

# ── Confidence Thresholds ──────────────────────────────────────────
CONFIDENCE_LOW_THRESHOLD  = 0.70    # Below this → route to human review
CONFIDENCE_HIGH_THRESHOLD = 0.90    # Above this → auto-approve

# ── Batch Processing ───────────────────────────────────────────────
BATCH_SIZE               = 100      # Documents per batch submission
MAX_DOCUMENT_CHARS       = 8_000    # Characters; oversized docs get chunked
BATCH_POLL_INTERVAL_SECS = 5        # Polling interval when waiting for batch
SLA_MINUTES              = 60       # SLA constraint for batch completion

# ── Human Review ───────────────────────────────────────────────────
HUMAN_REVIEW_QUEUE = "human_review_queue.json"

