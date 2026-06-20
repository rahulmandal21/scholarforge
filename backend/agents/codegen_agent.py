"""
backend/agents/codegen_agent.py

ScholarForge — Phase 6: Code Generation Agent

Takes one ML component (from decompose_agent) plus a list of similar prior
implementations (from chroma_store) and asks Groq's Llama model to generate
production-ready, object-oriented Python code for it.

The generated code includes: a class definition, docstrings, type hints,
and a usage example under `if __name__ == "__main__":`.
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def _format_similar_implementations(similar_implementations: list) -> str:
    if not similar_implementations:
        return "None available."

    blocks = []
    for i, impl in enumerate(similar_implementations[:3], start=1):
        blocks.append(
            f"--- Reference Example {i}: {impl.get('component_name', 'unknown')} ---\n"
            f"Description: {impl.get('description', '')}\n"
            f"Code:\n{impl.get('code', '')}\n"
        )
    return "\n".join(blocks)


def _build_prompt(component: dict, similar_implementations: list, feedback: str = None) -> str:
    name = component.get("component_name", "component")
    description = component.get("description", "")
    equations = component.get("equations", [])
    hints = component.get("implementation_hints", [])

    equations_text = "\n".join(f"- {eq}" for eq in equations) if equations else "None given."
    hints_text = "\n".join(f"- {h}" for h in hints) if hints else "None given."
    references_text = _format_similar_implementations(similar_implementations)
    feedback_text = (
        f"\nFEEDBACK FROM A PREVIOUS ATTEMPT (address this in your new version):\n{feedback}\n"
        if feedback else ""
    )

    return (
        "You are an expert ML engineer writing production-quality Python code.\n\n"
        f"COMPONENT TO IMPLEMENT: {name}\n\n"
        f"DESCRIPTION:\n{description}\n\n"
        f"RELEVANT EQUATIONS:\n{equations_text}\n\n"
        f"IMPLEMENTATION HINTS:\n{hints_text}\n\n"
        f"REFERENCE IMPLEMENTATIONS (for style and pattern guidance, not to copy verbatim):\n"
        f"{references_text}\n"
        f"{feedback_text}\n"
        "Write a complete, production-ready Python implementation of this component. Requirements:\n"
        "- Use PyTorch where appropriate (import torch, torch.nn as nn)\n"
        "- Wrap the logic in a well-named class with a clear docstring\n"
        "- Add type hints to all method signatures\n"
        "- Add a brief docstring to every method explaining what it does\n"
        "- Include a small usage example under `if __name__ == \"__main__\":` that demonstrates "
        "the class working on dummy/sample data\n"
        "- Do NOT include any explanation, commentary, or markdown formatting — respond with "
        "ONLY the raw Python code, starting directly with the imports."
    )


def _call_groq(prompt: str) -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a senior ML engineer. You respond with only raw Python code, never markdown or commentary.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return completion.choices[0].message.content


def _clean_code_output(raw_text: str) -> str:
    """Strip markdown code fences if the model added them despite instructions."""
    text = raw_text.strip()

    fence_match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("python"):
            text = text[6:].strip()

    return text


def generate_code(component: dict, similar_implementations: list, feedback: str = None) -> str:
    """
    Generate production-ready Python code for a single ML component.

    `feedback` is optional text from a previous evaluation attempt (see
    eval_agent.py) — when provided, it's included in the prompt so the
    model can correct course on a retry.

    Returns the generated code as a string. On failure, returns a string
    starting with "# ERROR:" so callers can detect failure without needing
    a separate exception-handling path.
    """
    if not os.getenv("GROQ_API_KEY"):
        return "# ERROR: GROQ_API_KEY not found in environment."

    prompt = _build_prompt(component, similar_implementations, feedback=feedback)

    try:
        raw_response = _call_groq(prompt)
    except Exception as e:
        return f"# ERROR: Groq API call failed: {e}"

    return _clean_code_output(raw_response)


if __name__ == "__main__":
    import sys
    import json

    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "sample_paper.pdf"

    # Chain Phases 2 -> 3 -> 5 -> 6 so this can be tested standalone.
    from parser_agent import parse_paper
    from decompose_agent import decompose_paper
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "chroma_store", os.path.join(os.path.dirname(__file__), "..", "vector_store", "chroma_store.py")
    )
    chroma_store = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(chroma_store)

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

    store = chroma_store.ScholarForgeVectorStore()
    if store.collection.count() == 0:
        chroma_store.seed_sample_data(store)

    # Generate code for just the first component as a demo.
    target_component = components[0]
    print(f"\nGenerating code for: {target_component['component_name']}\n")

    similar = store.search_similar(target_component["description"], top_k=3)
    code = generate_code(target_component, similar)

    print(code)
