"""
Hybrid search: merges keyword and semantic results instead of the
all-or-nothing choice the frontend used to make.

Previously (in frontend/search.js), a search ran keyword first and used
those results outright if ANY verse scored above 0.3 - falling back to
semantic only if keyword found nothing. This meant keyword search, once
it found anything decent, completely hid semantic results even when they
were clearly better suited. Confirmed live: "fruits of the spirit" (as
typed, plural) never surfaced Galatians 5:22 (the KJV's singular "fruit of
the Spirit"), because keyword mode "succeeded" - other spirit-related
verses scored well from individual word hits - and won outright before
semantic search ever got a chance.

A first attempt just merged both lists by taking each verse's best score
on a shared 0-1 scale (now possible since search_keyword.py's score was
normalized). That still failed the same test case: Romans 8:23 (keyword's
#1, score 1.0) doesn't even appear in the top 30 semantic results, meaning
its high keyword score is pure word-frequency coincidence, not real
relevance - yet a plain score merge still ranked it above Galatians 5:22
(semantic's #1, the verse most users would actually expect). Reciprocal
Rank Fusion was considered next, but doesn't resolve this either: both
verses are the #1 result of their own list, so a rank-based fusion just
ties them - rank position alone can't distinguish "genuinely the best
match" from "the top of a list prone to word-frequency artifacts."

What actually distinguishes them is WHY keyword ranked something highly.
An exact phrase match, or an exact whole-word match for a single-word
query (a name like "Melchizedek"), is an unambiguous, trustworthy signal.
A verse that only scored well from loose individual-term frequency
("of", "the", or any other word appearing several times) is exactly the
artifact-prone case. So this only trusts keyword results for genuine exact
matches, and ranks everything else by semantic similarity - which is a
real, well-calibrated relevance signal; loose keyword term-frequency isn't.
"""

import re
from typing import Dict, List

import search_keyword
import search_semantic


def hybrid_search(verses: List[Dict], query: str, max_results: int = 10) -> List[Dict]:
    if not query or not query.strip():
        return []

    fetch_n = max(max_results * 2, 20)

    keyword_results = search_keyword.search_keyword(verses, query, max_results=fetch_n)
    semantic_results = search_semantic.search_semantic(
        verses, query, max_results=fetch_n, min_similarity=0.2
    )

    query_lower = query.lower().strip()
    # Word-boundary aware, not a naive substring check: "fruits of the
    # spirit" is a raw substring of "firstfruits of the spirit" (Romans
    # 8:23), which a naive `query_lower in text_lower` check treated as an
    # exact match - confirmed live, and it's what let that verse jump the
    # queue ahead of Galatians 5:22 even after the tiering fix below.
    exact_pattern = re.compile(r'\b' + re.escape(query_lower) + r'\b')

    seen_keys = set()
    exact_tier = []

    for v in keyword_results:
        text_lower = v['text'].lower()
        if exact_pattern.search(text_lower):
            key = (v['book'], v['chapter'], v['verse'])
            if key not in seen_keys:
                exact_tier.append(v)
                seen_keys.add(key)

    semantic_tier = [
        v for v in semantic_results
        if (v['book'], v['chapter'], v['verse']) not in seen_keys
    ]

    return (exact_tier + semantic_tier)[:max_results]
