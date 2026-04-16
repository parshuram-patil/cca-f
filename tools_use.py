import json
import os
import sys
import anthropic

from dotenv import load_dotenv

from utils.api import add_user_message, add_assistant_message, chat, client
from utils.schema import get_current_datetime_schema
from utils.tools import get_current_datetime

load_dotenv()

if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("❌  ANTHROPIC_API_KEY not set. Add it to your .env file.")

api_key = os.getenv("ANTHROPIC_API_KEY")
model = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-1-20250805")

# ── Tool execution ────────────────────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool and return the result as a string."""
    if tool_name == "get_current_datetime":
        return get_current_datetime(
            date_format=tool_input.get("date_format", "%Y-%m-%d %H:%M:%S")
        )
    else:
        return f"Unknown tool: {tool_name}"


if __name__ == "__main__":
    messages: list = []

    add_user_message(messages, "What is the exact time, formatted as HH:MM:SS?")
    response = chat(messages, model=model, tools=[get_current_datetime_schema])
    add_assistant_message(messages, response)
    print(messages)



    # # Add assistant's response to messages
    # messages.append({"role": "assistant", "content": response.content})
    #
    # # ── Check for tool use ────────────────────────────────────────────────────
    #
    # if response.stop_reason == "tool_use":
    #
    #     # Find and execute the tool
    #     for block in response.content:
    #         if block.type == "tool_use":
    #             tool_name = block.name
    #             tool_input = block.input
    #             tool_use_id = block.id
    #
    #             print(f"Tool called: {tool_name}")
    #             print(f"Tool input: {tool_input}")
    #
    #             # Execute the tool
    #             tool_result = execute_tool(tool_name, tool_input)
    #             print(f"Tool result: {tool_result}\n")
    #
    #             # Add tool result to messages
    #             messages.append({
    #                 "role": "user",
    #                 "content": [
    #                     {
    #                         "type": "tool_result",
    #                         "tool_use_id": tool_use_id,
    #                         "content": tool_result,
    #                     }
    #                 ]
    #             })
    #
    #     # ── Second call with tool result ──────────────────────────────────────
    #
    #     print("Sending tool result back to Claude...\n")
    #     final_response = client.messages.create(
    #         model=model,
    #         max_tokens=1000,
    #         messages=messages,
    #         tools=[get_current_datetime_schema],
    #     )
    #
    #     print(f"Final response stop reason: {final_response.stop_reason}")
    #     print(f"Final response:\n{final_response.content[0].text}")
    # else:
    #     print("No tool use in response")
