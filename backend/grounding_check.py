"""
Deterministic grounding check for generated commentary.

This exists specifically to gate what's allowed into the memory store
(memory_store.py) without a hand-wavy "confidence score." An LLM cannot
reliably self-report its own correctness (already demonstrated in this
codebase: retrieval relevance score looked like a plausible confidence
signal and empirically wasn't - see _assess_query_complexity's docstring).
What CAN be checked deterministically:

1. Every cited verse reference actually exists in the corpus.
2. Any quoted text attributed to a citation actually matches that verse's
   real text (catches paraphrase-drift and outright hallucination).
3. The answer doesn't contain the model's own hedge language admitting it
   couldn't ground the answer (e.g. "not derived from the given verses").

This is necessarily a check for FACTUAL answers, where "grounded in the
provided verses" is a meaningful, checkable property. It says nothing about
whether an INTERPRETIVE/theological answer is theologically sound - that
has no ground truth to check against, which is why memory_store.py gates
interpretive answers on human approval instead of this.
"""

import re
from typing import Dict, List

import reference_lookup

_HEDGE_PHRASES = [
    'not derived from the given verses',
    'not derived from the provided verses',
    'from prior knowledge',
    'based on prior knowledge',
    'do not contain this information',
    'does not contain this information',
    'do not directly address this topic',
    'cannot be provided based on the given',
    'is not among them',
    'is not present in the provided',
    'not mentioned in the given verses',
    'insufficient information',
    'cannot determine',
]

_QUOTE_RE = re.compile(r'"([^"]{15,})"')


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def _quote_matches_any_verse(quote: str, verses: List[Dict]) -> bool:
    """A quote is considered grounded if it's a close substring/match of
    at least one of the verses actually used for this answer."""
    quote_norm = _normalize(quote)
    if not quote_norm:
        return True  # nothing to check
    for v in verses:
        verse_norm = _normalize(v.get('text', ''))
        if quote_norm in verse_norm or verse_norm in quote_norm:
            return True
        # Loose overlap check for minor paraphrase (e.g. dropped "the")
        quote_words = set(quote_norm.split())
        verse_words = set(verse_norm.split())
        if quote_words and len(quote_words & verse_words) / len(quote_words) > 0.8:
            return True
    return False


def check_grounding(commentary: str, verses: List[Dict], book_names: List[str]) -> Dict:
    """
    Returns:
        {
            'grounded': bool,
            'hedge_detected': bool,
            'citations_checked': int,
            'citations_invalid': List[str],
            'quotes_checked': int,
            'quotes_unmatched': int,
        }
    """
    commentary_lower = commentary.lower()
    hedge_detected = any(phrase in commentary_lower for phrase in _HEDGE_PHRASES)

    cited_refs = reference_lookup.find_all_references(commentary, book_names)
    citations_invalid = []
    for ref in cited_refs:
        if not any(
            v['book'] == ref['book'] and v['chapter'] == ref['chapter']
            and ref['verse_start'] <= v.get('verse', -1) <= ref['verse_end']
            for v in verses
        ):
            citations_invalid.append(f"{ref['book']} {ref['chapter']}:{ref['verse_start']}")

    quotes = _QUOTE_RE.findall(commentary)
    quotes_unmatched = sum(1 for q in quotes if not _quote_matches_any_verse(q, verses))

    grounded = (
        not hedge_detected
        and not citations_invalid
        and quotes_unmatched == 0
    )

    return {
        'grounded': grounded,
        'hedge_detected': hedge_detected,
        'citations_checked': len(cited_refs),
        'citations_invalid': citations_invalid,
        'quotes_checked': len(quotes),
        'quotes_unmatched': quotes_unmatched,
    }
