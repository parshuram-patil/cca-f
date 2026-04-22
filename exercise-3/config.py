# config.py
# ──────────────────────────────────────────────────────────────────
# Configuration for the Multi-Agent Research Pipeline
# ──────────────────────────────────────────────────────────────────

import os
from dotenv import load_dotenv
load_dotenv()

# ── Model ──────────────────────────────────────────────────────────
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")

# ── Tokens ─────────────────────────────────────────────────────────
MAX_TOKENS = 4096
SUBAGENT_MAX_TOKENS = 2048

# ── Timeouts ───────────────────────────────────────────────────────
SUBAGENT_TIMEOUT_SECS = 30      # Simulated timeout threshold
SIMULATED_TIMEOUT_AGENT = "web_search"   # Agent to simulate timeout on

# ── Retry / Error Handling ─────────────────────────────────────────
MAX_RETRIES = 2

# ── Output ─────────────────────────────────────────────────────────
REPORT_OUTPUT_FILE = "research_report.json"

