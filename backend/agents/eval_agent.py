"""
backend/agents/eval_agent.py

ScholarForge — Phase 7b: Self-Evaluation Agent

Scores generated code against a reference implementation using AST
structural similarity (utils/ast_evaluator.py). If the score is below
0.6, it retries code generation up to max_retries times, feeding the
score back into the prompt as feedback each time.
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "utils"))
from ast_evaluator import compute_ast_similarity  # noqa: E402

from codegen_agent import generate_code  # noqa: E402

PASS_THRESHOLD = 0.6


def evaluate_and_retry(
    component: dict,
    generated_code: str,
    reference_code: str,
    similar_implementations: list = None,
    max_retries: int = 3,
) -> dict:
    """
    Evaluate generated_code's structural similarity to reference_code.
    If the score is below PASS_THRESHOLD, retry generation (via
    codegen_agent.generate_code) up to max_retries total attempts,
    passing feedback about the shortfall back into the prompt each time.

    Returns:
        {
            "final_code": str,
            "final_score": float,
            "attempts": int,
            "passed": bool,
            "history": [{"attempt": int, "score": float}, ...]
        }
    """
    similar_implementations = similar_implementations or []
    history = []

    current_code = generated_code
    score = compute_ast_similarity(current_code, reference_code)
    history.append({"attempt": 1, "score": round(score, 3)})

    attempt = 1
    while score < PASS_THRESHOLD and attempt < max_retries:
        attempt += 1
        feedback = (
            f"Your previous attempt scored {score:.2f} structural similarity "
            f"(out of 1.0; needs to be >= {PASS_THRESHOLD}) when compared against a "
            "reference implementation. This usually means the code was too thin — "
            "missing classes, methods, or control flow that a complete implementation "
            "would have. Write a more complete, fully fleshed-out implementation this time."
        )
        current_code = generate_code(component, similar_implementations, feedback=feedback)
        score = compute_ast_similarity(current_code, reference_code)
        history.append({"attempt": attempt, "score": round(score, 3)})

    return {
        "final_code": current_code,
        "final_score": round(score, 3),
        "attempts": attempt,
        "passed": score >= PASS_THRESHOLD,
        "history": history,
    }


if __name__ == "__main__":
    import json

    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "sample_paper.pdf"

    # Chain Phases 2 -> 3 -> 5 -> 6 -> 7 so this can be tested standalone.
    from parser_agent import parse_paper
    from decompose_agent import decompose_paper
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "chroma_store",
        os.path.join(os.path.dirname(__file__), "..", "vector_store", "chroma_store.py"),
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

    target_component = components[0]
    print(f"\nGenerating code for: {target_component['component_name']}\n")

    similar = store.search_similar(target_component["description"], top_k=3)
    reference_code = similar[0]["code"] if similar else ""

    first_attempt = generate_code(target_component, similar)

    print("Evaluating and retrying if needed...\n")
    result = evaluate_and_retry(
        component=target_component,
        generated_code=first_attempt,
        reference_code=reference_code,
        similar_implementations=similar,
        max_retries=3,
    )

    print(f"Passed: {result['passed']}")
    print(f"Final score: {result['final_score']}")
    print(f"Attempts: {result['attempts']}")
    print(f"History: {result['history']}\n")
    print("--- FINAL CODE ---\n")
    print(result["final_code"])
