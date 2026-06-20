"""
backend/mcp/arxiv_mcp.py

ScholarForge — Phase 8A: Arxiv MCP

Fetches related papers from arXiv for a given query — useful for finding
papers cited by, or similar to, the one currently being processed.
"""

import arxiv


def fetch_related_papers(query: str, max_results: int = 5) -> list:
    """
    Search arXiv for papers matching `query`.

    Returns a list of dicts: {title, authors, abstract, pdf_url, published_date}
    On failure, returns a list with a single dict containing an "error" key.
    """
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        papers = []
        for result in client.results(search):
            papers.append({
                "title": result.title,
                "authors": [author.name for author in result.authors],
                "abstract": result.summary.replace("\n", " ").strip(),
                "pdf_url": result.pdf_url,
                "published_date": result.published.strftime("%Y-%m-%d") if result.published else "",
            })
        return papers

    except Exception as e:
        return [{"error": f"Arxiv search failed: {e}"}]


if __name__ == "__main__":
    import sys
    import json

    query = sys.argv[1] if len(sys.argv) > 1 else "attention is all you need"
    print(f"Searching arXiv for: '{query}'\n")
    results = fetch_related_papers(query, max_results=5)
    print(json.dumps(results, indent=2))
