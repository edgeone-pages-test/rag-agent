#!/usr/bin/env python3
"""
prepare_rag_data.py — Scan the ./files/ directory and write RAG knowledge base
data into the project's private data directory.

Run directly (no arguments needed):
  cd public/prepare-rag
  python3 prepare_rag_data.py

Output directory layout (located at <project_root>/agents/_data/):
  agents/_data/
  ├── index.json                       ← Full document manifest (replaces listDocuments)
  └── {docId}/
      ├── meta.json                    ← Document metadata
      ├── structure.json (optional)    ← PageIndex tree structure
      └── pages/
          ├── 1.txt
          ├── 2.txt
          └── ...

Input directory convention:
  public/prepare-rag/
  ├── files/
  │   ├── annual-report-2025.pdf   ← Required
  │   ├── annual-report-2025.json  ← Optional, PageIndex (same name as PDF)
  │   └── ...
  ├── prepare_rag_data.py
  └── requirements.txt

Execution flow:
  1. Scan ./files/*.pdf, use filename (without extension) as doc_id
  2. If a same-name .json exists, include it as PageIndex tree structure
  3. Clear agents/_data/ and rebuild from scratch
  4. Generate agents/_data/index.json as the runtime manifest

⚠️ This directory is NOT exposed via express.static; it's only read by the server
   (see agents/loader.js).
"""

import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────

FILES_DIR = Path(__file__).parent / "files"

# Script path: public/prepare-rag/prepare_rag_data.py
# Data target: agents/_data/ (two levels up from this file to project root, then into agents/_data)
PROJECT_ROOT = Path(__file__).parent.parent.parent
AGENTS_DIR = PROJECT_ROOT / "agents"
RAG_OUT_DIR = AGENTS_DIR / "_data"


# ── PDF Text Extraction ──────────────────────────────────────────────────────

