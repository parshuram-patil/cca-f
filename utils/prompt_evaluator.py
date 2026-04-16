"""
PromptEvaluator — orchestrates dataset generation, prompt execution, and grading.
"""

import json
import re
import concurrent.futures
from statistics import mean
from textwrap import dedent

from utils.api import chat, add_user_message, add_assistant_message
from utils.report import generate_prompt_evaluation_report


class PromptEvaluator:
    def __init__(self, max_concurrent_tasks: int = 3) -> None:
        self.max_concurrent_tasks = max_concurrent_tasks

    # ── Template rendering ────────────────────────────────────────────────────

    def render(self, template_string: str, variables: dict) -> str:
        """Replace {key} placeholders with values, then unescape {{ / }}."""
        for placeholder in re.findall(r"{([^{}]+)}", template_string):
            if placeholder in variables:
                template_string = template_string.replace(
                    "{" + placeholder + "}", str(variables[placeholder])
                )
        return template_string.replace("{{", "{").replace("}}", "}")

    # ── Dataset generation ────────────────────────────────────────────────────

    def generate_unique_ideas(
        self,
        task_description: str,
        prompt_inputs_spec: dict,
        num_cases: int,
    ) -> list[str]:
        """Generate a list of unique scenario ideas for the given task."""

        example_inputs = "".join(
            f'"{k}": str # {v.replace(chr(10), chr(92) + "n")},'
            for k, v in prompt_inputs_spec.items()
        )

        prompt = dedent("""
            Generate {num_cases} unique, diverse ideas for testing a prompt that accomplishes this task:

            <task_description>
            {task_description}
            </task_description>

            The prompt will receive the following inputs
            <prompt_inputs>
            {prompt_inputs}
            </prompt_inputs>

            Each idea should represent a distinct scenario or example that tests different aspects of the task.

            Output Format:
            Provide your response as a structured JSON array where each item is a brief description of the idea.

            Example:
            ```json
            [
                "Testing with technical computer science terminology",
                "Testing with medical research findings",
                ...
            ]
            ```

            Ensure each idea is:
            - Clearly distinct from the others
            - Relevant to the task description
            - Specific enough to guide generation of a full test case
            - Quick to solve without requiring extensive computation or multi-step processing
            - Solvable with no more than 400 tokens of output

            Remember, only generate {num_cases} unique ideas
        """)

        messages: list = []
        add_user_message(
            messages,
            self.render(prompt, {
                "task_description": task_description,
                "num_cases": num_cases,
                "prompt_inputs": example_inputs,
            }),
        )
        add_assistant_message(messages, "```json")
        text = chat(
            messages,
            system="You are a test scenario designer specialized in creating diverse, unique testing scenarios.",
            stop_sequences=["```"],
            temperature=1.0,
        )
        return json.loads(text)

    def generate_test_case(
        self,
        task_description: str,
        idea: str,
        prompt_inputs_spec: dict,
    ) -> dict:
        """Generate a detailed test case for a specific idea."""

        example_inputs = "".join(
            f'"{k}": "EXAMPLE_VALUE", // {v.replace(chr(10), chr(92) + "n")}\n'
            for k, v in prompt_inputs_spec.items()
        )
        allowed_keys = ", ".join(f'"{k}"' for k in prompt_inputs_spec)

        prompt = dedent("""
            Generate a single detailed test case for a prompt evaluation based on:

            <task_description>
            {task_description}
            </task_description>

            <specific_idea>
            {idea}
            </specific_idea>

            <allowed_input_keys>
            {allowed_keys}
            </allowed_input_keys>

            Output Format:
            ```json
            {{
                "prompt_inputs": {{
                {example_prompt_inputs}
                }},
                "solution_criteria": ["criterion 1", "criterion 2", ...]
            }}
            ```

            IMPORTANT REQUIREMENTS:
            - You MUST ONLY use these exact input keys: {allowed_keys}
            - All keys listed in allowed_input_keys must be included
            - Make the test case realistic and practically useful
            - Include 1-4 concise, measurable solution criteria directly tied to the task
            - Quick to solve, solvable with no more than 400 tokens of output
            - DO NOT include any fields beyond those specified
        """)

        messages: list = []
        add_user_message(
            messages,
            self.render(prompt, {
                "task_description": task_description,
                "idea": idea,
                "allowed_keys": allowed_keys,
                "example_prompt_inputs": example_inputs,
            }),
        )
        add_assistant_message(messages, "```json")
        text = chat(
            messages,
            system="You are a test case creator specializing in designing evaluation scenarios.",
            stop_sequences=["```"],
            temperature=0.7,
        )

        test_case = json.loads(text)
        test_case["task_description"] = task_description
        test_case["scenario"] = idea
        return test_case

    def generate_dataset(
        self,
        task_description: str,
        prompt_inputs_spec: dict | None = None,
        num_cases: int = 3,
        output_file: str = "dataset.json",
    ) -> list[dict]:
        """Generate a full dataset and write it to *output_file*."""

        if prompt_inputs_spec is None:
            prompt_inputs_spec = {}

        ideas = self.generate_unique_ideas(task_description, prompt_inputs_spec, num_cases)

        dataset: list[dict] = []
        completed = 0
        total = len(ideas)
        last_milestone = 0

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_concurrent_tasks
        ) as executor:
            futures = {
                executor.submit(
                    self.generate_test_case, task_description, idea, prompt_inputs_spec
                ): idea
                for idea in ideas
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    dataset.append(future.result())
                except Exception as exc:
                    print(f"Error generating test case: {exc}")
                finally:
                    completed += 1
                    milestone = (int(completed / total * 100) // 20) * 20
                    if milestone > last_milestone:
                        print(f"Generated {completed}/{total} test cases")
                        last_milestone = milestone

        with open(output_file, "w") as f:
            json.dump(dataset, f, indent=2)

        print(f"Dataset saved → {output_file}")
        return dataset

    # ── Grading ───────────────────────────────────────────────────────────────

    def grade_output(
        self, test_case: dict, output: str, extra_criteria: str | None = None
    ) -> dict:
        """Grade one output using the model."""

        prompt_inputs_str = "".join(
            f'"{k}":"{v.replace(chr(10), chr(92) + "n")}",\n'
            for k, v in test_case["prompt_inputs"].items()
        )

        extra_section = ""
        if extra_criteria:
            extra_section = self.render(
                dedent("""
                    Mandatory Requirements - ANY VIOLATION MEANS AUTOMATIC FAILURE (score of 3 or lower):
                    <extra_important_criteria>
                    {extra_criteria}
                    </extra_important_criteria>
                """),
                {"extra_criteria": extra_criteria},
            )

        eval_template = dedent("""
            Your task is to evaluate the following AI-generated solution with EXTREME RIGOR.

            Original task description:
            <task_description>
            {task_description}
            </task_description>

            Original task inputs:
            <task_inputs>
            {{ {prompt_inputs} }}
            </task_inputs>

            Solution to Evaluate:
            <solution>
            {output}
            </solution>

            Criteria:
            <criteria>
            {solution_criteria}
            </criteria>

            {extra_criteria_section}

            Scoring Guidelines:
            * 1-3: Fails one or more MANDATORY requirements
            * 4-6: Meets mandatory requirements but has significant deficiencies
            * 7-8: Meets all mandatory and most secondary criteria
            * 9-10: Meets all criteria

            IMPORTANT: Grade ONLY on listed criteria. ANY mandatory violation → score ≤ 3.

            Output Format (JSON only):
            {{
                "strengths": string[],
                "weaknesses": string[],
                "reasoning": string,
                "score": number
            }}
        """)

        messages: list = []
        add_user_message(
            messages,
            self.render(eval_template, {
                "task_description": test_case["task_description"],
                "prompt_inputs": prompt_inputs_str,
                "output": output,
                "solution_criteria": "\n".join(test_case["solution_criteria"]),
                "extra_criteria_section": extra_section,
            }),
        )
        add_assistant_message(messages, "```json")
        eval_text = chat(messages, stop_sequences=["```"], temperature=0.0)
        return json.loads(eval_text)

    # ── Single test case ──────────────────────────────────────────────────────

    def run_test_case(
        self,
        test_case: dict,
        run_prompt_function,
        extra_criteria: str | None = None,
    ) -> dict:
        """Execute the prompt function and grade its output."""
        output = run_prompt_function(test_case["prompt_inputs"])
        grade = self.grade_output(test_case, output, extra_criteria)
        return {
            "output": output,
            "test_case": test_case,
            "score": grade["score"],
            "reasoning": grade["reasoning"],
        }

    # ── Full evaluation ───────────────────────────────────────────────────────

    def run_evaluation(
        self,
        run_prompt_function,
        dataset_file: str = "dataset.json",
        extra_criteria: str | None = None,
        json_output_file: str = "output.json",
        html_output_file: str = "output.html",
    ) -> list[dict]:
        """Run all test cases concurrently, write JSON + HTML results."""

        with open(dataset_file) as f:
            dataset = json.load(f)

        results: list[dict] = []
        completed = 0
        total = len(dataset)
        last_milestone = 0

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_concurrent_tasks
        ) as executor:
            futures = {
                executor.submit(
                    self.run_test_case, tc, run_prompt_function, extra_criteria
                ): tc
                for tc in dataset
            }
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
                completed += 1
                milestone = (int(completed / total * 100) // 20) * 20
                if milestone > last_milestone:
                    print(f"Graded {completed}/{total} test cases")
                    last_milestone = milestone

        avg = mean(r["score"] for r in results)
        print(f"Average score: {avg:.2f}")

        with open(json_output_file, "w") as f:
            json.dump(results, f, indent=2)

        with open(html_output_file, "w", encoding="utf-8") as f:
            f.write(generate_prompt_evaluation_report(results))

        print(f"Results → {json_output_file}  |  {html_output_file}")
        return results

