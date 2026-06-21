"""
backend/agents/parser_agent.py

ScholarForge — Phase 2: PDF Parser Agent

Sends a PDF to a locally running Grobid instance (default: localhost:8070),
parses the returned TEI XML, and extracts a clean, structured dictionary:
title, abstract, sections (with text), equations, and references.
"""

import os
import requests
import xml.etree.ElementTree as ET

GROBID_URL = os.getenv("GROBID_URL", "http://localhost:8070")
TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def _text(el) -> str:
    """Flatten all text inside an element (including tails of children)."""
    if el is None:
        return ""
    return " ".join(t.strip() for t in el.itertext() if t.strip())


def _extract_title(root) -> str:
    title_el = root.find(
        ".//tei:fileDesc/tei:titleStmt/tei:title", TEI_NS
    )
    return _text(title_el)


def _extract_abstract(root) -> str:
    abstract_paras = root.findall(
        ".//tei:profileDesc/tei:abstract//tei:p", TEI_NS
    )
    if not abstract_paras:
        # fall back to raw abstract text if no <p> children
        abstract_el = root.find(".//tei:profileDesc/tei:abstract", TEI_NS)
        return _text(abstract_el)
    return "\n".join(_text(p) for p in abstract_paras)


def _extract_sections(root) -> list:
    sections = []
    body_divs = root.findall(".//tei:text/tei:body/tei:div", TEI_NS)
    for div in body_divs:
        head_el = div.find("tei:head", TEI_NS)
        heading = _text(head_el) if head_el is not None else "Untitled Section"
        paragraphs = div.findall("tei:p", TEI_NS)
        section_text = "\n".join(_text(p) for p in paragraphs)
        if heading or section_text:
            sections.append({"heading": heading, "text": section_text})
    return sections


def _extract_equations(root) -> list:
    equations = []
    formulas = root.findall(".//tei:text//tei:formula", TEI_NS)
    for i, f in enumerate(formulas):
        equations.append({
            "id": f.attrib.get("{http://www.w3.org/XML/1998/namespace}id", f"eq_{i}"),
            "text": _text(f),
        })
    return equations


def _extract_references(root) -> list:
    references = []
    bibl_structs = root.findall(
        ".//tei:text/tei:back//tei:listBibl/tei:biblStruct", TEI_NS
    )
    for bs in bibl_structs:
        # Title: prefer analytic (article) title, fall back to monograph title
        title_el = bs.find(".//tei:analytic/tei:title", TEI_NS)
        if title_el is None:
            title_el = bs.find(".//tei:monogr/tei:title", TEI_NS)
        title = _text(title_el)

        # Authors
        authors = []
        author_els = bs.findall(".//tei:analytic/tei:author") or bs.findall(
            ".//tei:monogr/tei:author"
        )
        for a in bs.findall(".//tei:author", TEI_NS):
            forename = a.find(".//tei:forename", TEI_NS)
            surname = a.find(".//tei:surname", TEI_NS)
            name_parts = [_text(forename), _text(surname)]
            full_name = " ".join(p for p in name_parts if p)
            if full_name:
                authors.append(full_name)

        # Year
        date_el = bs.find(".//tei:imprint/tei:date", TEI_NS)
        year = date_el.attrib.get("when", "") if date_el is not None else ""

        # DOI / external id if present
        idno_el = bs.find(".//tei:idno", TEI_NS)
        doi = _text(idno_el) if idno_el is not None else ""

        if title or authors:
            references.append({
                "title": title,
                "authors": authors,
                "year": year,
                "doi": doi,
            })
    return references


def parse_paper(pdf_path: str) -> dict:
    """
    Send a PDF to Grobid and return a structured dict:
    {
        "title": str,
        "abstract": str,
        "sections": [{"heading": str, "text": str}, ...],
        "equations": [{"id": str, "text": str}, ...],
        "references": [{"title": str, "authors": [...], "year": str, "doi": str}, ...],
        "error": str | None
    }
    """
    result = {
        "title": "",
        "abstract": "",
        "sections": [],
        "equations": [],
        "references": [],
        "error": None,
    }

    if not os.path.exists(pdf_path):
        result["error"] = f"PDF not found at path: {pdf_path}"
        return result

    endpoint = f"{GROBID_URL}/api/processFulltextDocument"

    # The free public Grobid demo server (cloud.science-miner.com) has a
    # broken/self-signed SSL certificate that fails standard verification —
    # this is a known issue with that specific server, not something we can
    # fix on our end. We only relax verification for that exact host; any
    # other Grobid endpoint (your own Docker container, a properly-deployed
    # instance, etc.) still gets full certificate verification as normal.
    verify_ssl = "cloud.science-miner.com" not in GROBID_URL

    try:
        with open(pdf_path, "rb") as f:
            files = {"input": (os.path.basename(pdf_path), f, "application/pdf")}
            data = {
                "consolidateHeader": "1",
                "consolidateCitations": "0",
                "includeRawCitations": "0",
            }
            response = requests.post(
                endpoint, files=files, data=data, timeout=180, verify=verify_ssl
            )
    except requests.exceptions.ConnectionError:
        result["error"] = (
            f"Could not connect to Grobid at {GROBID_URL}. "
            "Make sure the Grobid Docker container is running "
            "(docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0)."
        )
        return result
    except requests.exceptions.Timeout:
        result["error"] = "Grobid request timed out. The PDF may be too large or Grobid is overloaded."
        return result
    except Exception as e:
        result["error"] = f"Unexpected error calling Grobid: {e}"
        return result

    if response.status_code != 200:
        result["error"] = f"Grobid returned status {response.status_code}: {response.text[:300]}"
        return result

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as e:
        result["error"] = f"Failed to parse Grobid TEI XML: {e}"
        return result

    try:
        result["title"] = _extract_title(root)
        result["abstract"] = _extract_abstract(root)
        result["sections"] = _extract_sections(root)
        result["equations"] = _extract_equations(root)
        result["references"] = _extract_references(root)
    except Exception as e:
        result["error"] = f"Error extracting fields from TEI XML: {e}"

    return result


if __name__ == "__main__":
    import json
    import sys

    test_path = sys.argv[1] if len(sys.argv) > 1 else "sample_paper.pdf"
    parsed = parse_paper(test_path)
    print(json.dumps(parsed, indent=2)[:3000])