def load_pdf_reader():
    """Import pypdf or PyPDF2; exit with error if neither is available."""
    try:
        from pypdf import PdfReader
        return PdfReader
    except ImportError:
        pass
    try:
        from PyPDF2 import PdfReader
        return PdfReader
    except ImportError:
        print("❌ Missing PDF dependency. Please run: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)


def extract_pages(pdf_path: Path, PdfReader) -> tuple[dict[int, str], int]:
    """Extract text from each PDF page. Returns {page_number: text} and total page count."""
    reader = PdfReader(str(pdf_path))
    pages: dict[int, str] = {}
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            print(f"    ⚠️  Page {i + 1} extraction failed: {e}", file=sys.stderr)
            text = ""
        pages[i + 1] = text.strip()
    return pages, len(reader.pages)


# ── doc_id Processing ────────────────────────────────────────────────────────

def sanitize_doc_id(name: str) -> str:
    """Convert filename to a valid doc_id (keep only alphanumerics, underscores, hyphens)."""
    s = name.strip()
    s = re.sub(r"[\s.]+", "_", s)
    s = re.sub(r"[^\w\-]", "", s)
    s = s.strip("_")
    return s or "doc"


# ── Write Single Document ────────────────────────────────────────────────────

def write_document(
    pdf_path: Path,
    PdfReader,
    doc_id: str,
) -> dict:
    """Write meta.json / structure.json / pages/{n}.txt for a single PDF. Returns index.json entry."""
    print(f"\n  📄 {pdf_path.name}  →  doc_id: {doc_id}")

    # 1. Extract PDF text
    pages, page_count = extract_pages(pdf_path, PdfReader)
    text_pages = sum(1 for t in pages.values() if t)
    print(f"     Total {page_count} pages, {text_pages} pages with text")

    # 2. Try loading same-name PageIndex JSON
    index_path = pdf_path.with_suffix(".json")
    index_data: dict = {}
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        print(f"     Index: {index_path.name}  root: \u00ab{index_data.get('title', 'Untitled')}\u00bb")
    else:
        print(f"     Index: {index_path.name} not found, skipping structure.json")

    doc_name = index_data.get("title") or pdf_path.stem

    # 3. Prepare output directory
    doc_dir = RAG_OUT_DIR / doc_id
    pages_dir = doc_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    # 4. Write meta.json
    meta_payload = {
        "doc_name":        doc_name,
        "doc_description": index_data.get("summary", ""),
        "type":            "pdf",
        "page_count":      page_count,
        "status":          "completed",
        "created":         datetime.now(timezone.utc).isoformat(),
    }
    meta_path = doc_dir / "meta.json"
    meta_text = json.dumps(meta_payload, ensure_ascii=False, indent=2)
    meta_path.write_text(meta_text, encoding="utf-8")
    meta_bytes = len(meta_text.encode("utf-8"))

    # 5. Write structure.json (optional)
    structure_bytes = 0
    has_structure = bool(index_data)
    if has_structure:
        structure_text = json.dumps(index_data, ensure_ascii=False, indent=2)
        (doc_dir / "structure.json").write_text(structure_text, encoding="utf-8")
        structure_bytes = len(structure_text.encode("utf-8"))

    # 6. Write page text (skip empty pages)
    page_bytes = 0
    written_pages = 0
    skipped = 0
    for page_num, text in pages.items():
        if not text:
            skipped += 1
            continue
        page_file = pages_dir / f"{page_num}.txt"
        page_file.write_text(text, encoding="utf-8")
        page_bytes += len(text.encode("utf-8"))
        written_pages += 1

    if skipped:
        print(f"     Skipped {skipped} empty pages (image-only pages)")

    total_bytes = meta_bytes + structure_bytes + page_bytes
    print(
        f"     Written: 1 meta + {'1' if has_structure else '0'} structure + "
        f"{written_pages} pages  ({total_bytes / 1024:.1f} KB)"
    )

    return {
        "docId":          doc_id,
        "meta":           meta_payload,
        "hasStructure":   has_structure,
        "pages":          written_pages,
        "metaBytes":      meta_bytes,
        "structureBytes": structure_bytes,
        "pageBytes":      page_bytes,
        "totalBytes":     total_bytes,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("  RAG Data Generator  —  PageIndex")
    print("=" * 60)

    # Check files directory
    if not FILES_DIR.exists():
        print(f"❌ Directory does not exist: {FILES_DIR}", file=sys.stderr)
        sys.exit(1)

    pdf_files = sorted(FILES_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"⚠️  No PDF files found in {FILES_DIR}")
        sys.exit(0)

    print(f"\n📁 Scanning directory: {FILES_DIR}")
    print(f"   Found {len(pdf_files)} PDF file(s):")
    for p in pdf_files:
        has_index = p.with_suffix(".json").exists()
        marker = "  ✦" if has_index else "  ·"
        print(f"{marker} {p.name}" + (" [has index]" if has_index else ""))

    # Clear and rebuild output directory
    if RAG_OUT_DIR.exists():
        print(f"\n🗑️  Clearing old directory: {RAG_OUT_DIR}")
        shutil.rmtree(RAG_OUT_DIR)
    RAG_OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load PDF parsing library
    PdfReader = load_pdf_reader()

    # Process each document
    print("\n── Writing document content " + "─" * 33)
    index_entries: list[dict] = []
    used_ids: list[str] = []

    for pdf_path in pdf_files:
        doc_id = sanitize_doc_id(pdf_path.stem)
        if doc_id in used_ids:
            doc_id = f"{doc_id}_{len(used_ids)}"
        used_ids.append(doc_id)

        entry = write_document(pdf_path, PdfReader, doc_id)
        index_entries.append(entry)

    # Summary statistics
    total_bytes = sum(e["totalBytes"] for e in index_entries)

    # Write index.json
    index_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "documents":    index_entries,
    }
    index_path = RAG_OUT_DIR / "index.json"
    index_path.write_text(
        json.dumps(index_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n── Summary " + "─" * 48)
    print(f"   Documents:    {len(pdf_files)}")
    print(f"   Total size:   {total_bytes / 1024:.1f} KB  ({total_bytes / 1024 / 1024:.2f} MB)")
    print(f"   Output dir:   {RAG_OUT_DIR.relative_to(PROJECT_ROOT)}")
    print(f"   Manifest:     {index_path.relative_to(PROJECT_ROOT)}")

    print("\n" + "=" * 60)
    print("  ✅ RAG data generation complete!")
    print("=" * 60)
    for doc_id in used_ids:
        print(f"   doc_id: {doc_id}")
    print()


if __name__ == "__main__":
    main()
