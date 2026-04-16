"""
Dataset generation and persistence.
"""

import json
import os

from utils.api import chat, add_user_message, add_assistant_message


# ── Generate ──────────────────────────────────────────────────────────────────

def generate_dataset() -> list[dict]:
    prompt = """
    Generate an evaluation dataset for a prompt evaluation. The dataset will be used to evaluate prompts that generate Python, JSON, or Regex specifically for AWS-related tasks. Generate an array of JSON objects, each representing task that requires Python, JSON, or a Regex to complete.

    Example output:
    ```json
    [
      {
        "task": "Description of task",
        "format": "python" or "json" or "regex"
        "solution_criteria": "Key criteria for evaluating the solution.
      },
      ...additional
    ]
    ```

    * Focus on tasks that can be solved by writing a single Python function, a single JSON object, or a single regex
    * Focus on tasks that do not require writing much code

    Please generate 3 objects.
    """

    messages: list = []
    add_user_message(messages, prompt)
    add_assistant_message(messages, "```json")
    response = chat(messages, stop_sequences=["```"])
    return json.loads(response.content[0].text)


# ── Persist ───────────────────────────────────────────────────────────────────

def save_dataset(data: list[dict], path: str = "./data/tmp/dataset.json") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Dataset saved to {path}")


def load_dataset(path: str = "./data/tmp/dataset.json") -> list[dict]:
    with open(path, "r") as f:
        return json.load(f)

