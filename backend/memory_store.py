"""
Persistent, reusable memory of past question/answer pairs - the actual
missing piece identified when comparing this app's architecture to a
"human-like" Bible AI: today every query is answered cold, with nothing
learned from query N making query N+1 better, even when they're nearly
the same question.

An entry only becomes searchable/reusable ("promoted") through one of two
gates, never an automated confidence score (LLMs can't reliably self-report
correctness, and retrieval relevance score was already shown elsewhere in
this codebase not to correlate with answer quality):

- FACTUAL queries: promoted automatically if grounding_check.py's
  deterministic verification passes (every citation exists, every quote
  matches the real verse text, no hedge language).
- INTERPRETIVE/theological queries: promoted only after an explicit human
  thumbs-up via POST /commentary/approve - there's no ground truth to
  check automatically, so a real human judgment call is the honest gate.

Storage is a flat JSONL file (mirrors kjv_chunks.jsonl / commentary_chunks
.jsonl elsewhere in this codebase) plus an in-memory embedding matrix
rebuilt on write. This is intentionally NOT FAISS: the memory store is
expected to stay small (dozens-hundreds of entries for a personal app), so
a full rebuild on each write is simpler than incremental FAISS index
maintenance and costs nothing noticeable at this scale.
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import config
import search_semantic

logger = logging.getLogger(__name__)

if config.BASE_DIR.parent == Path("/"):
    _MEMORY_DIR = config.BASE_DIR / "cache" / "memory"
else:
    _MEMORY_DIR = config.CACHE_DIR / "memory"

_MEMORY_FILE = _MEMORY_DIR / "answered_questions.jsonl"

_entries_cache: Optional[List[Dict]] = None
_embeddings_cache = None
_np = None


def _get_numpy():
    global _np
    if _np is None:
        import numpy as np
        _np = np
    return _np


def _load_entries() -> List[Dict]:
    global _entries_cache
    if _entries_cache is not None:
        return _entries_cache
    entries = []
    if _MEMORY_FILE.exists():
        with open(_MEMORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    _entries_cache = entries
    return entries


def _rebuild_embeddings():
    """Recompute embeddings for every PROMOTED entry's query text. Only
    promoted entries are embedded/searchable - unreviewed or failed-
    grounding entries are stored (for later human review) but never
    surfaced as prior context."""
    global _embeddings_cache
    np = _get_numpy()
    entries = _load_entries()
    promoted = [e for e in entries if e.get('promoted')]

    if not promoted:
        _embeddings_cache = (None, [])
        return

    model = search_semantic.get_shared_model()
    texts = [e['query'] for e in promoted]
    embeddings = model.encode(texts, convert_to_numpy=True)
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    _embeddings_cache = (embeddings.astype('float32'), promoted)


def _append_entry(entry: Dict):
    _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(_MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    _entries_cache.append(entry) if _entries_cache is not None else _load_entries()
    global _embeddings_cache
    _embeddings_cache = None  # invalidate; rebuilt lazily on next search


def add_entry(
    query: str,
    commentary: str,
    verses_used: List[Dict],
    query_type: str,
    grounded: bool,
    model_info: Optional[Dict] = None,
) -> Dict:
    """
    Store a new answered question. query_type is 'factual' or
    'interpretive' (see app_refactored.py's classification). Returns the
    stored entry (including its id, needed by the frontend to later call
    /commentary/approve for interpretive entries).
    """
    promoted = query_type == 'factual' and grounded

    entry = {
        'id': f"mem_{uuid.uuid4().hex[:12]}",
        'query': query,
        'commentary': commentary,
        'verses_used': [
            {'reference': v['reference'], 'text': v['text']}
            for v in verses_used[:10]
        ],
        'query_type': query_type,
        'grounded': grounded,
        'human_approved': None,
        'promoted': promoted,
        'model_info': model_info or {},
    }
    _append_entry(entry)
    logger.info(f"Memory entry stored: {entry['id']} (type={query_type}, promoted={promoted})")
    return entry


def approve_entry(entry_id: str) -> Optional[Dict]:
    """Human thumbs-up: promote an interpretive entry into reusable
    memory. Rewrites the JSONL file since entries need in-place update
    (a small, infrequent operation - not a hot path)."""
    entries = _load_entries()
    updated = None
    for entry in entries:
        if entry['id'] == entry_id:
            entry['human_approved'] = True
            entry['promoted'] = True
            updated = entry
            break

    if updated is None:
        return None

    with open(_MEMORY_FILE, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    global _embeddings_cache
    _embeddings_cache = None
    logger.info(f"Memory entry approved: {entry_id}")
    return updated


def search_memory(query: str, min_similarity: float = 0.25, max_results: int = 1) -> List[Dict]:
    """Find prior PROMOTED answers similar to query, for use as context in
    a fresh answer (see commentary_summarizer_openai.py) - never returned
    as a verbatim replacement, only as prior-discussion context the model
    can draw on, same as Strong's word studies or the commentary corpus.

    0.25 is calibrated, not a guess, and is much lower than it would be for
    matching a query against long prose (like search_commentary_corpus.py's
    0.58) because this is short-question-to-short-question similarity, a
    different distribution with a much lower baseline. Measured directly:
    genuinely unrelated question pairs scored 0.07-0.15 ("explain
    sanctification" vs "why do bad things happen to good people": 0.07),
    while real paraphrases scored 0.29-0.95 depending on lexical overlap
    ("explain sanctification" vs "what does it mean to become holy": 0.29;
    "how old was Jesus when he died" vs "what age was Jesus at his death":
    0.95). 0.25 sits just below the lowest genuine match observed and well
    above the unrelated cluster.
    """
    if not query or not query.strip():
        return []

    global _embeddings_cache
    if _embeddings_cache is None:
        _rebuild_embeddings()

    embeddings, promoted = _embeddings_cache
    if embeddings is None or len(promoted) == 0:
        return []

    np = _get_numpy()
    model = search_semantic.get_shared_model()
    query_embedding = model.encode([query], convert_to_numpy=True)
    query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)

    similarities = (embeddings @ query_embedding[0]).tolist()
    ranked = sorted(zip(similarities, promoted), key=lambda x: x[0], reverse=True)

    results = []
    for similarity, entry in ranked[:max_results]:
        if similarity < min_similarity:
            continue
        results.append({**entry, 'similarity': round(float(similarity), 4)})
    return results


def get_best_match_debug(query: str) -> Optional[Dict]:
    """
    Return the single closest promoted entry regardless of threshold, with
    its similarity - for logging/analysis only, never for prompt context.

    This exists so near-misses (queries that almost matched but fell below
    search_memory()'s 0.25 cutoff) are actually recorded somewhere. Without
    this, there was no way to answer "which recurring topics keep failing
    to match" other than guessing - the exact data the concept-document
    curation approach needs.
    """
    if not query or not query.strip():
        return None

    global _embeddings_cache
    if _embeddings_cache is None:
        _rebuild_embeddings()

    embeddings, promoted = _embeddings_cache
    if embeddings is None or len(promoted) == 0:
        return None

    np = _get_numpy()
    model = search_semantic.get_shared_model()
    query_embedding = model.encode([query], convert_to_numpy=True)
    query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)

    similarities = (embeddings @ query_embedding[0]).tolist()
    best_similarity, best_entry = max(zip(similarities, promoted), key=lambda x: x[0])

    return {
        'query': best_entry['query'],
        'similarity': round(float(best_similarity), 4),
        'matched': best_similarity >= 0.25,
    }


def format_memory_context(results: List[Dict]) -> str:
    """Render prior related discussion as a prompt-ready text block."""
    if not results:
        return ""

    lines = [
        "Related Prior Discussion (a similar question was previously asked "
        "and answered - use it as helpful context, but still answer THIS "
        "question directly rather than just repeating the prior answer):"
    ]
    for r in results:
        lines.append(f"- Previously asked: \"{r['query']}\" (similarity: {r['similarity']:.0%})")
        lines.append(f"  Previous answer: {r['commentary'][:400]}")
    return "\n".join(lines)
