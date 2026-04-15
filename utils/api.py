"""
Low-level Anthropic API helpers.
"""

import anthropic
import os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

DEFAULT_MODEL = "claude-haiku-4-5"


# ── Message builders ──────────────────────────────────────────────────────────

def add_user_message(messages: list, text: str) -> None:
    messages.append({"role": "user", "content": text})


def add_assistant_message(messages: list, text: str) -> None:
    messages.append({"role": "assistant", "content": text})


# ── Chat ──────────────────────────────────────────────────────────────────────

def chat(
    messages: list,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    temperature: float = 1.0,
    stop_sequences: list[str] | None = None,
) -> str:
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

    response = client.messages.create(**params)
    _print_token_usage(response)
    return response.content[0].text


# ── Token usage ───────────────────────────────────────────────────────────────

def _print_token_usage(response: anthropic.types.Message) -> None:
    total = response.usage.input_tokens + response.usage.output_tokens
    print(f"Tokens Consumed: {response.model} - {total}")

