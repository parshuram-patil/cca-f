"""
prompting.py — Prompt evaluation entry point.

Usage:
    python prompting.py                  # generate dataset + run evaluation
    python prompting.py --load           # skip generation, load existing dataset.json
    python prompting.py --eval-only      # same as --load
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("❌  ANTHROPIC_API_KEY not set. Add it to your .env file.")

from utils.api import chat, add_user_message, add_assistant_message
from utils.prompt_evaluator import PromptEvaluator

# ── Configuration ─────────────────────────────────────────────────────────────

DATASET_FILE    = "data/tmp/dataset.json"
JSON_OUTPUT     = "data/tmp/output.json"
HTML_OUTPUT     = "data/tmp/output.html"

# ── Evaluator ─────────────────────────────────────────────────────────────────

# Increase max_concurrent_tasks for faster runs (watch out for rate limits)
evaluator = PromptEvaluator(max_concurrent_tasks=3)

# ── Task definition ───────────────────────────────────────────────────────────

TASK_DESCRIPTION = """
Summarize an AWS CloudWatch alarm configuration and explain what it monitors,
when it triggers, and what action it takes.
"""

PROMPT_INPUTS_SPEC = {
    "alarm_config": "A JSON string representing an AWS CloudWatch alarm configuration",
}

# ── Prompt under test ─────────────────────────────────────────────────────────

def run_prompt(prompt_inputs: dict) -> str:
    """
    This function is called once per test case.
    Edit the prompt here to iterate on what you're evaluating.
    """
    prompt = f"""
    You are an AWS expert. Analyze the following CloudWatch alarm configuration and provide a clear summary.

    CloudWatch Alarm Configuration:
    {prompt_inputs["alarm_config"]}

    Provide:
    1. What the alarm monitors
    2. When it triggers (threshold / conditions)
    3. What action it takes when triggered
    """

    messages: list = []
    add_user_message(messages, prompt)
    return chat(messages)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs("data/tmp", exist_ok=True)

    load_existing = "--load" in sys.argv or "--eval-only" in sys.argv

    if load_existing:
        print(f"Loading existing dataset from {DATASET_FILE} ...")
    else:
        print("Generating dataset ...")
        evaluator.generate_dataset(
            task_description=TASK_DESCRIPTION,
            prompt_inputs_spec=PROMPT_INPUTS_SPEC,
            num_cases=3,
            output_file=DATASET_FILE,
        )

    print("Running evaluation ...")
    results = evaluator.run_evaluation(
        run_prompt_function=run_prompt,
        dataset_file=DATASET_FILE,
        json_output_file=JSON_OUTPUT,
        html_output_file=HTML_OUTPUT,
    )

