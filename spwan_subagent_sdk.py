import asyncio
import os
import sys
from typing import Any
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    tool,
    ToolAnnotations,
    create_sdk_mcp_server,
    ResultMessage,
    AssistantMessage,
    ToolUseBlock,
)
from claude_agent_sdk.types import McpStdioServerConfig

from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    sys.exit("❌  ANTHROPIC_API_KEY not set. Add it to your .env file.")

# ─────────────────────────────────────────────────────────────
# STEP 1 — Define your custom tool with @tool decorator
# ─────────────────────────────────────────────────────────────

@tool(
    "get_product_price",                        # ① unique name Claude uses to call it
    "Get the price of a product by its ID. "    # ② Claude reads this to decide WHEN to call
    "Use when the user asks about product pricing.",
    {"product_id": str, "currency": str},       # ③ input schema → auto-converted to JSON Schema
    annotations=ToolAnnotations(
        readOnlyHint=True                        # ④ no side effects → Claude can batch in parallel
    ),
)
async def get_product_price(args: dict[str, Any]) -> dict[str, Any]:
    # Simulate a DB/API lookup
    prices = {
        "ABC123": {"USD": 29.99, "EUR": 27.50},
        "XYZ789": {"USD": 99.00, "EUR": 91.00},
    }

    product = prices.get(args["product_id"])
    currency = args.get("currency", "USD").upper()

    if not product:
        # ✅ Return is_error=True — agent loop CONTINUES, Claude reacts to failure
        return {
            "content": [{"type": "text",
                          "text": f"Product {args['product_id']} not found."}],
            "is_error": True,   # ← loop keeps running, Claude handles gracefully
        }

    price = product.get(currency, product["USD"])
    return {
        "content": [{"type": "text",
                      "text": f"Product {args['product_id']} costs {currency}{price:.2f}"}]
        # is_error omitted → defaults to False = success
    }


# ─────────────────────────────────────────────────────────────
# STEP 2 — Bundle tool(s) into an in-process MCP server
# ─────────────────────────────────────────────────────────────

product_server = create_sdk_mcp_server(
    name="products",        # server name → becomes part of tool's full name
    version="1.0.0",
    tools=[get_product_price],   # add as many tools as you need here
)

# Third-party GitHub MCP server (stdio-based)
github_server = McpStdioServerConfig(
    type="stdio",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-github"],
    env={"GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_TOKEN", "")},
)

# Tool's fully qualified name = mcp__{server_name}__{tool_name}
#                             = mcp__products__get_product_price


# ─────────────────────────────────────────────────────────────
# STEP 3 — Pass server to query() and list tool in allowedTools
# ─────────────────────────────────────────────────────────────

async def main():
    async for message in query(
        prompt="What is the price of product ABC123 in EUR? "
               "Also check XYZ789. Then try product FAKE999.",

        options=ClaudeAgentOptions(
            model="claude-haiku-4-5",         # ← explicitly set model - default claude-sonnet-4-5 (for Claude Code 2.x)
            mcp_servers={
                "products": product_server,   # ← in-process custom server
                "github": github_server,      # ← third-party GitHub MCP server
            },
            allowed_tools=[
                "mcp__products__get_product_price",    # ← custom tool
                "mcp__github__*",                      # ← all GitHub tools
            ],
        ),
    ):
        # ── See WHEN Claude calls your tool ──────────────────────
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print(f"🔧 Tool called : {block.name}")
                    print(f"   Input       : {block.input}")

        # ── Final answer ──────────────────────────────────────────
        if isinstance(message, ResultMessage) and message.subtype == "success":
            print(f"\n✅ Result : {message.result}")
            print(f"💰 Cost   : ${message.total_cost_usd:.6f}")

asyncio.run(main())