"""
backend/mcp/hf_mcp.py

ScholarForge — Phase 8C: HuggingFace MCP (v2 — fixed search logic)

Searches HuggingFace Hub for pretrained models relevant to a paper's ML
task, so the Codegen Agent can reference real pretrained weights instead
of always generating from scratch.

Two things this version fixes vs. the original:
1. HF's `search` parameter does literal substring matching on model
   names/ids, NOT natural-language search. A long combined phrase like
   "machine learning Attention Is All You Need" will almost never match
   anything. This version tries progressively narrower single-keyword
   queries (extracted from the paper title) until one actually hits.
2. Newer huggingface_hub versions removed the `direction` parameter from
   list_models(). This version handles both old and new signatures so it
   doesn't silently break if the package gets upgraded later.
"""

import os
import re

from dotenv import load_dotenv
from huggingface_hub import HfApi

load_dotenv()

STOPWORDS = {
    "a", "an", "the", "is", "are", "all", "you", "need", "for", "of", "and",
    "to", "with", "using", "on", "in", "by", "at", "as", "we", "this", "new",
}


def _extract_keywords(text: str) -> list:
    """Pull out distinctive single words from text, longest/most specific first."""
    words = re.findall(r"[a-zA-Z]+", text or "")
    words = [w for w in words if w.lower() not in STOPWORDS and len(w) > 2]
    return sorted(set(words), key=len, reverse=True)


def _list_models_compat(api: HfApi, search: str, sort: str, limit: int) -> list:
    """
    Call list_models() in a way that works across huggingface_hub versions —
    older versions accept a `direction` kwarg for descending sort; newer
    versions dropped it.
    """
    try:
        return list(api.list_models(search=search, sort=sort, direction=-1, limit=limit))
    except TypeError:
        pass
    try:
        return list(api.list_models(search=search, sort=f"-{sort}", limit=limit))
    except Exception:
        return list(api.list_models(search=search, sort=sort, limit=limit))


def find_relevant_models(task: str, paper_title: str = "", top_k: int = 5) -> list:
    """
    Search HuggingFace Hub for models matching `task` and/or `paper_title`.

    Tries the combined query first, then the task alone, then individual
    keywords from the title — since HF's search is substring-based, narrower
    queries are more likely to actually match something.

    Returns a list of dicts: {model_id, task, downloads, description, model_url}
    On failure, returns a list with a single dict containing an "error" key.
    """
    try:
        api = HfApi(token=os.getenv("HF_TOKEN") or None)

        candidate_queries = []
        combined = f"{task} {paper_title}".strip()
        if combined:
            candidate_queries.append(combined)
        if task:
            candidate_queries.append(task)
        candidate_queries.extend(_extract_keywords(paper_title)[:5])

        models = []
        for query in candidate_queries:
            try:
                models = _list_models_compat(api, query, "downloads", top_k)
            except Exception:
                models = []
            if models:
                break

        results = []
        for model in models:
            tags = getattr(model, "tags", None) or []
            results.append({
                "model_id": model.id,
                "task": getattr(model, "pipeline_tag", None) or task,
                "downloads": getattr(model, "downloads", 0) or 0,
                "description": ", ".join(tags[:5]),
                "model_url": f"https://huggingface.co/{model.id}",
            })
        return results

    except Exception as e:
        return [{"error": f"HuggingFace search failed: {e}"}]


if __name__ == "__main__":
    import sys
    import json

    task = sys.argv[1] if len(sys.argv) > 1 else "text-classification"
    print(f"Searching HuggingFace Hub for task: '{task}'\n")
    results = find_relevant_models(task)
    print(json.dumps(results, indent=2))
