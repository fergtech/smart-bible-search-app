"""
Build a searchable, embedded corpus from local, offline commentary/devotional
PDFs (Ellen G. White works: The Great Controversy, The Desire of Ages, Steps
to Christ - all public domain). Combines every source PDF found in
COMMENTARY_SOURCES into one corpus so the backend only has to search one
index, while each chunk keeps its own accurate title/author for attribution.

These are NOT verse-by-verse Bible commentaries. They're narrative/devotional
works with inline bracketed Scripture citations (e.g. "[Romans 8:38, 39,
37.]") and original printed-edition page markers (e.g. "[175]") scattered
through the prose. This script extracts that text, strips the repeated
running headers/footers (detected generically by frequency, not hardcoded
per book), chunks it into paragraph-sized pieces, pulls out any Scripture
citations found in each chunk, and embeds the chunks with the same
sentence-transformers model already used for the KJV corpus.

Output:
  commentary_chunks.jsonl        - one chunk per line, tagged with its source
  cache/commentary_embeddings.npy
  cache/commentary_index.faiss

Usage: python build_commentary_corpus.py
"""

import json
import re
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

COMMENTARY_SOURCES = [
    Path("en_GC88.pdf"),
    Path("en_DA.pdf"),
    Path("en_SC.pdf"),
]

OUTPUT_JSONL = Path("commentary_chunks.jsonl")
CACHE_DIR = Path("cache")

CHUNK_WORD_TARGET = 180

_PAGE_MARKER_RE = re.compile(r"\[(\d{1,4})\]")
# Some books (The Great Controversy) wrap citations in brackets:
# "[Romans 8:38, 39, 37.]". Others (The Desire of Ages, Steps to Christ)
# cite inline with no brackets: "Job 14:4; Romans 8:7." Both forms are
# captured, then deduped.
_BRACKETED_REF_RE = re.compile(
    r"\[((?:[1-3]\s)?[A-Z][a-zA-Z]+\.?\s\d{1,3}:\d{1,3}(?:,\s*\d{1,3})*\.?)\]"
)
_INLINE_REF_RE = re.compile(
    r"(?<![\[\w])((?:[1-3]\s)?[A-Z][a-zA-Z]+\.?\s\d{1,3}:\d{1,3}(?:,\s*\d{1,3})*\.?)"
)
_STANDALONE_NUMBER_RE = re.compile(r"^\d{1,4}$")


def extract_scripture_refs(text: str) -> list:
    refs = set(_BRACKETED_REF_RE.findall(text)) | set(_INLINE_REF_RE.findall(text))
    return sorted(refs)


def clean_source_label(title: str, author: str) -> str:
    # PDF metadata sometimes has the year twice, e.g.
    # "The Great Controversy 1888 (1888)" -> "The Great Controversy 1888"
    match = re.search(r"\((\d{4})\)\s*$", title)
    if match and match.group(1) in title[: match.start()]:
        title = title[: match.start()].strip()
    return f"{title}, {author}"


def extract_page_lines(doc) -> list:
    """Return list of lines with running headers/footers dropped.

    These PDFs repeat the book title and bare page numbers on every page
    (LaTeX-generated running headers/footers). A short line that recurs
    often across the whole document is treated as a header/footer and
    dropped rather than spliced into the middle of a sentence. This is
    generic (frequency-based), so it works the same for any book in
    COMMENTARY_SOURCES without book-specific string matching.
    """
    raw_pages = []
    for page_index in range(doc.page_count):
        lines = [l.strip() for l in doc[page_index].get_text().split("\n") if l.strip()]
        raw_pages.append(lines)

    from collections import Counter
    line_counts = Counter(line for lines in raw_pages for line in lines)

    def is_header_or_footer(line: str) -> bool:
        if _STANDALONE_NUMBER_RE.match(line):
            return True
        if len(line.split()) <= 6 and line_counts[line] >= 4:
            return True
        return False

    all_lines = []
    for lines in raw_pages:
        for line in lines:
            if not is_header_or_footer(line):
                all_lines.append(line)
    return all_lines


def build_chunks(lines: list, id_prefix: str, source_label: str) -> list:
    """Join lines into a continuous stream, then split into ~CHUNK_WORD_TARGET
    word chunks, tracking the most recent [NNN] original-page marker seen."""
    full_text = re.sub(r"\s+", " ", " ".join(lines)).strip()
    sentences = re.split(r"(?<=[.!?])\s+", full_text)

    chunks = []
    current_words = []
    current_page_marker = None

    def flush():
        if not current_words:
            return
        text = " ".join(current_words).strip()
        if len(text.split()) < 20:
            return  # too short to be a useful standalone chunk
        scripture_refs = extract_scripture_refs(text)
        chunks.append({
            "page": current_page_marker,
            "text": text,
            "scripture_refs": scripture_refs,
            "source": source_label,
        })

    for sentence in sentences:
        marker_match = _PAGE_MARKER_RE.search(sentence)
        if marker_match:
            current_page_marker = int(marker_match.group(1))

        current_words.extend(sentence.split())
        if len(current_words) >= CHUNK_WORD_TARGET:
            flush()
            current_words = []

    flush()

    for i, chunk in enumerate(chunks):
        chunk["id"] = f"{id_prefix}_{i:05d}"

    return chunks


def process_source(pdf_path: Path) -> list:
    doc = fitz.open(str(pdf_path))
    meta = doc.metadata or {}
    title = meta.get("title") or pdf_path.stem
    author = meta.get("author") or "Unknown"
    source_label = clean_source_label(title, author)
    id_prefix = pdf_path.stem.lower().replace("en_", "")

    print(f"\n  {pdf_path.name}: \"{source_label}\" ({doc.page_count} pages)")

    lines = extract_page_lines(doc)
    chunks = build_chunks(lines, id_prefix, source_label)
    with_refs = sum(1 for c in chunks if c["scripture_refs"])
    print(f"    {len(chunks)} chunks, {with_refs} with Scripture citations ({with_refs / len(chunks) * 100:.1f}%)")
    return chunks


def main():
    print("=" * 70)
    print("Building combined commentary corpus (local, offline PDFs)")
    print("=" * 70)

    all_chunks = []
    for pdf_path in COMMENTARY_SOURCES:
        if not pdf_path.exists():
            print(f"\n  SKIP: {pdf_path} not found")
            continue
        all_chunks.extend(process_source(pdf_path))

    if not all_chunks:
        print("\nERROR: no source PDFs found, nothing to build.")
        return

    print(f"\nTotal chunks across all sources: {len(all_chunks)}")

    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    print(f"Saved chunks -> {OUTPUT_JSONL}")

    print("\nGenerating embeddings (sentence-transformers/all-MiniLM-L6-v2)...")
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True, batch_size=256)
    embeddings = embeddings.astype("float32")
    faiss.normalize_L2(embeddings)

    CACHE_DIR.mkdir(exist_ok=True)
    np.save(CACHE_DIR / "commentary_embeddings.npy", embeddings)

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, str(CACHE_DIR / "commentary_index.faiss"))

    print(f"Saved {embeddings.shape[0]} embeddings -> cache/commentary_embeddings.npy")
    print(f"Saved FAISS index -> cache/commentary_index.faiss")

    print("\n" + "=" * 70)
    print("Chunk counts by source:")
    print("=" * 70)
    from collections import Counter
    counts = Counter(c["source"] for c in all_chunks)
    for source, count in counts.items():
        print(f"  {count:5d}  {source}")

    print("\nDone. backend/search_commentary_corpus.py consumes these files.")


if __name__ == "__main__":
    main()
