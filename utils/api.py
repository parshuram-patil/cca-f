"""
Low-level Anthropic API helpers.
"""

import anthropic
from anthropic.types import Message, ToolParam
import os

from dotenv import load_dotenv
load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

DEFAULT_MODEL = "claude-haiku-4-5"


# ── Message builders ──────────────────────────────────────────────────────────

def add_user_message(messages: list, message) -> None:
    messages.append({
        "role": "user",
        "content": message.content if isinstance(message, Message) else message
    })


def add_assistant_message(messages: list, message) -> None:
    messages.append({
        "role": "assistant",
        "content": message.content if isinstance(message, Message) else message
    })


# ── Chat ──────────────────────────────────────────────────────────────────────

def chat(
    messages: list,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    temperature: float = 1.0,
    stop_sequences: list[str] | None = None,
    tools: list[ToolParam] | None = None,
    should_print_token_usage: bool = True,
) -> anthropic.types.Message:
    """
    Send messages to Claude and return the complete response object.
    Caller can access: response.content, response.stop_reason, response.usage, etc.
    """
    params: dict = {
        "model": model,
        "max_tokens": 1000,
        "messages": messages,
        "temperature": temperature,
    }
    if system:
        params["system"] = system
    if stop_sequences:
        params["stop_sequences"] = stop_sequences
    if tools:
        params["tools"] = tools

    response = client.messages.create(**params)
    if should_print_token_usage:
        _print_token_usage(response)
    return response

# ── Extract text content from a Message ───────────────────────────────────────────────────────────────
def text_from_message(message):
    return "\n".join(
        [block.text for block in message.content if block.type == "text"]
    )

# ── Token usage ───────────────────────────────────────────────────────────────

def _print_token_usage(response: anthropic.types.Message) -> None:
    total = response.usage.input_tokens + response.usage.output_tokens
    print(f"Tokens Consumed: {response.model} - {total}")

