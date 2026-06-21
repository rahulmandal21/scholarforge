"""
backend/graph/langgraph_pipeline.py

ScholarForge — Phase 9: LangGraph Pipeline

Wires every agent built in Phases 2-8 into a single LangGraph StateGraph:

    PDF Upload
        |
    parse_node       (Grobid)
        |
    decompose_node   (Groq -> ML components)
        |
    kg_node          (Groq + NetworkX -> dependency graph)
        |
    retrieve_node    (ChromaDB -> similar prior implementations)
        |
    codegen_eval_node (Groq -> code, then AST-score + retry per component)
        |
    mcp_push_node    (GitHub push + HuggingFace model search)
        |
    DONE -> final result dict

Design note: the original spec calls for a graph-level conditional edge
that loops back from "eval" to "codegen" when a score is too low. Since
this pipeline processes multiple components per paper (not just one),
that retry logic is handled *inside* codegen_eval_node by reusing
eval_agent.evaluate_and_retry() per component, rather than as a
graph-level loop. This keeps the graph simple while still giving every
component its own retry-on-low-score behavior.
"""

import os
import re
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypedDict

from langgraph.graph import StateGraph, START, END

# Make sibling folders importable regardless of where this script is run from.
_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..")
for _subdir in ("agents", "mcp_tools", "utils"):
    sys.path.append(os.path.join(_BACKEND_DIR, _subdir))

from parser_agent import parse_paper                # noqa: E402
from decompose_agent import decompose_paper          # noqa: E402
from kg_agent import build_knowledge_graph            # noqa: E402
from codegen_agent import generate_code               # noqa: E402
from eval_agent import evaluate_and_retry              # noqa: E402
from mcp_client import call_mcp_tools                    # noqa: E402

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "chroma_store", os.path.join(_BACKEND_DIR, "vector_store", "chroma_store.py")
)
chroma_store = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chroma_store)

_vector_store = None


def _get_vector_store():
    """Lazily create (and reuse) a single vector store instance per process."""
    global _vector_store
    if _vector_store is None:
        _vector_store = chroma_store.ScholarForgeVectorStore()
        if _vector_store.collection.count() == 0:
            chroma_store.seed_sample_data(_vector_store)
    return _vector_store


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] if slug else f"scholarforge-{uuid.uuid4().hex[:8]}"


def _clean_title(title: str) -> str:
    """
    Grobid sometimes prepends copyright/permission boilerplate before the
    real title (common with Google papers, e.g. "Provided proper
    attribution is provided... Attention Is All You Need"). When a title
    is unusually long and contains a period, the real title is often the
    text after the last period. This is a heuristic, not a guarantee.
    """
    title = (title or "").strip()
    if len(title) > 120 and "." in title:
        candidate = title.rsplit(".", 1)[-1].strip()
        if candidate:
            return candidate
    return title


class PipelineState(TypedDict):
    pdf_path: str
    github_token: str
    parsed_paper: dict
    components: list
    knowledge_graph: dict
    similar_implementations: dict
    generated_codes: dict
    eval_results: dict
    github_url: str
    hf_models: list
    arxiv_papers: list
    status_message: str


def parse_node(state: PipelineState) -> dict:
    parsed = parse_paper(state["pdf_path"])
    if parsed.get("error"):
        return {"parsed_paper": parsed, "status_message": f"Parse error: {parsed['error']}"}
    return {"parsed_paper": parsed, "status_message": "Parsing complete."}


def decompose_node(state: PipelineState) -> dict:
    parsed = state.get("parsed_paper", {})
    if parsed.get("error"):
        return {"components": [], "status_message": "Skipped decomposition due to parse error."}

    components = decompose_paper(parsed)
    if components and "error" in components[0]:
        return {"components": [], "status_message": f"Decompose error: {components[0]['error']}"}
    return {"components": components, "status_message": f"Decomposed into {len(components)} components."}


def kg_node(state: PipelineState) -> dict:
    components = state.get("components", [])
    if not components:
        return {"knowledge_graph": {"nodes": [], "edges": []}, "status_message": "Skipped KG (no components)."}

    graph_json = build_knowledge_graph(components)
    return {"knowledge_graph": graph_json, "status_message": "Knowledge graph built."}


