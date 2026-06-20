"""
ScholarForge - Parser Agent (Phase 2)

Sends a PDF to a Grobid server and extracts structured content:
title, abstract, sections, equations (best-effort), and references.

By default this points at a local Grobid instance running via Docker:
    docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0
    (then GROBID_URL=http://localhost:8070, the default below)

If you ever need a no-setup fallback for quick testing, the Grobid
team also runs a free public demo server (rate-limited, testing only):
    GROBID_URL=https://cloud.science-miner.com/grobid
"""

import os
import xml.etree.ElementTree as ET
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()  # picks up GROBID_URL (and other keys) from your .env file

GROBID_URL = os.getenv("GROBID_URL", "http://localhost:8070")
TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def parse_paper(pdf_path: str) -> dict:
    """
    Send a PDF to Grobid and return a structured dictionary:
    {
        "title": str,
        "abstract": str,
        "sections": [{"heading": str, "text": str}],
        "equations": [str],
        "references": [{"title": str, "authors": [str]}],
    }

    Returns a dict with an "error" key instead of raising, so the
    pipeline can decide how to handle a failure gracefully.
    """
    if not os.path.exists(pdf_path):
        return {"error": f"File not found: {pdf_path}"}

    try:
        with open(pdf_path, "rb") as f:
            response = requests.post(
                f"{GROBID_URL}/api/processFulltextDocument",
                files={"input": f},
                timeout=120,  # the public demo can be slow on a cold start
            )
    except requests.exceptions.RequestException as e:
        return {"error": f"Could not reach Grobid server at {GROBID_URL}: {e}"}

    if response.status_code != 200:
        return {
            "error": f"Grobid returned status {response.status_code}: {response.text[:300]}"
        }

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as e:
        return {"error": f"Failed to parse Grobid XML response: {e}"}

    return {
        "title": _extract_title(root),
        "abstract": _extract_abstract(root),
        "sections": _extract_sections(root),
        "equations": _extract_equations(root),
        "references": _extract_references(root),
    }


def _text_or_empty(el) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def _extract_title(root) -> str:
    el = root.find(".//tei:titleStmt/tei:title", TEI_NS)
    return _text_or_empty(el)


def _extract_abstract(root) -> str:
    el = root.find(".//tei:abstract", TEI_NS)
    return _text_or_empty(el)


def _extract_sections(root) -> list:
    sections = []
    for div in root.findall(".//tei:text/tei:body/tei:div", TEI_NS):
        heading_el = div.find("tei:head", TEI_NS)
        heading = _text_or_empty(heading_el) or "Untitled section"
        # Grab all paragraph text in this div, excluding the heading itself
        paragraphs = [
            _text_or_empty(p) for p in div.findall("tei:p", TEI_NS)
        ]
        sections.append({"heading": heading, "text": "\n".join(paragraphs)})
    return sections


def _extract_equations(root) -> list:
    # Grobid tags inline/display formulas as <formula> elements
    return [_text_or_empty(f) for f in root.findall(".//tei:formula", TEI_NS)]


def _extract_references(root) -> list:
    references = []
    for bibl in root.findall(".//tei:listBibl/tei:biblStruct", TEI_NS):
        title_el = bibl.find(".//tei:title", TEI_NS)
        authors = [
            _text_or_empty(a)
            for a in bibl.findall(".//tei:author//tei:surname", TEI_NS)
        ]
        references.append({
            "title": _text_or_empty(title_el),
            "authors": authors,
        })
    return references


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python parser_agent.py <path_to_pdf>")
        sys.exit(1)

    result = parse_paper(sys.argv[1])
    print(json.dumps(result, indent=2))