"""
Natural language explanation synthesis.
Generates simple, clear explanations from search results.
"""

from typing import List, Dict


def explain_results(verses: List[Dict], query: str, max_verses: int = 5) -> str:
    """
    Generate a natural language explanation from search results.
    
    Args:
        verses: List of verse dictionaries with relevance scores
        query: Original search query
        max_verses: Maximum number of verses to include in explanation
    
    Returns:
        Natural language explanation string
    """
    if not verses:
        return f"No verses were found matching '{query}'."
    
    # Limit to top results
    top_verses = verses[:max_verses]
    
    # Build explanation
    explanation_parts = []
    
    # Introduction
    if len(verses) == 1:
        explanation_parts.append(f"I found 1 verse related to '{query}':")
    else:
        explanation_parts.append(
            f"I found {len(verses)} verses related to '{query}'. "
            f"Here are the top {len(top_verses)} most relevant:"
        )
    
    explanation_parts.append("")
    
    # Add verses with context
    for i, verse in enumerate(top_verses, 1):
        ref = verse["reference"]
        text = verse["text"]
        score = verse.get("relevance_score", 0)
        
        # Format verse entry
        verse_entry = f"{i}. **{ref}** (score: {score})\n   \"{text}\""
        explanation_parts.append(verse_entry)
        explanation_parts.append("")
    
    # Summary insight (optional)
    if len(top_verses) > 1:
        books = set(v["book"] for v in top_verses)
        if len(books) == 1:
            explanation_parts.append(f"All results are from {list(books)[0]}.")
        else:
            explanation_parts.append(
                f"Results span {len(books)} books: {', '.join(sorted(books))}."
            )
    
    return "\n".join(explanation_parts)


def explain_semantic_results(verses: List[Dict], query: str, max_verses: int = 5) -> str:
    """
    Generate explanation for semantic search results with similarity scores.
    
    Args:
        verses: List of verse dictionaries with similarity scores
        query: Original natural language query
        max_verses: Maximum number of verses to include
    
    Returns:
        Natural language explanation string
    """
    if not verses:
        return f"No verses were found semantically similar to: '{query}'."
    
    # Limit to top results
    top_verses = verses[:max_verses]
    
    # Build explanation
    explanation_parts = []
    
    # Introduction
    explanation_parts.append(
        f"Based on semantic similarity to '{query}', "
        f"I found {len(verses)} relevant verses. "
        f"Here are the top {len(top_verses)}:"
    )
    explanation_parts.append("")
    
    # Add verses with similarity context
    for i, verse in enumerate(top_verses, 1):
        ref = verse["reference"]
        text = verse["text"]
        similarity = verse.get("relevance_score", 0)
        
        # Interpret similarity score
        if similarity > 0.7:
            relevance = "highly relevant"
        elif similarity > 0.5:
            relevance = "very relevant"
        elif similarity > 0.3:
            relevance = "relevant"
        else:
            relevance = "somewhat relevant"
        
        # Format verse entry
        verse_entry = (
            f"{i}. **{ref}** ({relevance}, similarity: {similarity:.3f})\n"
            f"   \"{text}\""
        )
        explanation_parts.append(verse_entry)
        explanation_parts.append("")
    
    # Thematic summary
    if len(top_verses) >= 3:
        # Simple thematic analysis
        common_words = _extract_common_themes(top_verses, query)
        if common_words:
            explanation_parts.append(
                f"Common themes: {', '.join(common_words[:5])}."
            )
    
    return "\n".join(explanation_parts)


def _extract_common_themes(verses: List[Dict], query: str, min_frequency: int = 2) -> List[str]:
    """
    Extract common words/themes from verse texts.
    
    Args:
        verses: List of verse dictionaries
        query: Original query (words to exclude from themes)
        min_frequency: Minimum times a word must appear
    
    Returns:
        List of common words, sorted by frequency
    """
    import re
    from collections import Counter
    
    # Stop words to exclude
    stop_words = {
        'the', 'and', 'of', 'to', 'a', 'in', 'that', 'is', 'was', 'for',
        'with', 'as', 'his', 'he', 'be', 'not', 'by', 'but', 'from', 'they',
        'which', 'this', 'or', 'an', 'had', 'on', 'are', 'were', 'their',
        'have', 'you', 'shall', 'it', 'at', 'unto', 'thy', 'thee', 'him',
        'said', 'all', 'will', 'them', 'there', 'when', 'so', 'what'
    }
    
    # Add query words to stop words
    query_words = set(re.findall(r'\w+', query.lower()))
    stop_words.update(query_words)
    
    # Extract and count words
    word_counts = Counter()
    for verse in verses:
        words = re.findall(r'\w+', verse["text"].lower())
        # Only count significant words (length >= 4)
        significant_words = [
            w for w in words 
            if len(w) >= 4 and w not in stop_words
        ]
        word_counts.update(significant_words)
    
    # Return words that appear at least min_frequency times
    common = [
        word for word, count in word_counts.most_common()
        if count >= min_frequency
    ]
    
    return common[:10]  # Top 10 themes