def retrieve_node(state: PipelineState) -> dict:
    components = state.get("components", [])
    if not components:
        return {"similar_implementations": {}, "status_message": "Skipped retrieval (no components)."}

    store = _get_vector_store()
    similar_map = {}
    for comp in components:
        name = comp.get("component_name", "unknown")
        similar_map[name] = store.search_similar(
            comp.get("description", ""), top_k=3, component_type=name
        )

    return {"similar_implementations": similar_map, "status_message": "Retrieved similar implementations."}


def _process_one_component(comp: dict, similar_map: dict) -> tuple:
    """Generate + evaluate (with retries) a single component. Runs in a worker thread."""
    name = comp.get("component_name", "unknown")
    similar = similar_map.get(name, [])
    reference_code = similar[0]["code"] if similar else ""

    first_attempt = generate_code(comp, similar)

    if reference_code:
        result = evaluate_and_retry(
            component=comp,
            generated_code=first_attempt,
            reference_code=reference_code,
            similar_implementations=similar,
            # Reduced from 3 to 2: in practice, a 3rd retry rarely improved the
            # score (see Phase 7/9 testing), since most low scores stem from a
            # poor reference match in the vector store rather than fixable
            # generation quality. Cutting this saves real wall-clock time.
            max_retries=2,
        )
    else:
        result = {
            "final_code": first_attempt,
            "final_score": None,
            "attempts": 1,
            "passed": None,
            "history": [],
        }

    return name, result


def codegen_eval_node(state: PipelineState) -> dict:
    components = state.get("components", [])
    similar_map = state.get("similar_implementations", {})

    generated_codes = {}
    eval_results = {}

    # Components are independent of each other, so generate + evaluate them
    # concurrently instead of one at a time. This is the single biggest lever
    # on total pipeline time: 5 components run in parallel instead of in
    # sequence. Capped at 3 concurrent workers (rather than unlimited) as a
    # deliberate tradeoff — Groq's free tier has a requests-per-minute limit,
    # and firing all 5+ components' worth of calls at once raises the odds of
    # hitting a 429 rate-limit error (which the pipeline already handles
    # gracefully by returning an error string, but it's better avoided).
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(_process_one_component, comp, similar_map)
            for comp in components
        ]
        for future in as_completed(futures):
            name, result = future.result()
            generated_codes[name] = result["final_code"]
            eval_results[name] = result

    return {
        "generated_codes": generated_codes,
        "eval_results": eval_results,
        "status_message": f"Generated and evaluated {len(generated_codes)} components.",
    }


def mcp_push_node(state: PipelineState) -> dict:
    generated_codes = state.get("generated_codes", {})
    parsed_paper = state.get("parsed_paper", {})
    raw_title = parsed_paper.get("title", "") or "scholarforge-generated-project"
    title = _clean_title(raw_title)
    github_token = state.get("github_token", "")

    if not generated_codes:
        return {
            "github_url": "",
            "hf_models": [],
            "arxiv_papers": [],
            "status_message": "Skipped MCP push (no generated code).",
        }

    # HuggingFace and Arxiv searches need no per-user credential, so they
    # always run. GitHub push is conditional on the requesting user having
    # supplied their own token — without one, we skip the push entirely
    # rather than falling back to the server operator's own GitHub account.
    # Without this, every visitor's generated code would land in *your*
    # GitHub, not theirs, the moment this is deployed for others to use.
    #
    # `calls` is built as a list of (tool_name, arguments) tuples and each
    # entry's position is tracked by name in `call_names` below, rather than
    # relying on fixed indices — this keeps the result-unpacking correct
    # regardless of which optional calls (currently just GitHub) end up
    # included.
    calls = []
    call_names = []

    if github_token:
        files = {f"{name}.py": code for name, code in generated_codes.items()}
        # Append a short unique suffix so re-running the pipeline on the same
        # paper doesn't collide with a previously created repo of the same name.
        repo_name = f"{_slugify(title)}-{uuid.uuid4().hex[:6]}"
        calls.append((
            "push_to_github",
            {
                "repo_name": repo_name,
                "files": files,
                "description": f"Auto-generated implementation of: {title}"[:350],
                "token": github_token,
            },
        ))
        call_names.append("github")

    calls.append(("find_hf_models", {"task": "machine learning", "paper_title": title, "top_k": 5}))
    call_names.append("hf_models")

    calls.append(("search_arxiv", {"query": title, "max_results": 5}))
    call_names.append("arxiv_papers")

    # All calls go through the real MCP protocol (mcp_client.py spawns
    # mcp_server.py as a subprocess and talks JSON-RPC over stdio) rather
    # than calling github_mcp/hf_mcp/arxiv_mcp's functions directly in-process.
    results = call_mcp_tools(calls)
    by_name = dict(zip(call_names, results))

    github_url = by_name.get("github", "")
    hf_models = by_name.get("hf_models", [])
    arxiv_papers = by_name.get("arxiv_papers", [])

    found_parts = []
    if hf_models:
        found_parts.append("related HuggingFace models")
    if arxiv_papers:
        found_parts.append("related Arxiv papers")
    found_summary = " and ".join(found_parts) if found_parts else "no related resources"

    if github_token:
        message = f"Pushed to GitHub and found {found_summary}."
    else:
        message = f"Found {found_summary}. (GitHub push skipped — no token provided.)"

    return {
        "github_url": github_url,
        "hf_models": hf_models,
        "arxiv_papers": arxiv_papers,
        "status_message": message,
    }
