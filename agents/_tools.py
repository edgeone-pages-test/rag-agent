"""RAG tool definitions for OpenAI Agents SDK (Python).

5 tools: searchDocument, fetchPages, getWeather, getUserTimezone, calculate
"""

import json
import time
import random
from typing import Annotated

from agents import function_tool

from ._loader import (
    list_documents,
    get_document_meta,
    get_document_structure,
    get_page_content,
    parse_page_range,
)
from ._logger import create_logger

logger = create_logger("tools")


@function_tool
def search_document(
    query: Annotated[str, "User's search query"],
    doc_id: Annotated[str, "Document ID. Pass empty string to list all available documents and let the model pick the most relevant one(s)."] = "",
) -> str:
    """Search knowledge base documents. Returns document metadata and structure index for locating relevant pages.
    Always call this first when answering knowledge-base questions.

    Calling pattern:
      1. First call with doc_id="" to discover what documents exist in the knowledge base.
      2. Pick the document(s) whose names / descriptions best match the user's question.
      3. Call search_document again with the chosen doc_id to retrieve metadata + structure.
      4. Then call fetch_pages with the appropriate page range.
    """

    logger.log(f"searchDocument called: query=\"{query}\", doc_id=\"{doc_id}\"")

    # No doc_id → list all available documents and let the LLM choose the relevant one(s).
    # IMPORTANT: do NOT auto-pick the first document — the knowledge base may contain
    # multiple unrelated documents and silently picking docs[0] hides the rest from
    # the model, causing wrong "not found" answers.
    if not doc_id:
        docs = list_documents()
        logger.log(f"listDocuments returned {len(docs)} docs")
        if not docs:
            return json.dumps({
                "error": "Knowledge base is empty. Please run prepare_rag_data.py first.",
            }, ensure_ascii=False)

        return json.dumps({
            "query": query,
            "documentCount": len(docs),
            "documents": [
                {
                    "docId": d.get("docId", ""),
                    "meta": d.get("meta", {}),
                    "pages": d.get("pages", 0),
                    "hasStructure": d.get("hasStructure", False),
                }
                for d in docs
            ],
            "instruction": (
                "Multiple documents are available in the knowledge base. "
                "Review the document list above (especially `meta.doc_name` and `meta.doc_description`), "
                "select the document(s) most relevant to the user's question, "
                "then call search_document again with the chosen `doc_id` to retrieve its structure, "
                "or call fetch_pages directly if the document is small. "
                "If multiple documents look relevant, query them one by one."
            ),
        }, ensure_ascii=False)

    meta = get_document_meta(doc_id)
    if not meta:
        return json.dumps({
            "error": f"Document '{doc_id}' not found.",
        }, ensure_ascii=False)

    structure = get_document_structure(doc_id)

    # When no tree-structure index exists, instruct to fetch all pages for small docs
    if not structure:
        page_count = meta.get("page_count", 0)
        suggested_pages = f"1-{page_count}" if page_count <= 20 else "1-20"
        return json.dumps({
            "docId": doc_id,
            "query": query,
            "meta": meta,
            "structure": None,
            "instruction": (
                f"This document has no tree-structure index but contains {page_count} pages. "
                f"Please call fetchPages with pages=\"{suggested_pages}\" to retrieve the content, "
                "then answer the user's question based on the retrieved text."
            ),
        }, ensure_ascii=False)

    return json.dumps({
        "docId": doc_id,
        "query": query,
        "meta": meta,
        "structure": structure,
        "instruction": (
            "Analyze the document structure above, find sections most relevant to the user's question, "
            "determine the page range (start_index to end_index), "
            "then call fetchPages to retrieve the original text and answer based on it."
        ),
    }, ensure_ascii=False)


@function_tool
def fetch_pages(
    doc_id: Annotated[str, "Document ID"],
    pages: Annotated[str, "Page range, e.g. '5-7,12,15-16'. Max 20 pages per call."],
) -> str:
    """Fetch specific pages from a document. Use after searchDocument to retrieve actual content."""

    logger.log(f"fetchPages called: doc_id=\"{doc_id}\", pages=\"{pages}\"")

    page_list = parse_page_range(pages)
    if not page_list:
        return json.dumps({"error": "Invalid page range"}, ensure_ascii=False)

    content = get_page_content(doc_id, page_list)
    if not content:
        return json.dumps({"error": "No pages found"}, ensure_ascii=False)

    # Get document name for citation
    meta = get_document_meta(doc_id)
    doc_name = meta.get("doc_name", doc_id) if meta else doc_id

    total_chars = sum(len(p["content"]) for p in content)

    return json.dumps({
        "type": "citation_pages",
        "docId": doc_id,
        "docName": doc_name,
        "pages": pages,
        "pageCount": len(content),
        "totalChars": total_chars,
        "content": [
            {"page": p["page"], "content": p["content"], "preview": p["content"][:400]}
            for p in content
        ],
    }, ensure_ascii=False)


@function_tool
def get_weather(city: Annotated[str, "City name"]) -> str:
    """Get current weather for a city (mock data)."""
    conditions = ["sunny", "cloudy", "rainy"]
    temp = random.randint(5, 35)
    return json.dumps({
        "city": city,
        "temperature": temp,
        "condition": random.choice(conditions),
    })


@function_tool
def get_user_timezone() -> str:
    """Get the server's current timezone and local time."""
    return json.dumps({
        "timezone": time.tzname[0] if time.tzname[0] else "UTC",
        "localTime": time.strftime("%Y-%m-%d %H:%M:%S"),
    })


@function_tool
def calculate(
    a: Annotated[float, "First number"],
    b: Annotated[float, "Second number"],
    operator: Annotated[str, "Arithmetic operator: +, -, *, /, %"],
) -> str:
    """Perform a math calculation with two numbers."""
    ops = {
        "+": lambda x, y: x + y,
        "-": lambda x, y: x - y,
        "*": lambda x, y: x * y,
        "/": lambda x, y: x / y if y != 0 else None,
        "%": lambda x, y: x % y if y != 0 else None,
    }
    if operator not in ops:
        return json.dumps({"error": f"Unknown operator: {operator}"})
    result = ops[operator](a, b)
    if result is None:
        return json.dumps({"error": "Division by zero"})
    return json.dumps({
        "expression": f"{a} {operator} {b}",
        "result": result,
    })


# Tool collection for RAG agent
RAG_TOOLS = [search_document, fetch_pages, get_weather, get_user_timezone, calculate]
