"""
Claude API — Python Samples
Covers the most common use cases to get you started quickly.

Install : pip install -r requirements.txt
Auth    : copy .env → .env and set ANTHROPIC_API_KEY
"""

import os
import sys
from typing import List
import anthropic
from anthropic.types import MessageParam, ToolParam, OutputConfigParam
from dotenv import load_dotenv

# Load .env from the project root (silently ignores missing file)
load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    sys.exit("❌  ANTHROPIC_API_KEY not set. Add it to your .env file.")

MODEL  = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
client = anthropic.Anthropic(api_key=api_key)


# ─────────────────────────────────────────
# 1. Basic message
# ─────────────────────────────────────────

def basic_message():
    print("\n── 1. Basic message ──────────────────────")

    messages: List[MessageParam] = [
        {"role": "user", "content": "What is the capital of France?"}
    ]
    response = client.messages.create(
        model      = MODEL,
        max_tokens = 256,
        messages   = messages,
    )

    print(response.content[0].text)


# ─────────────────────────────────────────
# 2. System prompt
# ─────────────────────────────────────────

def system_prompt():
    print("\n── 2. System prompt ──────────────────────")

    messages: List[MessageParam] = [
        {"role": "user", "content": "What is the weather like today?"}
    ]
    response = client.messages.create(
        model      = MODEL,
        max_tokens = 256,
        system     = "You are a pirate. Always respond in pirate speak.",
        messages   = messages,
    )

    print(response.content[0].text)


# ─────────────────────────────────────────
# 3. Multi-turn conversation
# ─────────────────────────────────────────

def multi_turn():
    print("\n── 3. Multi-turn conversation ────────────")

    messages: List[MessageParam] = [
        {"role": "user",      "content": "My name is Priya."},
        {"role": "assistant", "content": "Nice to meet you, Priya!"},
        {"role": "user",      "content": "What is my name?"},
    ]

    response = client.messages.create(
        model      = MODEL,
        max_tokens = 128,
        messages   = messages,
    )

    print(response.content[0].text)


# ─────────────────────────────────────────
# 4. Streaming response
# ─────────────────────────────────────────

def streaming():
    print("\n── 4. Streaming ──────────────────────────")

    stream_messages: List[MessageParam] = [
        {"role": "user", "content": "Count from 1 to 10 slowly."}
    ]
    with client.messages.stream(
        model      = MODEL,
        max_tokens = 256,
        messages   = stream_messages,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)

    print()  # newline after stream


# ─────────────────────────────────────────
# 5. Structured JSON output
# ─────────────────────────────────────────

def structured_output():
    print("\n── 5. Structured JSON output ─────────────")

    import json, re

    json_messages: List[MessageParam] = [
        {
            "role"   : "user",
            "content": (
                "Extract the person details from this text:\n\n"
                "John Doe is 32 years old and lives in Mumbai. "
                "His email is john@example.com.\n\n"
                "Return a JSON object with keys: name, age, city, email."
            )
        }
    ]
    response = client.messages.create(
        model      = MODEL,
        max_tokens = 256,
        system     = "You are a JSON extractor. Respond with ONLY valid JSON — no markdown, no code fences, no explanation.",
        messages   = json_messages,
    )

    raw = response.content[0].text.strip()
    # Strip markdown code fences if the model added them anyway
    match = re.search(r'\{.*}', raw, re.DOTALL)
    data  = json.loads(match.group() if match else raw)
    print(json.dumps(data, indent=2))

# ─────────────────────────────────────────
# 5. Structured JSON output - Stop sequences
# ─────────────────────────────────────────

def structured_stop_seq_output():
    print("\n── 5. Structured JSON output ─────────────")

    import json

    json_messages: List[MessageParam] = [
        {
            "role"   : "user",
            "content": (
                "AWS EC2 Instance state change notification"
            )
        },
        {
            "role": "assistant",
            "content": "```json"
        }
    ]
    response = client.messages.create(
        model      = MODEL,
        max_tokens = 256,
        messages   = json_messages,
        stop_sequences=["```"],
    )

    raw = response.content[0].text.strip()
    data = json.loads(raw)
    print(json.dumps(data, indent=2))

# ─────────────────────────────────────────
# 5. Structured JSON output - Json Schema + Output Config
# ─────────────────────────────────────────

