import ast
import re
from statistics import mean

from dotenv import load_dotenv
import os
import sys
import json
import anthropic

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    sys.exit("❌  ANTHROPIC_API_KEY not set. Add it to your .env file.")

client = anthropic.Anthropic(api_key=api_key)


def generate_dataset():
    prompt = """
    Generate an evaluation dataset for a prompt evaluation. The dataset will be used to evaluate prompts that generate Python, JSON, or Regex specifically for AWS-related tasks. Generate an array of JSON objects, each representing task that requires Python, JSON, or a Regex to complete.

    Example output:
    ```json
    [
      {
        "task": "Description of task",
        "format": "python" or "json" or "regex"
      },
      ...additional
    ]
    ```

    * Focus on tasks that can be solved by writing a single Python function, a single JSON object, or a single regex
    * Focus on tasks that do not require writing much code

    Please generate 3 objects.
    """

    messages = []
    add_user_message(messages, prompt)
    add_assistant_message(messages, "```json")
    text = chat(messages, stop_sequences=["```"])

    return json.loads(text)


def run_prompt(test_case):
    """Merges the prompt and test case input, then returns the result"""

    prompt = f"""
    Please solve the following task:
    
    {test_case["task"]}
    
    * Respond only with Python, JSON, or a plain Regex
    * Do not add any comments or commentary or explanation
    """

    messages = []
    add_user_message(messages, prompt)
    add_assistant_message(messages, "```code")
    output = chat(messages, stop_sequences=["```"])
    return output

def grade_by_model(test_case, output):
    # Create evaluation prompt
    eval_prompt = f"""
    You are an expert AWS code reviewer. Your task is to evaluate the following AI-generated solution.

    Original Task:
    <task>
    {test_case["task"]}
    </task>

    Solution to Evaluate:
    <solution>
    {output}
    </solution>

    Output Format
    Provide your evaluation as a structured JSON object with the following fields, in this specific order:
    - "strengths": An array of 1-3 key strengths
    - "weaknesses": An array of 1-3 key areas for improvement
    - "reasoning": A concise explanation of your overall assessment
    - "score": A number between 1-10

    Respond with JSON. Keep your response concise and direct.
    Example response shape:
    {{
        "strengths": string[],
        "weaknesses": string[],
        "reasoning": string,
        "score": number
    }}
        """

    messages = []
    add_user_message(messages, eval_prompt)
    add_assistant_message(messages, "```json")

    eval_text = chat(messages, stop_sequences=["```"])
    return json.loads(eval_text)

def validate_json(text):
    try:
        json.loads(text.strip())
        return 10
    except json.JSONDecodeError:
        return 0


def validate_python(text):
    try:
        ast.parse(text.strip())
        return 10
    except SyntaxError:
        return 0


def validate_regex(text):
    try:
        re.compile(text.strip())
        return 10
    except re.error:
        return 0

def grade_syntax(response, test_case):
    format = test_case["format"]
    if format == "json":
        return validate_json(response)
    elif format == "python":
        return validate_python(response)
    else:
        return validate_regex(response)

def run_test_case(test_case):
    """Calls run_prompt, then grades the result"""

    output = run_prompt(test_case)

    model_grade = grade_by_model(test_case, output)
    model_score = model_grade["score"]
    reasoning = model_grade["reasoning"]

    syntax_score = grade_syntax(output, test_case)
    score = (model_score + syntax_score) / 2

    return {
        "output": output,
        "test_case": test_case,
        "score": score,
        "reasoning": reasoning,
    }


def run_eval(test_data):
    """Loads the dataset and calls run_test_case with each case"""

    results = []

    for test_case in test_data:
        result = run_test_case(test_case)
        results.append(result)

    average_score = mean([result["score"] for result in results])
    print(f"Average score: {average_score}")

    return results

def add_user_message(messages, text):
    user_message = {"role": "user", "content": text}
    messages.append(user_message)


def add_assistant_message(messages, text):
    assistant_message = {"role": "assistant", "content": text}
    messages.append(assistant_message)


def chat(messages, model = 'claude-haiku-4-5', system=None, temperature=1.0, stop_sequences=[]):
    params = {
        "model": model,
        "max_tokens": 1000,
        "messages": messages,
        "temperature": temperature
    }
    if system:
        params["system"] = system
    if stop_sequences:
        params["stop_sequences"] = stop_sequences

    response = client.messages.create(**params)
    print_token_usage(response)
    return response.content[0].text

def print_token_usage(response):
    token_usage = response.usage
    input_tokens = token_usage.input_tokens
    output_tokens = token_usage.output_tokens
    total_tokens = input_tokens + output_tokens
    # print(f"Input tokens: {input_tokens}")
    # print(f"Output tokens: {output_tokens}")
    print(f"Tokens Consumed: {response.model} - {total_tokens}")


def save_dataset(data):
    os.makedirs('./data/tmp', exist_ok=True)
    with open('./data/tmp/dataset.json', 'w') as f:
        json.dump(data, f, indent=2)

    print('Dataset saved to ./data/tmp/dataset.json')


if __name__ == "__main__":
    dataset = generate_dataset()
    # save_dataset(dataset)
    # print(json.dumps(dataset, indent=2))
    # with open("./data/tmp/dataset.json", "r") as f:
    #     dataset = json.load(f)
    eval_result = run_eval(dataset)
    # print(json.dumps(eval_result, indent=2))