# Exercise 1 — Multi-Tool Agent with Escalation Logic

A production-style agentic banking assistant built with the Anthropic Python SDK. Demonstrates tool design, agentic loops, structured error handling, programmatic business-rule hooks, and multi-concern message decomposition.

---

## Objective

> Practice designing an agentic loop with tool integration, structured error handling, and escalation patterns.

---

## Project Structure

```
exercise-1/
├── main.py             # Entry point — runs a single full demo
├── agent.py            # Agentic loop (stop_reason handling, retry logic)
├── tools.py            # 4 MCP-style tool definitions with descriptions
├── tool_executor.py    # Programmatic hook + tool simulators + dispatcher
├── escalation.py       # Escalation workflow (ticket creation, routing)
├── error_handler.py    # Structured error catalogue (transient/validation/permission)
├── config.py           # Central configuration (thresholds, retries, model)
├── test_scenarios.py   # 7 end-to-end test scenarios
└── prompt              # Original exercise specification
```

---

## Features Implemented

### Step 1 — Tool Design (4 MCP Tools)

Defined in `tools.py` with careful, differentiating descriptions:

| Tool | Direction | Boundary |
|---|---|---|
| `get_account_balance` | READ only — no side effects | Cannot initiate any money movement |
| `process_payment` | DEBIT — money OUT | Amounts ≥ $10,000 auto-escalated |
| `process_refund` | CREDIT — money IN | Amounts ≥ $5,000 auto-escalated |
| `escalate_to_human_agent` | Creates support ticket | Used for permission errors or explicit requests |

> **Key design decision:** `process_payment` and `process_refund` are intentionally similar. Their descriptions explicitly call out *direction of money flow* and include `Do NOT use for...` clauses to prevent Claude selecting the wrong tool.

### Step 2 — Agentic Loop

Implemented in `agent.py`:

```
while True:
    response = client.messages.create(...)
    if stop_reason == "end_turn"  → return final text
    if stop_reason == "tool_use"  → execute tools, append results, loop
    else                          → handle unexpected stop reasons
```

- Maintains full conversation history for context continuity
- Supports multiple parallel tool calls per turn (Claude may batch them)
- Handles `max_tokens`, `stop_sequence`, and other unexpected stop reasons gracefully

### Step 3 — Structured Error Responses

Defined in `error_handler.py`. Every error includes:

```json
{
  "success": false,
  "errorCategory": "transient | validation | permission",
  "errorCode": "MACHINE_READABLE_CODE",
  "isRetryable": true | false,
  "message": "Human-readable description"
}
```

| Category | Behaviour | Examples |
|---|---|---|
| `transient` | Auto-retry up to `MAX_RETRIES` (3) | `DB_TIMEOUT`, `SERVICE_UNAVAILABLE` |
| `validation` | Pass to Claude — explained to user | `INSUFFICIENT_FUNDS`, `ACCOUNT_FROZEN`, `INVALID_ACCOUNT` |
| `permission` | Auto-escalate to human agent | `HIGH_VALUE_TRANSACTION`, `FRAUD_FLAG` |

### Step 4 — Programmatic Escalation Hook

Implemented in `tool_executor.py` (`business_rule_hook`):

```
execute_tool(name, inputs)
  └─► business_rule_hook()        ← runs BEFORE tool simulator
        ├─ payment ≥ $10,000  →  create_escalation_ticket("HIGH_VALUE_PAYMENT")
        ├─ refund  ≥ $5,000   →  create_escalation_ticket("HIGH_VALUE_REFUND")
        └─ no rule triggered  →  None (proceed normally)
```

The hook **short-circuits** execution — the actual tool simulator never runs for flagged requests. An escalation ticket (with team routing and wait time estimate) is returned directly to Claude.

### Step 5 — Multi-Concern Message Decomposition

Claude naturally decomposes requests like:
> *"Check my balance, pay $300 to VENDOR, and refund TXN-20001"*

into three sequential/parallel tool calls, handles each independently (with its own error handling), and synthesises a single unified response.

---

## Quick Start

### Prerequisites

```bash
pip install anthropic python-dotenv
```

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### Run the Demo

```bash
cd exercise-1
python main.py
```

### Run All Test Scenarios

```bash
python test_scenarios.py
```

---

## Test Scenarios

| # | Scenario | Tools Used | Validates |
|---|---|---|---|
| 1 | Balance check + $500 payment | `get_account_balance`, `process_payment` | Multi-tool decomposition & synthesis |
| 2 | Payment of $15,000 | Hook intercept | Escalation hook (high-value payment) |
| 3 | Payment with insufficient funds | `process_payment` | Validation error explained to user |
| 4 | Refund of $6,000 | Hook intercept | Escalation hook (high-value refund) |
| 5 | 3 concerns in one message | All tools | Full decomposition + unified response |
| 6 | Frozen account payment | `get_account_balance`, `process_payment` | Validation error on frozen account |
| 7 | Customer requests human agent | `escalate_to_human_agent` | Manual escalation trigger |

---

## Configuration (`config.py`)

| Setting | Default | Description |
|---|---|---|
| `MAX_TOKENS` | `4096` | Max tokens per API call |
| `MAX_RETRIES` | `3` | Retry limit for transient errors |
| `PAYMENT_ESCALATION_THRESHOLD` | `$10,000` | Payment hook trigger amount |
| `REFUND_ESCALATION_THRESHOLD` | `$5,000` | Refund hook trigger amount |

---

## Claude Features & Documentation References

| Feature | Implementation File | Anthropic Documentation |
|---|---|---|
| Tool use / function calling | `tools.py` | [Tool use overview](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) |
| Agentic loop (`stop_reason`) | `agent.py` | [How tool use works](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/how-tool-use-works) |
| `tool_result` blocks | `agent.py` (messages append) | [Return tool results](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#return-tool-results-to-claude) |
| Structured error responses | `error_handler.py` | [Tool use best practices](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#best-practices-for-tool-definitions) |
| Transient error retry | `agent.py` (`_handle_tool_error`) | [Error handling patterns](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use#error-handling) |
| Programmatic hook / interceptor | `tool_executor.py` (`business_rule_hook`) | [Inject tool results](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use) |
| Escalation workflow | `escalation.py` | [Human-in-the-loop patterns](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#handling-tool-use-in-long-running-agents) |
| Context window management | `agent.py` (`messages` list) | [Context window management](https://docs.anthropic.com/en/docs/build-with-claude/context-windows) |
| Multi-concern decomposition | `test_scenarios.py` (Scenario 5) | [Agentic patterns](https://docs.anthropic.com/en/docs/agents-and-tools/agents-overview) |
| System prompt for tool guidance | `agent.py` (`system=...`) | [System prompts](https://docs.anthropic.com/en/docs/build-with-claude/system-prompts) |

---

## Domains Covered

| Domain | Coverage |
|---|---|
| **Domain 1** — Agentic Architecture & Orchestration | Agentic loop, stop_reason handling, multi-tool parallelism, escalation routing |
| **Domain 2** — Tool Design & MCP Integration | 4 tools with differentiating descriptions, input schemas, boundary conditions |
| **Domain 5** — Context Management & Reliability | Conversation history, retry logic, transient vs permanent error classification |