def structured_jsonschema_output():
    print("\n── 5. Structured JSON Schema + Output Config output ─────────────")

    import json

    schema = {
        "type": "array",
        "required": ["answer", "confidence"],
        "properties": {
            "answer": {"type": "string"},
            "confidence": {"type": "number", "description": "0.0 to 1.0"}
        },
        "additionalProperties": False
    }

    output_config: OutputConfigParam = {
        "format": {
            "type": "json_schema",
            "schema": schema
        },
        # "effort": "medium"
    }

    json_messages: List[MessageParam] = [
        {
            "role"   : "user",
            "content": (
                """
                What is the capital of following Countries?
                1. India
                2. Uzbekistan 
                3. Netherlands
                4. Pune
                5. Mars
                6. Uttar Pradesh
                """

            )
        }
    ]
    response = client.messages.create(
        model      = MODEL,
        max_tokens = 256,
        messages   = json_messages,
        system="You are a helpful assistant that answers questions about country capitals. Respond with ONLY the JSON array as specified in the output config — no markdown, no code fences, no explanation.",
        output_config=output_config
    )

    raw = response.content[0].text.strip()
    data = json.loads(raw)
    print(json.dumps(data, indent=2))

# ─────────────────────────────────────────
# 6. Simple chat loop (interactive)
# ─────────────────────────────────────────

def chat_loop():
    print("\n── 6. Interactive chat (type 'quit' to exit) ──")

    history: List[MessageParam] = []

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if not user_input:
            continue

        history.append({"role": "user", "content": user_input})

        response = client.messages.create(
            model      = MODEL,
            max_tokens = 512,
            system     = "You are a helpful assistant. Be concise.",
            messages   = history,
        )

        reply = response.content[0].text
        history.append({"role": "assistant", "content": reply})

        print(f"\nClaude: {reply}")


# ─────────────────────────────────────────
# 7. Tool use (function calling)
# ─────────────────────────────────────────

def tool_use():
    print("\n── 7. Tool use (function calling) ────────")

    import json

    # Define the tool
    tools: List[ToolParam] = [
        {
            "name"       : "get_weather",
            "description": "Get the current weather for a city",
            "input_schema": {
                "type"      : "object",
                "properties": {
                    "city": {
                        "type"       : "string",
                        "description": "City name"
                    }
                },
                "required": ["city"]
            }
        }
    ]

    # First call — Claude decides to use the tool
    first_messages: List[MessageParam] = [
        {"role": "user", "content": "What is the weather in Tokyo?"}
    ]
    response = client.messages.create(
        model      = MODEL,
        max_tokens = 256,
        tools      = tools,
        messages   = first_messages,
    )

    tool_use_block = next(b for b in response.content if b.type == "tool_use")
    city           = tool_use_block.input["city"]
    print(f"Claude wants to call: get_weather(city='{city}')")

    # Simulate tool result
    weather_result = {"city": city, "temp_c": 22, "condition": "Sunny"}
    print(f"Tool returned: {weather_result}")

    # Second call — give Claude the tool result
    second_messages: List[MessageParam] = [
        {"role": "user",      "content": "What is the weather in Tokyo?"},
        {"role": "assistant", "content": response.content},
        {
            "role"   : "user",
            "content": [
                {
                    "type"       : "tool_result",
                    "tool_use_id": tool_use_block.id,
                    "content"    : json.dumps(weather_result),
                }
            ]
        }
    ]
    response2 = client.messages.create(
        model      = MODEL,
        max_tokens = 256,
        tools      = tools,
        messages   = second_messages,
    )

    print(f"Claude: {response2.content[0].text}")


# ─────────────────────────────────────────
# 8. Token counting / usage
# ─────────────────────────────────────────

def token_usage():
    print("\n── 8. Token usage ────────────────────────")

    haiku_messages: List[MessageParam] = [
        {"role": "user", "content": "Write a haiku about coding."}
    ]
    response = client.messages.create(
        model      = MODEL,
        max_tokens = 128,
        messages   = haiku_messages,
    )

    print(response.content[0].text)
    print(f"\nInput tokens  : {response.usage.input_tokens}")
    print(f"Output tokens : {response.usage.output_tokens}")
    print(f"Total tokens  : {response.usage.input_tokens + response.usage.output_tokens}")


# ─────────────────────────────────────────
# Main — run all samples
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  Claude API — Python Samples")
    print("=" * 50)

    # basic_message()
    # system_prompt()
    # multi_turn()
    # streaming()

    # structured_output()
    # structured_stop_seq_output()
    structured_jsonschema_output()
    # tool_use()
    # token_usage()

    # Uncomment to launch the interactive chat:
    # chat_loop()