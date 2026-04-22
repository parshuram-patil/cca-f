# coordinator.py
# ──────────────────────────────────────────────────────────────────
# Coordinator Agent for the Multi-Agent Research Pipeline
#
# Responsibilities:
#   • Emit multiple Task tool calls in a SINGLE response (parallel execution)
#   • Pass research findings explicitly in each subagent prompt
#   • Handle subagent errors with structured error propagation
#   • Track coverage gaps and annotate the final report
# ──────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import time
import concurrent.futures

import anthropic

from config import MODEL, MAX_TOKENS
from schema import SubagentResult, SynthesisReport
from subagents import (
    run_web_search_subagent,
    run_document_analysis_subagent,
    run_synthesis_subagent,
)


# ── Anthropic client ───────────────────────────────────────────────
client = anthropic.Anthropic()


# ─────────────────────────────────────────────────────────────────
# Tool definitions for the coordinator
# (Each "Task" tool represents delegating work to a subagent)
# Ref: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use
# ─────────────────────────────────────────────────────────────────
COORDINATOR_TOOLS = [
    {
        "name": "web_search_task",
        "description": (
            "Delegate a web research task to the WebSearch subagent. "
            "The subagent will search online sources and return structured findings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Unique identifier for this task"},
                "query": {"type": "string", "description": "The research query to investigate"},
                "simulate_timeout": {
                    "type": "boolean",
                    "description": "If true, simulates a timeout for testing error propagation",
                    "default": False,
                },
            },
            "required": ["agent_id", "query"],
        },
    },
    {
        "name": "document_analysis_task",
        "description": (
            "Delegate a document analysis task to the DocumentAnalysis subagent. "
            "The subagent will analyse internal documents and return structured findings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Unique identifier for this task"},
                "query": {"type": "string", "description": "The research query to investigate"},
            },
            "required": ["agent_id", "query"],
        },
    },
    {
        "name": "synthesis_task",
        "description": (
            "Delegate synthesis to the Synthesis subagent. "
            "Pass ALL prior findings and coverage gaps explicitly in this call."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "findings_json": {
                    "type": "string",
                    "description": "JSON-serialised list of SubagentResult objects",
                },
                "coverage_gaps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of topics not covered due to subagent failures",
                },
            },
            "required": ["query", "findings_json", "coverage_gaps"],
        },
    },
]


# ─────────────────────────────────────────────────────────────────
# Execute a single tool call (dispatches to the right subagent)
# ─────────────────────────────────────────────────────────────────

