import os
import sys

from dotenv import load_dotenv

from utils.api import add_user_message, add_assistant_message, chat, text_from_message
from utils.schema import get_current_datetime_schema, add_duration_to_datetime_schema, set_reminder_schema
from utils.tools import get_current_datetime, add_duration_to_datetime, set_reminder

load_dotenv()

if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("❌  ANTHROPIC_API_KEY not set. Add it to your .env file.")

api_key = os.getenv("ANTHROPIC_API_KEY")
model = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-1-20250805")

# ── Tool execution ────────────────────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool and return the result as a string."""
    if tool_name == "get_current_datetime":
        return get_current_datetime(**tool_input)
    if tool_name == "add_duration_to_datetime":
        return add_duration_to_datetime(**tool_input)
    if tool_name == "set_reminder":
        return set_reminder(**tool_input)

    else:
        return f"Unknown tool: {tool_name}"

def single_tool_call():
    messages: list = []

    add_user_message(messages, "What is the exact time, formatted as HH:MM:SS?")
    response = chat(messages, model=model, tools=[get_current_datetime_schema])
    add_assistant_message(messages, response)

    block = response.content[0]
    tool_name = block.name
    tool_input = block.input
    tool_use_id = block.id

    print(f"Tool called: {tool_name}")
    print(f"Tool input: {tool_input}")

    tool_result = execute_tool(tool_name, tool_input)
    print(f"Tool result: {tool_result}\n")

    # Add tool result as a properly formatted message block
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": tool_result,
            }
        ]
    })

    response = chat(messages, model=model)
    print(text_from_message(response))


def run_tools(message):
    tool_requests = [
        block for block in message.content if block.type == "tool_use"
    ]
    tool_result_blocks = []

    for tool_request in tool_requests:
        try:
            tool_result = execute_tool(tool_request.name, tool_request.input)
            tool_result_blocks.append({
                "type": "tool_result",
                "tool_use_id": tool_request.id,
                "content": tool_result,
                "is_error": False,
             })
        except Exception as ex:
            tool_result_blocks.append({
                "type": "tool_result",
                "tool_use_id": tool_request.id,
                "content": f"Error executing tool {tool_request.name}: {str(ex)}",
                "is_error": True,
            })

    return tool_result_blocks


def run_conversation():
    messages: list = []
    add_user_message(
        messages,
        "Set a reminder of my doctor appointment. Its after 179 days from today at 10am."
    )

    while True:
        response = chat(
            messages,
            tools=[
                get_current_datetime_schema,
                add_duration_to_datetime_schema,
                set_reminder_schema
            ],
            should_print_token_usage=False,
        )
        add_assistant_message(messages, response)
        print(text_from_message(response))

        if response.stop_reason != "tool_use":
            break

        tool_results = run_tools(response)

        add_user_message(messages, tool_results)

    return messages

if __name__ == "__main__":
    # single_tool_call()
    run_conversation()
