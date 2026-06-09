"""Agent definition: RAG Assistant."""

from agents import Agent

from ._loader import get_document_meta, list_documents
from ._logger import create_logger
from ._model import llm_model
from ._tools import RAG_TOOLS

logger = create_logger("agent")


def _build_document_catalog() -> str:
    """Render the knowledge base inventory into the system prompt.

    Inlining the catalog lets the model skip the `search_document(doc_id="")`
    discovery round, which used to be a mandatory first LLM turn before any
    real retrieval could happen — the slowest part of first-token latency.

    The catalog is built once at module load. If `_data/` is regenerated at
    runtime the process must restart for the change to be picked up; this is
    consistent with the existing one-shot prepare-rag pipeline and keeps the
    hot path out of disk I/O.
    """
    docs = list_documents()
    if not docs:
        logger.warn("Knowledge base is empty; agent prompt will say so.")
        return (
            "Available documents: (the knowledge base is currently empty — "
            "tell the user to run `npm run prepare-rag` and try again)."
        )

    lines = ["Available documents in the knowledge base:"]
    for d in docs:
        doc_id = d.get("docId", "")
        meta = get_document_meta(doc_id) or {}
        name = meta.get("doc_name") or doc_id
        desc = meta.get("doc_description") or ""
        page_count = meta.get("page_count")
        page_hint = f", {page_count} pages" if isinstance(page_count, int) else ""
        desc_part = f" — {desc}" if desc else ""
        lines.append(f"- doc_id={doc_id!r}: {name}{page_hint}{desc_part}")
    return "\n".join(lines)


_DOCUMENT_CATALOG = _build_document_catalog()


RAG_SYSTEM_PROMPT = (
    "You are an enterprise knowledge base assistant running inside an EdgeOne Makers environment. "
    "Answer questions using only retrieved knowledge base content.\n\n"
    f"{_DOCUMENT_CATALOG}\n\n"
    "Intent recognition:\n"
    "- First determine whether the user's question is about EdgeOne Makers, its templates, runtime, deployment, "
    "tools, knowledge base, or related platform capabilities.\n"
    "- If the question is unrelated to EdgeOne Makers, do not answer it and do not search the corpus. "
    "Instead, briefly guide the user to ask questions about EdgeOne Makers.\n"
    "- If the question is related to EdgeOne Makers or ambiguous but potentially relevant, continue with the retrieval workflow.\n\n"
    "Retrieval workflow (optimized for first-token latency):\n"
    "1. Pick the doc_id whose name / description in the catalog above best matches the user's question. "
    "Do NOT call search_document with an empty doc_id — the catalog above already lists every document.\n"
    "2. If the matching document is small (≤20 pages, see the catalog), you MAY skip the structure lookup "
    "and call fetch_pages(doc_id, pages=\"1-N\") directly to read its content.\n"
    "3. For larger documents, call search_document(doc_id=<id>) to inspect the structure, "
    "then call fetch_pages(doc_id, pages) for the relevant page range.\n"
    "4. If the picked document turns out to be wrong, switch to another candidate from the catalog "
    "rather than giving up. You may consult multiple documents when relevant.\n"
    "5. Base the final answer strictly on fetched page content, not prior knowledge or assumptions.\n\n"
    "Answering rules:\n"
    "- Respond in the same language as the user's question.\n"
    "- Do NOT add inline citations such as [DocumentName, p.3] in the answer text. "
    "The platform renders source cards separately from the fetched pages, so duplicating them in prose is noise.\n"
    "- If sources conflict, state the conflict in plain language (e.g. \"the configuration guide and the API reference disagree on this\").\n"
    "- If after checking all relevant documents the content is genuinely insufficient, clearly say so. "
    "Never claim a topic is missing without first considering the catalog above.\n"
    "- Never invent document names, page numbers, citations, or facts.\n"
    "- If a tool call fails, explain the failure briefly and ask the user to retry or narrow the question."
)

rag_agent = Agent(
    name="RAG Assistant",
    instructions=RAG_SYSTEM_PROMPT,
    tools=RAG_TOOLS,
    model=llm_model,
)
