"""
backend/agents/kg_agent.py

ScholarForge — Phase 4: Knowledge Graph Agent

Takes the list of components produced by decompose_agent.decompose_paper()
and builds a directed dependency graph between them (e.g. "training_loop"
depends_on "model_architecture" and "loss_function"). Uses Groq's Llama
model to infer the relationships, then represents them with NetworkX.

Returns a JSON-serializable dict:
    {
        "nodes": [{"id": str, "label": str, "description": str}, ...],
        "edges": [{"source": str, "target": str, "relationship": str}, ...]
    }
This is what gets sent to the React frontend for graph visualization.
"""

import os
import json

import networkx as nx
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def _build_nodes(components: list) -> list:
    """Turn each component dict into a graph node."""
    nodes = []
    for comp in components:
        if "error" in comp:
            continue
        nodes.append({
            "id": comp.get("component_name", "unknown"),
            "label": comp.get("component_name", "unknown").replace("_", " ").title(),
            "description": comp.get("description", ""),
        })
    return nodes


def _build_prompt(nodes: list) -> str:
    node_summaries = "\n".join(
        f'- "{n["id"]}": {n["description"]}' for n in nodes
    )
    valid_ids = ", ".join(f'"{n["id"]}"' for n in nodes)
    return (
        "You are analyzing the implementation components of an ML research paper. "
        "Below is a list of components with short descriptions.\n\n"
        f"{node_summaries}\n\n"
        "Identify the dependency relationships between these components — i.e. which "
        "component depends on, uses, or produces output for another.\n\n"
        "Respond with ONLY a JSON array (no markdown, no commentary) where each item has "
        "exactly these keys:\n"
        '  "source": the id of the component that depends on / uses the other (must be one of: '
        f"{valid_ids})\n"
        '  "target": the id of the component being depended on / used (must be one of: '
        f"{valid_ids})\n"
        '  "relationship": a short label, one of: "depends_on", "uses", "outputs_to", "evaluates"\n\n'
        "Only include edges that make real sense for this paper. Do not include self-loops "
        "(source equal to target). Respond with ONLY the JSON array."
    )


def _call_groq(prompt: str) -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You always respond with valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return completion.choices[0].message.content


def _parse_json_array(raw_text: str) -> list:
    """Defensively parse a JSON array out of the model's raw text response."""
    text = raw_text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            for value in parsed.values():
                if isinstance(value, list):
                    return value
            return [parsed]
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse a JSON array from model output:\n{raw_text[:500]}")


def build_knowledge_graph(components: list) -> dict:
    """
    Build a dependency graph from a list of ML components.

    Returns {"nodes": [...], "edges": [...], "error": str | None}
    """
    nodes = _build_nodes(components)

    if not nodes:
        return {"nodes": [], "edges": [], "error": "No valid components to build a graph from."}

    if len(nodes) == 1:
        # Nothing to connect — return a single-node graph with no edges.
        return {"nodes": nodes, "edges": [], "error": None}

    if not os.getenv("GROQ_API_KEY"):
        return {"nodes": nodes, "edges": [], "error": "GROQ_API_KEY not found in environment."}

    prompt = _build_prompt(nodes)

    try:
        raw_response = _call_groq(prompt)
    except Exception as e:
        return {"nodes": nodes, "edges": [], "error": f"Groq API call failed: {e}"}

    try:
        raw_edges = _parse_json_array(raw_response)
    except ValueError as e:
        return {"nodes": nodes, "edges": [], "error": str(e)}

    valid_ids = {n["id"] for n in nodes}

    graph = nx.DiGraph()
    for n in nodes:
        graph.add_node(n["id"], label=n["label"], description=n["description"])

    edges = []
    for e in raw_edges:
        if not isinstance(e, dict):
            continue
        source = e.get("source")
        target = e.get("target")
        relationship = e.get("relationship", "depends_on")

        if source not in valid_ids or target not in valid_ids or source == target:
            continue
        if graph.has_edge(source, target):
            continue  # avoid duplicates

        graph.add_edge(source, target, relationship=relationship)
        edges.append({"source": source, "target": target, "relationship": relationship})

    return {"nodes": nodes, "edges": edges, "error": None}


if __name__ == "__main__":
    import sys

    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "sample_paper.pdf"

    # Chain Phases 2 -> 3 -> 4 so this can be tested standalone.
    from parser_agent import parse_paper
    from decompose_agent import decompose_paper

    print(f"Parsing {pdf_path} with Grobid...")
    parsed = parse_paper(pdf_path)
    if parsed.get("error"):
        print(json.dumps(parsed, indent=2))
        sys.exit(1)

    print("Decomposing into ML components with Groq...")
    components = decompose_paper(parsed)
    if components and "error" in components[0]:
        print(json.dumps(components, indent=2))
        sys.exit(1)

    print("Building knowledge graph with Groq + NetworkX...")
    graph_json = build_knowledge_graph(components)
    print(json.dumps(graph_json, indent=2))
