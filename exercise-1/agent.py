# agent.py
# ──────────────────────────────────────────────────────────────────
# Step 2: Agentic loop that checks stop_reason to determine whether
# to continue tool execution or present final response.
#
# Handles:
#   • "tool_use"  → execute tool(s), feed results back, continue
#   • "end_turn"  → present final synthesised response
#
# Step 3 (error handling):
#   • transient   → retry up to MAX_RETRIES
#   • validation  → explain to user (no retry)
#   • permission  → auto-escalate to human agent
#
# Step 5: Handles multi-concern messages by letting Claude decompose
# and call multiple tools, then synthesise a unified response.
# ──────────────────────────────────────────────────────────────────

import json
import os
import sys

import anthropic
from tools import TOOLS
from tool_executor import execute_tool
from config import MAX_TOKENS, MAX_RETRIES, ERROR_TRANSIENT, ERROR_PERMISSION
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    sys.exit("❌  ANTHROPIC_API_KEY not set. Add it to your .env file.")

MODEL  = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

client = anthropic.Anthropic(api_key=api_key)


def run_agent(user_message: str) -> str:
    """
    Main agentic loop.

    Reference: Anthropic docs — "The agentic loop (client tools)"
    Pattern  : while stop_reason == "tool_use" → execute → feed back
    Exits on : stop_reason == "end_turn" (natural completion)

    Args:
        user_message: The raw user request (may contain multiple concerns)

    Returns:
        The final synthesised response text from Claude.
    """
    print(f"\n{'═' * 60}")
    print(f"[AGENT] 🤖 User: {user_message}")
    print(f"{'═' * 60}")

    # ── Conversation history (context management) ──────────────────
    # Reference: Domain 5 — Context Management
    messages = [{"role": "user", "content": user_message}]

    # ── Retry tracking for transient errors ───────────────────────
    retry_counts: dict[str, int] = {}  # keyed by tool_use_id

    # ── Agentic Loop ───────────────────────────────────────────────
    # Reference: "The canonical shape is a while loop keyed on stop_reason"
    # Source: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/how-tool-use-works

    while True:

        # ── API Call ───────────────────────────────────────────────
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=(
                "You are a helpful and professional banking assistant. "
                "When handling customer requests:\n"
                "1. Use get_account_balance to check account status BEFORE transactions.\n"
                "2. Use process_payment ONLY for outgoing payments (debits/charges).\n"
                "3. Use process_refund ONLY for incoming credits (refunds/reversals).\n"
                "4. Use escalate_to_human_agent when a tool returns errorCategory='permission', "
                "   or when the customer explicitly requests a human.\n"
                "5. For transient errors (isRetryable=true), retry automatically up to "
                f"  {MAX_RETRIES} times before explaining the issue.\n"
                "6. When multiple issues are raised, handle each one and provide a "
                "   unified summary at the end.\n"
                "7. Always be transparent about what happened and what the next steps are."
            ),
            tools=TOOLS,
            messages=messages
        )

        print(f"\n[AGENT] Stop reason: {response.stop_reason}")

        # ── Check stop_reason ──────────────────────────────────────
        # Reference: https://docs.anthropic.com/en/docs/build-with-claude/handling-stop-reasons

        # ── CASE 1: end_turn → Present final response ──────────────
        if response.stop_reason == "end_turn":
            final_text = _extract_text(response)
            print(f"\n[AGENT] ✅ Final response:\n{final_text}")
            return final_text

        # ── CASE 2: tool_use → Execute tools, loop back ────────────
        elif response.stop_reason == "tool_use":

            # Collect all tool_use blocks (Claude may request multiple)
            tool_use_blocks = [
                block for block in response.content
                if block.type == "tool_use"
            ]

            # Append Claude's response to conversation history
            messages.append({"role": "assistant", "content": response.content})

            # Execute each tool and collect results
            tool_results = []

            for tool_use in tool_use_blocks:
                tool_name = tool_use.name
                tool_input = tool_use.input
                tool_id = tool_use.id

                result_json = execute_tool(tool_name, tool_input)
                result_data = json.loads(result_json)

                # ── Error Handling (Step 3) ────────────────────────

                handled_result = _handle_tool_error(
                    tool_id=tool_id,
                    tool_name=tool_name,
                    tool_input=tool_input,
                    result_data=result_data,
                    retry_counts=retry_counts
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": json.dumps(handled_result)
                })

            # Feed all tool results back into the conversation
            # Reference: "Send a new request containing tool_result blocks"
            messages.append({"role": "user", "content": tool_results})

        # ── CASE 3: Other stop reasons (max_tokens, refusal, etc.) ─
        else:
            print(f"[AGENT] ⚠️ Unexpected stop reason: {response.stop_reason}")
            return (
                f"I encountered an unexpected situation "
                f"(stop_reason: {response.stop_reason}). "
                "Please try again or contact support."
            )


def _handle_tool_error(
        tool_id: str,
        tool_name: str,
        tool_input: dict,
        result_data: dict,
        retry_counts: dict
) -> dict:
    """
    Implements Step 3 error handling logic.

    - transient  : retry up to MAX_RETRIES, then pass failure to Claude
    - validation : pass failure directly to Claude (it will explain to user)
    - permission : auto-trigger escalation tool call via modified result

    Returns the final result dict (either original, retried, or escalation info).
    """
    if result_data.get("success", True):
        return result_data  # No error, pass through

    error_category = result_data.get("errorCategory", "")
    is_retryable = result_data.get("isRetryable", False)

    # ── TRANSIENT: retry automatically ────────────────────────────
    if error_category == ERROR_TRANSIENT and is_retryable:
        current_retries = retry_counts.get(tool_id, 0)

        if current_retries < MAX_RETRIES:
            retry_counts[tool_id] = current_retries + 1
            print(f"\n[AGENT] 🔄 Transient error — retrying {tool_name} "
                  f"(attempt {current_retries + 1}/{MAX_RETRIES})")

            # Re-execute the tool
            retry_result_json = execute_tool(tool_name, tool_input)
            retry_result = json.loads(retry_result_json)

            if retry_result.get("success", False):
                print(f"[AGENT] ✅ Retry succeeded!")
                return retry_result
            else:
                # Update result and potentially retry again (recursive)
                return _handle_tool_error(
                    tool_id, tool_name, tool_input,
                    retry_result, retry_counts
                )
        else:
            print(f"[AGENT] ❌ Max retries ({MAX_RETRIES}) exceeded for {tool_name}")
            result_data["message"] += (
                f" (Retried {MAX_RETRIES} times — service still unavailable.)"
            )

    # ── PERMISSION: auto-escalate ─────────────────────────────────
    elif error_category == ERROR_PERMISSION:
        print(f"[AGENT] 🚨 Permission error — auto-escalating")
        # Claude will see this and know to call escalate_to_human_agent
        result_data["autoEscalateHint"] = (
            "Please call escalate_to_human_agent immediately "
            "with priority='high'."
        )

    # VALIDATION: pass through — Claude will explain to user
    return result_data


def _extract_text(response) -> str:
    """Extract the final text response from Claude's message."""
    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return "I've completed your request. Please let me know if you need anything else."