def _execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Execute a coordinator tool call and return a JSON-serialisable result."""
    if tool_name == "web_search_task":
        result = run_web_search_subagent(
            agent_id=tool_input["agent_id"],
            query=tool_input["query"],
            simulate_timeout=tool_input.get("simulate_timeout", False),
        )
        return result.model_dump()

    elif tool_name == "document_analysis_task":
        result = run_document_analysis_subagent(
            agent_id=tool_input["agent_id"],
            query=tool_input["query"],
        )
        return result.model_dump()

    elif tool_name == "synthesis_task":
        subagent_results_raw = json.loads(tool_input["findings_json"])
        subagent_results = [SubagentResult(**r) for r in subagent_results_raw]
        report = run_synthesis_subagent(
            query=tool_input["query"],
            subagent_results=subagent_results,
            coverage_gaps=tool_input.get("coverage_gaps", []),
        )
        return report.model_dump()

    else:
        return {"error": f"Unknown tool: {tool_name}"}


# ─────────────────────────────────────────────────────────────────
# Parallel task execution
# ─────────────────────────────────────────────────────────────────

def _execute_tool_calls_parallel(
    tool_calls: list[anthropic.types.ToolUseBlock],
) -> tuple[list[dict], float]:
    """
    Execute multiple tool calls IN PARALLEL using a thread pool.
    Returns (results_list, elapsed_seconds).
    Ref: https://docs.anthropic.com/en/docs/agents-and-tools/agents#parallel-tool-use
    """
    start = time.perf_counter()

    def _run(tc: anthropic.types.ToolUseBlock) -> tuple[str, dict]:
        result = _execute_tool(tc.name, tc.input)
        return tc.id, result

    results: dict[str, dict] = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(_run, tc): tc for tc in tool_calls}
        for future in concurrent.futures.as_completed(futures):
            tc_id, result = future.result()
            results[tc_id] = result

    elapsed = time.perf_counter() - start
    # Return in original order
    ordered = [results[tc.id] for tc in tool_calls]
    return ordered, elapsed


# ─────────────────────────────────────────────────────────────────
# Sequential baseline (for latency comparison)
# ─────────────────────────────────────────────────────────────────

def _execute_tool_calls_sequential(
    tool_calls: list[anthropic.types.ToolUseBlock],
) -> tuple[list[dict], float]:
    start = time.perf_counter()
    results = []
    for tc in tool_calls:
        results.append(_execute_tool(tc.name, tc.input))
    elapsed = time.perf_counter() - start
    return results, elapsed


# ─────────────────────────────────────────────────────────────────
# Main Coordinator Agent
# ─────────────────────────────────────────────────────────────────

class CoordinatorAgent:
    """
    Orchestrates a multi-agent research pipeline.

    Architecture (Anthropic agentic patterns):
      Coordinator → [WebSearch subagent, DocumentAnalysis subagent]  (parallel)
                  → Synthesis subagent  (sequential, needs prior results)
    """

    def __init__(self, topic: str, simulate_timeout: bool = True):
        self.topic = topic
        self.simulate_timeout = simulate_timeout
        self.subagent_results: list[SubagentResult] = []
        self.coverage_gaps: list[str] = []
        self.latency_log: dict = {}

    # ── Agentic loop ──────────────────────────────────────────────

    def run(self) -> SynthesisReport:
        print(f"\n{'='*60}")
        print(f"Coordinator started for topic: {self.topic}")
        print(f"{'='*60}\n")

        # ── Phase 1: Coordinator plans and emits parallel Tasks ───
        phase1_report = self._phase1_parallel_research()

        # ── Phase 2: Synthesis ────────────────────────────────────
        report = self._phase2_synthesis()

        return report

    # ── Phase 1: Parallel subagent dispatch ───────────────────────

    def _phase1_parallel_research(self):
        """
        Ask the coordinator LLM to plan the research tasks.
        The coordinator emits MULTIPLE tool calls in a single response,
        which we execute in parallel.
        """
        system = (
            "You are a research coordinator managing a multi-agent pipeline. "
            "Your job is to delegate research tasks to specialised subagents. "
            "You MUST call BOTH web_search_task AND document_analysis_task in a SINGLE response "
            "so they can run in parallel. "
            f"Set simulate_timeout=true for web_search_task to test error propagation."
        )

        user_msg = (
            f"Research topic: {self.topic}\n\n"
            "Please delegate research tasks to both available subagents simultaneously. "
            "Use agent_id 'ws-001' for web search and 'da-001' for document analysis."
        )

        messages = [{"role": "user", "content": user_msg}]

        print("[Coordinator] Requesting parallel task delegation from LLM...")
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            tools=COORDINATOR_TOOLS[:2],  # Only Task tools (no synthesis yet)
            tool_choice={"type": "any"},
            messages=messages,
        )

        tool_calls = [b for b in response.content if b.type == "tool_use"]
        print(f"[Coordinator] LLM emitted {len(tool_calls)} tool call(s) in one response.")

        if not tool_calls:
            print("[Coordinator] No tool calls emitted. Using default parallel dispatch.")
            tool_calls = self._default_tool_calls()

        # ── Execute in PARALLEL and measure latency ───────────────
        print("[Coordinator] Executing subagents in PARALLEL...")
        parallel_results, parallel_elapsed = _execute_tool_calls_parallel(tool_calls)
        self.latency_log["parallel_secs"] = round(parallel_elapsed, 3)
        print(f"[Coordinator] Parallel execution completed in {parallel_elapsed:.2f}s")

        # ── Also measure sequential baseline ─────────────────────
        print("[Coordinator] Re-running subagents SEQUENTIALLY for latency comparison...")
        _, sequential_elapsed = _execute_tool_calls_sequential(tool_calls)
        self.latency_log["sequential_secs"] = round(sequential_elapsed, 3)
        improvement = sequential_elapsed - parallel_elapsed
        self.latency_log["improvement_secs"] = round(improvement, 3)
        self.latency_log["speedup_factor"] = round(sequential_elapsed / max(parallel_elapsed, 0.001), 2)
        print(f"[Coordinator] Sequential baseline: {sequential_elapsed:.2f}s | "
              f"Improvement: {improvement:.2f}s ({self.latency_log['speedup_factor']}x speedup)\n")

        # ── Process results & handle errors ───────────────────────
        for tc, raw_result in zip(tool_calls, parallel_results):
            result = SubagentResult(**raw_result)
            self.subagent_results.append(result)

            if not result.success and result.error:
                err = result.error
                print(f"[Coordinator] ⚠  Subagent '{result.agent_id}' failed:")
                print(f"             Failure type : {err.failure_type}")
                print(f"             Query        : {err.attempted_query}")
                print(f"             Partial items: {len(err.partial_results)}")
                print(f"             Message      : {err.error_message}")
                gap = (
                    f"Web search incomplete for '{err.attempted_query}' "
                    f"({err.failure_type}): {len(err.partial_results)} partial results only"
                )
                self.coverage_gaps.append(gap)
            else:
                print(f"[Coordinator] ✓  Subagent '{result.agent_id}' returned "
                      f"{len(result.findings)} finding(s).")

    # ── Phase 2: Synthesis ────────────────────────────────────────

    def _phase2_synthesis(self) -> SynthesisReport:
        """Pass all findings explicitly to the synthesis subagent."""
        findings_json = json.dumps(
            [r.model_dump() for r in self.subagent_results], indent=2
        )

        print("\n[Coordinator] Delegating to Synthesis subagent...")
        synthesis_input = {
            "query": self.topic,
            "findings_json": findings_json,
            "coverage_gaps": self.coverage_gaps,
        }
        raw = _execute_tool("synthesis_task", synthesis_input)
        report = SynthesisReport(**raw)
        print("[Coordinator] Synthesis complete.\n")
        return report

    # ── Fallback tool calls (if LLM emits none) ───────────────────

    def _default_tool_calls(self) -> list:
        """Create default tool call objects when LLM doesn't emit them."""

        class _FakeTool:
            def __init__(self, id_, name, input_):
                self.id = id_
                self.name = name
                self.input = input_
                self.type = "tool_use"

        return [
            _FakeTool(
                "tc-ws-001",
                "web_search_task",
                {"agent_id": "ws-001", "query": self.topic, "simulate_timeout": self.simulate_timeout},
            ),
            _FakeTool(
                "tc-da-001",
                "document_analysis_task",
                {"agent_id": "da-001", "query": self.topic},
            ),
        ]