_compiled_graph = None


def build_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("parse_node", parse_node)
    graph.add_node("decompose_node", decompose_node)
    graph.add_node("kg_node", kg_node)
    graph.add_node("retrieve_node", retrieve_node)
    graph.add_node("codegen_eval_node", codegen_eval_node)
    graph.add_node("mcp_push_node", mcp_push_node)

    graph.add_edge(START, "parse_node")
    graph.add_edge("parse_node", "decompose_node")
    graph.add_edge("decompose_node", "kg_node")
    graph.add_edge("kg_node", "retrieve_node")
    graph.add_edge("retrieve_node", "codegen_eval_node")
    graph.add_edge("codegen_eval_node", "mcp_push_node")
    graph.add_edge("mcp_push_node", END)

    return graph.compile()


def run_pipeline(pdf_path: str, github_token: str = "") -> dict:
    """Run the full ScholarForge pipeline on a PDF and return the final result dict."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()

    initial_state: PipelineState = {
        "pdf_path": pdf_path,
        "github_token": github_token,
        "parsed_paper": {},
        "components": [],
        "knowledge_graph": {},
        "similar_implementations": {},
        "generated_codes": {},
        "eval_results": {},
        "github_url": "",
        "hf_models": [],
        "status_message": "Starting pipeline...",
    }

    return _compiled_graph.invoke(initial_state)


NODE_ORDER = [
    "parse_node",
    "decompose_node",
    "kg_node",
    "retrieve_node",
    "codegen_eval_node",
    "mcp_push_node",
]


def run_pipeline_with_progress(pdf_path: str, github_token: str = "", progress_callback=None) -> dict:
    """
    Same as run_pipeline(), but streams a progress update after each node
    finishes — used by the FastAPI backend (Phase 10) to report real
    stage/percentage instead of guessing.

    progress_callback(node_name: str, step: int, total: int, message: str)
    is called once per node, in execution order.
    """
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()

    state: PipelineState = {
        "pdf_path": pdf_path,
        "github_token": github_token,
        "parsed_paper": {},
        "components": [],
        "knowledge_graph": {},
        "similar_implementations": {},
        "generated_codes": {},
        "eval_results": {},
        "github_url": "",
        "hf_models": [],
        "status_message": "Starting pipeline...",
    }

    total = len(NODE_ORDER)
    step = 0
    for update in _compiled_graph.stream(state):
        for node_name, partial in update.items():
            state.update(partial)
            step += 1
            if progress_callback:
                progress_callback(node_name, step, total, partial.get("status_message", ""))

    return state


if __name__ == "__main__":
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "sample_paper.pdf"

    print(f"Running full ScholarForge pipeline on '{pdf_path}'...\n")
    result = run_pipeline(pdf_path)

    print(f"Final status: {result.get('status_message')}\n")
    print(f"Components: {[c.get('component_name') for c in result.get('components', [])]}")
    print(f"Knowledge graph: {len(result.get('knowledge_graph', {}).get('nodes', []))} nodes, "
          f"{len(result.get('knowledge_graph', {}).get('edges', []))} edges")
    print(f"GitHub URL: {result.get('github_url')}")
    print(f"HuggingFace models found: {len(result.get('hf_models', []))}\n")

    print("Eval results per component:")
    for name, res in result.get("eval_results", {}).items():
        print(f"  - {name}: passed={res.get('passed')}, score={res.get('final_score')}, attempts={res.get('attempts')}")
