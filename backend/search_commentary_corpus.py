"""
Semantic search over the local commentary/devotional corpus (currently:
The Great Controversy, The Desire of Ages, and Steps to Christ, all by
Ellen G. White - see build_commentary_corpus.py).

Separate from search_semantic.py (which searches Bible verses) because
this corpus has a different shape (page/paragraph chunks, not
book/chapter/verse) and a different purpose: supplementary historical,
devotional, or narrative commentary from a named author, not scripture.
Keeping it a distinct index means it never silently contaminates plain
verse search results, only the commentary generation flow that opts into
it. Each chunk carries its own "source" (title + author) since the corpus
spans multiple books.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import config
import search_semantic

logger = logging.getLogger(__name__)

if config.BASE_DIR.parent == Path("/"):
    _DATA_DIR = config.BASE_DIR
else:
    _DATA_DIR = config.DATA_DIR

_CHUNKS_FILE = _DATA_DIR / "commentary_chunks.jsonl"
_INDEX_FILE = config.CACHE_DIR / "commentary_index.faiss"

_faiss_index = None
_chunks = None
_np = None


def _get_numpy():
    global _np
    if _np is None:
        import numpy as np
        _np = np
    return _np


def _load() -> bool:
    """Lazy-load the commentary FAISS index and chunk text. Returns False
    (without raising) if the corpus hasn't been built, so callers can
    degrade gracefully instead of breaking commentary generation."""
    global _faiss_index, _chunks

    if _faiss_index is not None:
        return True

    if not _INDEX_FILE.exists() or not _CHUNKS_FILE.exists():
        logger.info(
            f"Commentary corpus not found ({_INDEX_FILE}, {_CHUNKS_FILE}). "
            "Run build_commentary_corpus.py to enable it."
        )
        return False

    import faiss
    _faiss_index = faiss.read_index(str(_INDEX_FILE))

    chunks = []
    with open(_CHUNKS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    _chunks = chunks

    logger.info(f"Loaded commentary corpus: {len(_chunks)} chunks")
    return True


def search_commentary_corpus(
    query: str,
    max_results: int = 3,
    min_similarity: float = 0.58,
) -> List[Dict]:
    """
    Find commentary/devotional passages relevant to a query, across all
    loaded sources (The Great Controversy, The Desire of Ages, Steps to
    Christ).

    A much higher min_similarity than the Bible verse search is deliberate
    and calibrated, not a guess: this corpus's prose shares enough generic
    "biblical register" vocabulary that even off-topic queries (e.g. "how
    many sons did Jacob have") scored 0.51-0.54 against it during testing,
    while genuinely on-topic queries (Reformation, prophecy, the sabbath,
    the mark of the beast) scored 0.62-0.75. 0.58 sits in that gap so this
    corpus only contributes when it actually has something relevant to say.
    """
    if not query or not query.strip():
        return []

    if not _load():
        return []

    model = search_semantic.get_shared_model()
    np = _get_numpy()

    query_embedding = model.encode([query], convert_to_numpy=True)
    query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)

    k = min(max_results * 4, _faiss_index.ntotal)
    similarities, indices = _faiss_index.search(query_embedding.astype("float32"), k)

    results = []
    for similarity, idx in zip(similarities[0], indices[0]):
        if similarity < min_similarity:
            continue
        chunk = _chunks[idx]
        results.append({
            **chunk,
            "relevance_score": round(float(similarity), 4),
        })
        if len(results) >= max_results:
            break

    return results


def format_commentary_context(results: List[Dict]) -> str:
    """Render commentary passages as a clearly-attributed, clearly-secondary
    prompt block. Attribution is mandatory here (not left to the LLM) and
    per-passage (not one blanket line) because this is a named author's
    interpretive/devotional writing, not scripture, and results can span
    multiple books - it must never be presented as if it were biblical
    text."""
    if not results:
        return ""

    lines = [
        "Supplementary Commentary (NOT scripture - each passage below is "
        "one author's interpretation/devotional writing from the named "
        "work; only use a passage if it is directly relevant to the "
        "question, and always attribute it by title and author if you use it):"
    ]
    for r in results:
        page_note = f", p. {r['page']}" if r.get("page") else ""
        lines.append(f"- [{r['source']}{page_note}] {r['text']}")
    return "\n".join(lines)
