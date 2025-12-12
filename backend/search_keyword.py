"""
Keyword-based search for Bible verses.
Implements traditional text matching with relevance scoring.
"""

import re
from typing import List, Dict


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
    query_terms = re.findall(r'\w+', query_lower)
    
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
            
            results.append({
                **verse,
                "relevance_score": round(score, 2)
            })
    
    # Sort by relevance score (highest first)
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    
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
    
    # 2. Individual term frequency
    for term in query_terms:
        score += text_lower.count(term) * 1.5
    
    # 3. Term coverage (what % of query terms matched)
    coverage = matching_terms / len(query_terms)
    score += coverage * 5.0
    
    # 4. Position bonus (earlier matches score higher)
    if exact_match:
        position = text_lower.find(query_lower)
        # Bonus if match is in first 50 characters
        if position < 50:
            score += 3.0 - (position / 50 * 2.0)
    
    # 5. Verse length penalty (prefer concise matches)
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
