"""
Keyword-based search for Bible verses.
Implements traditional text matching with relevance scoring.
"""

import re
from typing import List, Dict

# Without this filter, a query like "fruits of the spirit" let "of" and
# "the" alone rack up term-frequency bonus points against ANY long,
# repetitive verse (confirmed live: Ezekiel 43:11, containing neither
# "fruits" nor "spirit", scored higher than Galatians 5:22 purely from
# repeated "of"/"the"/"all" - and since search.js prefers keyword results
# over semantic ones whenever any verse scores above 0.3, this silently
# replaced the actually-relevant semantic results with irrelevant ones).
_STOP_WORDS = {
    'a', 'an', 'the', 'of', 'and', 'or', 'but', 'to', 'in', 'on', 'at', 'by',
    'for', 'with', 'as', 'is', 'was', 'are', 'were', 'be', 'been', 'it',
    'that', 'this', 'these', 'those', 'from', 'not', 'so', 'if', 'then',
}


def search_keyword(verses: List[Dict], query: str, max_results: int = 10) -> List[Dict]:
    """
    Perform keyword-based search across verse text.
    
    Args:
        verses: List of verse dictionaries
        query: Search terms or phrase
        max_results: Maximum number of results to return
    
    Returns:
        List of matching verses with relevance scores, sorted by relevance
    """
    if not query or not query.strip():
        return []
    
    query_lower = query.lower().strip()
    all_terms = re.findall(r'\w+', query_lower)
    query_terms = [t for t in all_terms if t not in _STOP_WORDS] or all_terms

    results = []
    
    for verse in verses:
        text_lower = verse["text"].lower()
        
        # Check for exact phrase match
        exact_match = query_lower in text_lower
        
        # Count matching terms and their frequency
        matching_terms = sum(1 for term in query_terms if term in text_lower)
        
        if exact_match or matching_terms > 0:
            score = _calculate_relevance_score(
                text_lower, 
                query_lower, 
                query_terms, 
                exact_match, 
                matching_terms,
                len(verse["text"])
            )
            
            # The raw score above is an unbounded heuristic (word-frequency
            # and position bonuses stack with no ceiling) - fine for
            # internal ranking, but it was being returned as-is and the
            # frontend displays it directly as "{score}% match", which is
            # how a verse scored 1.05 rendered as "105% match". 12.0 is
            # calibrated to a strong exact-phrase match (+10 base, plus
            # some term-frequency bonus), so a real match approaches 1.0
            # and a thin one-word incidental match stays well below it.
            normalized_score = max(0.0, min(score / 12.0, 1.0))

            results.append({
                **verse,
                "relevance_score": round(normalized_score, 2),
                "_sort_score": score,
            })

    # Sort by the raw (unbounded) score, not the normalized display score,
    # so ranking still distinguishes strong matches that both happened to
    # clip to 1.0 after normalization.
    results.sort(key=lambda x: x["_sort_score"], reverse=True)

    for r in results:
        del r["_sort_score"]

    return results[:max_results]


def _calculate_relevance_score(
    text_lower: str,
    query_lower: str,
    query_terms: List[str],
    exact_match: bool,
    matching_terms: int,
    text_length: int
) -> float:
    """
    Calculate relevance score for a verse based on multiple factors.
    
    Args:
        text_lower: Lowercase verse text
        query_lower: Lowercase query string
        query_terms: List of query terms
        exact_match: Whether query exactly matches phrase in text
        matching_terms: Number of query terms that matched
        text_length: Length of original verse text
    
    Returns:
        Relevance score (higher is better)
    """
    score = 0.0
    
    # 1. Exact phrase match bonus
    if exact_match:
        score += 10.0
        # Count how many times the exact phrase appears
        score += text_lower.count(query_lower) * 2.0
    
    # 2. Exact word boundary match (for names like "Zuriel")
    # This catches single words that match exactly, not as substrings
    query_words = query_lower.split()
    if len(query_words) == 1:
        word_pattern = r'\b' + re.escape(query_lower) + r'\b'
        if re.search(word_pattern, text_lower):
            score += 15.0  # High bonus for exact word match (biblical names)
    
    # 3. Individual term frequency
    for term in query_terms:
        score += text_lower.count(term) * 1.5
        # Bonus for whole word matches
        word_pattern = r'\b' + re.escape(term) + r'\b'
        if re.search(word_pattern, text_lower):
            score += 3.0
    
    # 4. Term coverage (what % of query terms matched)
    coverage = matching_terms / len(query_terms)
    score += coverage * 5.0
    
    # 5. Position bonus (earlier matches score higher)
    if exact_match:
        position = text_lower.find(query_lower)
        # Bonus if match is in first 50 characters
        if position < 50:
            score += 3.0 - (position / 50 * 2.0)
    
    # 6. Verse length penalty (prefer concise matches)
    length_penalty = text_length / 500
    score -= length_penalty
    
    return score


def search_by_reference(verses: List[Dict], book: str, chapter: int, verse: int = None) -> List[Dict]:
    """
    Search for verses by biblical reference.
    
    Args:
        verses: List of verse dictionaries
        book: Book name (e.g., "Genesis", "John")
        chapter: Chapter number
        verse: Optional specific verse number
    
    Returns:
        List of matching verses
    """
    book_lower = book.lower()
    
    if verse is not None:
        # Return specific verse
        return [
            v for v in verses
            if v["book"].lower() == book_lower 
            and v["chapter"] == chapter 
            and v["verse"] == verse
        ]
    else:
        # Return entire chapter
        return [
            v for v in verses
            if v["book"].lower() == book_lower 
            and v["chapter"] == chapter
        ]
