"""
backend/mcp/mcp_client.py

ScholarForge — MCP Client

A thin synchronous wrapper around the real MCP protocol client (Anthropic's
`mcp` SDK), so the LangGraph pipeline's (synchronous) node functions can
call tools exposed by mcp_server.py without needing to be rewritten as
async themselves.

Under the hood this spawns mcp_server.py as a subprocess and talks to it
over stdio using the actual MCP wire protocol (JSON-RPC) — the same
mechanism a real MCP host like Claude Desktop would use.
"""

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_SERVER_PATH = os.path.join(os.path.dirname(__file__), "mcp_server.py")

# Tool names whose contract is "always returns a list". Used to work around
# a known FastMCP bug (github.com/jlowin/fastmcp #1064): when a tool's
# return value is annotated as `list` but the list has exactly one item,
# FastMCP's serialization sometimes unwraps it down to the bare item
# instead of a one-element list. We detect and correct that here so
# callers can always rely on getting a list back, regardless of result
# count.
_LIST_RETURNING_TOOLS = {"find_hf_models", "search_arxiv"}


def _extract_result(call_tool_result) -> object:
    """
    MCP tool results come back as a list of content blocks. FastMCP
    auto-serializes Python return values (dict/list/str) into a JSON text
    block, so we parse that back into a Python object here.
    """
    if not call_tool_result.content:
        return None
    block = call_tool_result.content[0]
    text = getattr(block, "text", None)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text  # plain string return (e.g. push_to_github's URL)


async def _call_tools_async(calls: list) -> list:
    """
    Opens a single MCP session (one server subprocess) and calls each
    (tool_name, arguments_dict) pair in `calls`, in order. Reusing one
    session for multiple calls avoids paying subprocess-startup cost per
    tool call.
    """
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[_SERVER_PATH],
    )

    results = []
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for tool_name, arguments in calls:
                raw_result = await session.call_tool(tool_name, arguments=arguments)
                extracted = _extract_result(raw_result)
                if tool_name in _LIST_RETURNING_TOOLS and isinstance(extracted, dict):
                    # FastMCP unwrapped a single-item list down to the bare
                    # dict (see _LIST_RETURNING_TOOLS comment above) — put
                    # it back in a list so callers get a consistent shape.
                    extracted = [extracted]
                results.append(extracted)
    return results


def call_mcp_tools(calls: list) -> list:
    """
    Synchronous entry point. `calls` is a list of (tool_name, arguments_dict)
    tuples. Returns a list of results in the same order.

    Example:
        call_mcp_tools([
            ("push_to_github", {"repo_name": "foo", "files": {...}, "description": "..."}),
            ("find_hf_models", {"task": "machine learning", "paper_title": "...", "top_k": 5}),
        ])
    """
    return asyncio.run(_call_tools_async(calls))


if __name__ == "__main__":
    # Smoke test: list available tools without calling any of them
    # (calling push_to_github for real requires a valid GITHUB_TOKEN).
    async def _list_tools():
        server_params = StdioServerParameters(command=sys.executable, args=[_SERVER_PATH])
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                print("Tools exposed by the MCP server:")
                for t in tools.tools:
                    print(f"  - {t.name}: {t.description.strip().splitlines()[0]}")

    asyncio.run(_list_tools())
