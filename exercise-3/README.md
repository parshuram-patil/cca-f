# Exercise 3 – Multi-Agent Research Pipeline

## Overview

A production-grade multi-agent research pipeline that demonstrates all five exercise steps using Anthropic's Claude API.

```
User Query
    │
    ▼
┌──────────────────────────────────────────────────────┐
│              COORDINATOR AGENT                        │
│  (claude-opus-4-5, tool_use, parallel Task dispatch) │
└────────┬───────────────────────┬─────────────────────┘
         │  (parallel)           │  (parallel)
         ▼                       ▼
┌─────────────────┐   ┌──────────────────────┐
│  WebSearch      │   │  DocumentAnalysis     │
│  Subagent       │   │  Subagent             │
│  (ws-001)       │   │  (da-001)             │
└────────┬────────┘   └──────────┬────────────┘
         │  findings / error     │  findings
         └──────────┬────────────┘
                    ▼
         ┌─────────────────────┐
         │  SYNTHESIS Subagent │
         │  (full provenance)  │
         └─────────────────────┘
                    │
                    ▼
          SynthesisReport (JSON)
```

## Files

| File | Purpose |
|---|---|
| `config.py` | Central config (model, timeouts, paths) |
| `schema.py` | Pydantic schemas: `Finding`, `SubagentResult`, `SubagentError`, `SynthesisReport` |
| `subagents.py` | Three subagent implementations: WebSearch, DocumentAnalysis, Synthesis |
| `coordinator.py` | Coordinator agent with parallel dispatch, error handling, coverage-gap tracking |
| `main.py` | Entry point – runs pipeline and pretty-prints report |
| `test_pipeline.py` | Four automated test scenarios |

## Running

```bash
cd exercise-3
python main.py           # Full pipeline with simulated timeout
python test_pipeline.py  # All test scenarios
```

## Claude Features Used

| Feature | Purpose | Documentation |
|---|---|---|
| **Tool Use** | Coordinator delegates to subagents via named tools | [Tool use](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use) |
| **Parallel Tool Calls** | Coordinator emits `web_search_task` + `document_analysis_task` in a single response | [Parallel tool use](https://docs.anthropic.com/en/docs/agents-and-tools/agents#parallel-tool-use) |
| **Agentic Orchestrator–Subagent Pattern** | Coordinator holds the plan; subagents are stateless workers | [Building effective agents](https://docs.anthropic.com/en/docs/agents-and-tools/agents) |
| **Explicit Context Passing** | Each subagent receives its findings directly in its prompt, no automatic context inheritance | [Context management](https://docs.anthropic.com/en/docs/agents-and-tools/agents#context-management) |
| **Structured JSON Output** | `Finding`, `SubagentResult`, `SynthesisReport` enforce provenance fields | [Structured outputs](https://docs.anthropic.com/en/docs/test-and-evaluate/strengthen-guardrails/increase-consistency) |
| **Error Propagation** | `SubagentError` carries `failure_type`, `attempted_query`, `partial_results` to coordinator | [Error handling in agents](https://docs.anthropic.com/en/docs/agents-and-tools/agents#error-handling) |
| **Contested vs Established Findings** | Synthesis subagent preserves both conflicting statistics with attribution | [Faithfulness / attribution](https://docs.anthropic.com/en/docs/test-and-evaluate/strengthen-guardrails/reduce-hallucinations) |

