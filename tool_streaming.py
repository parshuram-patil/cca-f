import json
import os
import sys

from dotenv import load_dotenv

from utils.api import add_user_message, chat_stream, add_assistant_message
from utils.schema import save_article_schema
from utils.tools import save_article

load_dotenv()

if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("❌  ANTHROPIC_API_KEY not set. Add it to your .env file.")

def run_tool(tool_name, tool_input):
    if tool_name == "save_article":
        return save_article(**tool_input)

    return f"Unknown tool: {tool_name}"

def run_tools(message):
    tool_requests = [block for block in message.content if block.type == "tool_use"]
    tool_result_blocks = []

    for tool_request in tool_requests:
        try:
            tool_output = run_tool(tool_request.name, tool_request.input)
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": tool_request.id,
                "content": json.dumps(tool_output),
                "is_error": False,
            }
        except Exception as e:
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": tool_request.id,
                "content": f"Error: {e}",
                "is_error": True,
            }

        tool_result_blocks.append(tool_result_block)

    return tool_result_blocks


def run_conversation(messages, tools=None, tool_choice=None, fine_grained=False):
    while True:
        with chat_stream(
                messages,
                tools=tools,
                betas=["fine-grained-tool-streaming-2025-05-14"] if fine_grained else [],
                tool_choice=tool_choice,
        ) as stream:
            for chunk in stream:
                if chunk.type == "text":
                    print(chunk.text, end="")

                if chunk.type == "content_block_start":
                    if chunk.content_block.type == "tool_use":
                        print(f'\n>>> Tool Call: "{chunk.content_block.name}"')

                if chunk.type == "input_json" and chunk.partial_json:
                    print(chunk.partial_json, end="")

                if chunk.type == "content_block_stop":
                    print("\n")

            response = stream.get_final_message()

        add_assistant_message(messages, response)

        if response.stop_reason != "tool_use":
            break

        tool_results = run_tools(response)
        add_user_message(messages, tool_results)

        if tool_choice:
            break

    return messages

if __name__ == "__main__":
    messages = []
    add_user_message(messages, "Write a haiku about the ocean and save it.")
    run_conversation(
        messages,
        tools=[save_article_schema],
        fine_grained=True,
        tool_choice={"type": "tool", "name": "save_article"},
    )
