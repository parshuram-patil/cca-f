"""
Evaluation runner: prompts the model, grades results, aggregates scores.
"""

from statistics import mean

from utils.api import chat, add_user_message, add_assistant_message
from utils.grader import grade_by_model, grade_syntax


# ── Prompt runner ─────────────────────────────────────────────────────────────

def run_prompt(test_case: dict) -> str:
    """Send a test case to the model and return its raw output."""
    prompt = f"""
    Please solve the following task:

    {test_case["task"]}

    * Respond only with Python, JSON, or a plain Regex
    * Do not add any comments or commentary or explanation
    """

    messages: list = []
    add_user_message(messages, prompt)
    add_assistant_message(messages, "```code")
    return chat(messages, stop_sequences=["```"])


# ── Single test case ──────────────────────────────────────────────────────────

def run_test_case(test_case: dict) -> dict:
    """Run one test case and return a graded result."""
    output = run_prompt(test_case)

    model_grade = grade_by_model(test_case, output)
    model_score = model_grade["score"]
    reasoning   = model_grade["reasoning"]

    syntax_score = grade_syntax(output, test_case)

    score = (model_score + syntax_score) / 2

    return {
        "output":     output,
        "test_case":  test_case,
        "score":      score,
        "reasoning":  reasoning,
    }


# ── Full eval ─────────────────────────────────────────────────────────────────

def run_eval(test_data: list[dict]) -> list[dict]:
    """Run all test cases and print the aggregate score."""
    results = [run_test_case(tc) for tc in test_data]

    average_score = mean(r["score"] for r in results)
    print(f"Average score: {average_score:.2f}")

    return results

