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
                results.append(_extract_result(raw_result))
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
