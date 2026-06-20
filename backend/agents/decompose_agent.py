"""
backend/agents/decompose_agent.py

ScholarForge — Phase 3: Decompose Agent

Takes the structured dict produced by parser_agent.parse_paper() and uses
an LLM on Groq (free tier, Llama models) to break the paper down into
modular ML implementation components:
    - model_architecture
    - loss_function
    - training_loop
    - data_preprocessing
    - evaluation_metric

Returns a list of dicts, each with:
    component_name, description, equations, implementation_hints

Requires GROQ_API_KEY in your .env file (or environment).
"""

import os
import json

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Keep the prompt within a safe context size — long papers get truncated.
MAX_SECTION_CHARS = 12000

COMPONENT_TYPES = [
    "model_architecture",
    "loss_function",
    "training_loop",
    "data_preprocessing",
    "evaluation_metric",
]


def _build_paper_context(parsed_paper: dict) -> str:
    """Flatten the parsed paper dict into a single text block for the prompt."""
    title = parsed_paper.get("title", "")
    abstract = parsed_paper.get("abstract", "")
    sections = parsed_paper.get("sections", [])
    equations = parsed_paper.get("equations", [])

    section_text = "\n\n".join(
        f"### {s.get('heading', 'Untitled')}\n{s.get('text', '')}" for s in sections
    )
    if len(section_text) > MAX_SECTION_CHARS:
        section_text = section_text[:MAX_SECTION_CHARS] + "\n...[truncated]"

    equations_text = "\n".join(f"- {eq}" for eq in equations) if equations else "None found."

    return (
        f"TITLE:\n{title}\n\n"
        f"ABSTRACT:\n{abstract}\n\n"
        f"SECTIONS:\n{section_text}\n\n"
        f"EQUATIONS:\n{equations_text}"
    )


def _build_prompt(paper_context: str) -> str:
    component_list = ", ".join(COMPONENT_TYPES)
    return (
        "You are an ML research engineer. Read the research paper content below "
        "and decompose it into modular implementation components.\n\n"
        f"Identify components from these categories where present in the paper: {component_list}.\n"
        "If a category genuinely isn't discussed in the paper, omit it rather than inventing one.\n\n"
        "Respond with ONLY a JSON array (no markdown, no commentary) where each item has exactly "
        "these keys:\n"
        '  "component_name": one of the categories above\n'
        '  "description": a clear 2-4 sentence explanation of what this component does in the paper\n'
        '  "equations": a list of relevant equation strings from the paper (empty list if none)\n'
        '  "implementation_hints": 2-4 concrete, actionable notes for implementing this in Python/PyTorch\n\n'
        f"PAPER CONTENT:\n{paper_context}\n\n"
        "Respond with ONLY the JSON array."
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
        # NOTE: not all Groq models support strict JSON mode the same way,
        # so we ask for JSON in the prompt instead and parse defensively below.
    )
    return completion.choices[0].message.content


def _parse_json_array(raw_text: str) -> list:
    """Defensively parse a JSON array out of the model's raw text response."""
    text = raw_text.strip()

    # Strip markdown code fences if the model added them anyway.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    # If the model wrapped the array in an object, try to find the array inside it.
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

    # Last resort: find the first '[' and last ']' and try again.
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse a JSON array from model output:\n{raw_text[:500]}")


def decompose_paper(parsed_paper: dict) -> list:
    """
    Decompose a parsed paper dict into ML implementation components.

    Returns a list of dicts:
        [{"component_name": ..., "description": ..., "equations": [...],
          "implementation_hints": [...]}, ...]
    On failure, returns a list with a single dict containing an "error" key.
    """
    if not os.getenv("GROQ_API_KEY"):
        return [{"error": "GROQ_API_KEY not found. Add it to your .env file in backend/."}]

    paper_context = _build_paper_context(parsed_paper)
    prompt = _build_prompt(paper_context)

    try:
        raw_response = _call_groq(prompt)
    except Exception as e:
        return [{"error": f"Groq API call failed: {e}"}]

    try:
        components = _parse_json_array(raw_response)
    except ValueError as e:
        return [{"error": str(e)}]

    # Basic shape validation so downstream agents don't choke on malformed items.
    cleaned = []
    for item in components:
        if not isinstance(item, dict):
            continue
        cleaned.append({
            "component_name": item.get("component_name", "unknown"),
            "description": item.get("description", ""),
            "equations": item.get("equations", []) or [],
            "implementation_hints": item.get("implementation_hints", []) or [],
        })

    if not cleaned:
        return [{"error": "Model returned no valid components."}]

    return cleaned


if __name__ == "__main__":
    import sys

    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "sample_paper.pdf"

    # Reuse Phase 2's parser so this can be tested end-to-end on its own.
    from parser_agent import parse_paper

    print(f"Parsing {pdf_path} with Grobid...")
    parsed = parse_paper(pdf_path)
    if parsed.get("error"):
        print(json.dumps(parsed, indent=2))
        sys.exit(1)

    print("Decomposing into ML components with Groq...")
    components = decompose_paper(parsed)
    print(json.dumps(components, indent=2))
