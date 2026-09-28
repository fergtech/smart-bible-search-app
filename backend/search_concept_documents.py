"""
Semantic search over the theological concept document corpus (see
build_concept_documents.py for why this exists and what it fixes).

Structured the same way as search_commentary_corpus.py: a separate index
because this is reference/glossary material, not scripture or a specific
author's commentary - so it gets attributed as such, and calibrated
independently since its similarity distribution differs from both the
Bible-verse index and the commentary-corpus index.

Extending this corpus: don't guess new concepts upfront. Check
logs/app.log for 'memory_search' events where "matched": false and the
same topic recurs - that's the real signal for which concept a document
would actually help, per the "measure failures first" approach validated
in this codebase already (it's exactly why get_best_match_debug() exists
in memory_store.py).
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

import config
import search_semantic

logger = logging.getLogger(__name__)

if config.BASE_DIR.parent == Path("/"):
    _DATA_DIR = config.BASE_DIR
else:
    _DATA_DIR = config.DATA_DIR

_CHUNKS_FILE = _DATA_DIR / "concept_documents.jsonl"
_INDEX_FILE = config.CACHE_DIR / "concept_index.faiss"

_faiss_index = None
_concepts = None
_np = None


def _get_numpy():
    global _np
    if _np is None:
        import numpy as np
        _np = np
    return _np


def _load() -> bool:
    global _faiss_index, _concepts

    if _faiss_index is not None:
        return True

    if not _INDEX_FILE.exists() or not _CHUNKS_FILE.exists():
        logger.info(
            f"Concept document corpus not found ({_INDEX_FILE}, {_CHUNKS_FILE}). "
            "Run build_concept_documents.py to enable it."
        )
        return False

    import faiss
    _faiss_index = faiss.read_index(str(_INDEX_FILE))

    concepts = []
    with open(_CHUNKS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                concepts.append(json.loads(line))
    _concepts = concepts

    logger.info(f"Loaded concept document corpus: {len(_concepts)} concepts")
    return True


def search_concepts(query: str, max_results: int = 2, min_similarity: float = 0.45) -> List[Dict]:
    """
    Find relevant concept documents for a query.

    0.45 is calibrated against build_concept_documents.py's own sanity
    checks: the three known embedding-gap failure cases this corpus exists
    to fix scored 0.41-0.63 against their correct concept document, so the
    threshold sits below that range while still well above noise (concept
    documents are short and topically narrow, so unrelated queries score
    considerably lower than they do against the longer, broader commentary
    corpus).
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
        concept = _concepts[idx]
        results.append({
            **concept,
            "relevance_score": round(float(similarity), 4),
        })
        if len(results) >= max_results:
            break

    return results


def format_concept_context(results: List[Dict]) -> str:
    """Render concept documents as a prompt-ready text block."""
    if not results:
        return ""

    lines = ["Relevant Theological Concepts (glossary reference, for context):"]
    for r in results:
        lines.append(f"- {r['concept']}: {r['text']}")
    return "\n".join(lines)
