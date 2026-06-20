"""
backend/mcp/mcp_server.py

ScholarForge — MCP Server (real Model Context Protocol)

Exposes three tools over the actual MCP protocol (stdio transport), using
Anthropic's official `mcp` Python SDK:
    - push_to_github : create a GitHub repo and push generated code
    - find_hf_models  : search HuggingFace Hub for relevant pretrained models
    - search_arxiv    : search arXiv for related papers

This replaces the earlier "MCP" naming used in Phase 8 (arxiv_mcp.py,
github_mcp.py, hf_mcp.py), which were just plain Python functions despite
the filename — not actually using the MCP protocol. This file wraps that
same underlying logic (reused, not rewritten) and exposes it through a real
FastMCP server, so a real MCP client (this pipeline's mcp_client.py, or any
other MCP-compatible client like Claude Desktop) can discover and call
these tools in a standardized way.

Run standalone for testing:
    python mcp_server.py
(it will wait on stdio for a client — see mcp_client.py to actually call it)
"""

import os
import sys

sys.path.append(os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP

# Reuse the existing, already-tested logic from Phase 8 rather than
# duplicating it — this file is purely a protocol wrapper around it.
from github_mcp import push_generated_code as _push_generated_code
from hf_mcp import find_relevant_models as _find_relevant_models
from arxiv_mcp import fetch_related_papers as _fetch_related_papers

mcp = FastMCP("scholarforge-tools")


@mcp.tool()
def push_to_github(repo_name: str, files: dict, description: str, token: str = "") -> str:
    """
    Create a new public GitHub repository, push the given generated code
    files to it along with a README, and return the repo URL.

    files: a dict mapping filename -> file content (e.g. {"model.py": "..."})
    token: the requesting user's own GitHub Personal Access Token. Required —
        without it, the caller should skip calling this tool entirely rather
        than letting it fall back to the server's own credentials.
    """
    return _push_generated_code(repo_name, files, description, token=token or None)


@mcp.tool()
def find_hf_models(task: str, paper_title: str = "", top_k: int = 5) -> list:
    """
    Search HuggingFace Hub for pretrained models relevant to a given ML
    task and/or paper title. Returns a list of model info dicts.
    """
    return _find_relevant_models(task, paper_title, top_k)


@mcp.tool()
def search_arxiv(query: str, max_results: int = 5) -> list:
    """
    Search arXiv for papers related to a query. Returns a list of paper
    info dicts (title, authors, abstract, pdf_url, published_date).
    """
    return _fetch_related_papers(query, max_results)


if __name__ == "__main__":
    mcp.run(transport="stdio")
