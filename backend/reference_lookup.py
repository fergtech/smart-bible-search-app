"""
Exact Bible-reference detection, direct lookup, and meta-question query
rewriting for the /commentary endpoint.

Fixes two confirmed retrieval failures from testing against Haven's
"Scripture Citation & Cross-Reference" test category:

1. "Give me the exact text of John 14:27" returned "not found," even
   though the word-perfect verse is stored and instantly retrievable via
   /chapter. Semantic search over a query that doesn't textually resemble
   the verse's own content is the wrong tool for a deterministic
   book:chapter:verse lookup - so this bypasses it entirely when a query
   names an exact reference.

2. "Where does Paul discuss the armor of God?" failed to retrieve
   Ephesians 6 at all, even though a direct query ("armor of God") finds
   it easily (0.62 similarity). The meta-question framing ("where does
   Paul discuss...") embeds the query toward "Paul" rather than the actual
   topic, so verses merely *introducing* Paul out-ranked the actual armor
   passage. extract_topic_for_search() strips that framing before the
   embedding call, without changing what's shown to the user or the LLM.
"""

import re
from typing import Dict, List, Optional

_book_pattern_cache = None
_cached_book_names = None

_REFERENCE_RE_TEMPLATE = r'\b({books})\s+(\d{{1,3}})\s*:\s*(\d{{1,3}})(?:\s*-\s*(\d{{1,3}}))?'

_EXACT_TEXT_PHRASES = [
    'exact text', 'exact wording', 'exact words', 'word for word',
    'verbatim', 'precisely what it says', 'quote it exactly',
]

# Meta-question framings that ask WHERE a topic is discussed rather than
# asking about the topic itself. Matched case-insensitively; the group
# after the linking phrase becomes the rewritten search query.
_META_QUESTION_RE = re.compile(
    r'\b(?:discuss(?:es)?|talks?\s+about|says?\s+about|mentions?|teach(?:es)?\s+about)\b\s+(.+)',
    re.IGNORECASE,
)
_LOCATION_TRIGGER_RE = re.compile(
    r'\b(where\s+(?:does|is|can\s+i\s+find|in\s+the\s+bible)|which\s+(?:book|verse|chapter))\b',
    re.IGNORECASE,
)


def get_book_names(verses: List[Dict]) -> List[str]:
    """Unique canonical book names as they appear in the loaded corpus."""
    global _cached_book_names
    if _cached_book_names is None:
        _cached_book_names = sorted({v['book'] for v in verses}, key=len, reverse=True)
    return _cached_book_names


def _get_pattern(book_names: List[str]) -> re.Pattern:
    global _book_pattern_cache
    if _book_pattern_cache is not None:
        return _book_pattern_cache
    escaped = [re.escape(b) for b in book_names]
    _book_pattern_cache = re.compile(
        _REFERENCE_RE_TEMPLATE.format(books='|'.join(escaped)),
        re.IGNORECASE,
    )
    return _book_pattern_cache


def find_all_references(text: str, book_names: List[str]) -> List[Dict]:
    """Return every exact book:chapter:verse[-verse] reference mentioned
    anywhere in text (not just the first) - used by grounding_check.py to
    verify every citation a generated answer makes, not just detect one."""
    if not book_names:
        return []
    refs = []
    for book_text, chapter, verse_start, verse_end in _get_pattern(book_names).findall(text):
        canonical = next((b for b in book_names if b.lower() == book_text.lower()), book_text)
        refs.append({
            'book': canonical,
            'chapter': int(chapter),
            'verse_start': int(verse_start),
            'verse_end': int(verse_end) if verse_end else int(verse_start),
        })
    return refs


def extract_reference(query: str, book_names: List[str]) -> Optional[Dict]:
    """Return {'book','chapter','verse_start','verse_end'} if the query
    names an exact book:chapter:verse[-verse] reference, else None."""
    if not book_names:
        return None
    match = _get_pattern(book_names).search(query)
    if not match:
        return None
    book_text, chapter, verse_start, verse_end = match.groups()
    canonical = next((b for b in book_names if b.lower() == book_text.lower()), book_text)
    return {
        'book': canonical,
        'chapter': int(chapter),
        'verse_start': int(verse_start),
        'verse_end': int(verse_end) if verse_end else int(verse_start),
    }


def lookup_reference(verses: List[Dict], ref: Dict) -> List[Dict]:
    """Direct exact lookup - no semantic search or LLM involved, so this
    can never hallucinate or mislabel a reference."""
    return [
        {**v, 'relevance_score': None}
        for v in verses
        if v['book'] == ref['book']
        and v['chapter'] == ref['chapter']
        and ref['verse_start'] <= v['verse'] <= ref['verse_end']
    ]


def wants_exact_text(query: str) -> bool:
    """True if the query is asking for literal/verbatim text, not an
    explanation - e.g. "give me the exact text of John 14:27"."""
    query_lower = query.lower()
    return any(phrase in query_lower for phrase in _EXACT_TEXT_PHRASES)


def extract_topic_for_search(query: str) -> str:
    """
    Strip "where does X discuss/talk about/mention Y" framing down to just
    Y for the semantic-search embedding call. Returns the original query
    unchanged if no such framing is detected, so this is a no-op for
    ordinary direct queries.
    """
    if not _LOCATION_TRIGGER_RE.search(query):
        return query

    match = _META_QUESTION_RE.search(query)
    if not match:
        return query

    topic = match.group(1).strip().rstrip('?.!').strip()
    return topic if topic else query
