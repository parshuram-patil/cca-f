# main.py
# ──────────────────────────────────────────────────────────────────
# Run a single demonstration with annotated console output.
# ──────────────────────────────────────────────────────────────────

from agent import run_agent

if __name__ == "__main__":
    # Full multi-concern demo
    result = run_agent(
        "I have three things: "
        "1) Check balance on ACC-100001. "
        "2) Pay $500 from ACC-100001 to VENDOR-ABC for 'server hosting'. "
        "3) Refund $6,500 on TXN-20002 for account ACC-100002 (duplicate charge)."
    )
    print("\n" + "═"*60)
    print("AGENT FINAL RESPONSE:")
    print("═"*60)
    print(result)