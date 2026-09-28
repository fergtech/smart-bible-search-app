"""
Data loading utilities for Bible Query System.
Handles loading verses and lexicon metadata.
"""

import json
import os
from typing import List, Dict, Optional
from pathlib import Path
import config


def load_verses(data_file: Optional[str] = None) -> List[Dict]:
    """
    Load KJV verses from JSONL file.
    
    Args:
        data_file: Path to JSONL file (defaults to config.KJV_CHUNKS_FILE)
    
    Returns:
        List of verse dictionaries with keys: book, chapter, verse, text, reference
    """
    if data_file is None:
        data_file = config.KJV_CHUNKS_FILE
    
    verses = []
    
    # Try current directory first, then parent directory
    if not os.path.exists(data_file):
        data_file = f"../{data_file}"
    
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"KJV data file not found: {data_file}")
    
    print(f"Loading verses from {data_file}...")
    
    with open(data_file, "r", encoding="utf-8") as f:
        for line in f:
            verse_data = json.loads(line.strip())
            # Create a reference string for display
            reference = f"{verse_data['book']} {verse_data['chapter']}:{verse_data['verse']}"
            verses.append({
                "book": verse_data["book"],
                "chapter": verse_data["chapter"],
                "verse": verse_data["verse"],
                "text": verse_data["text"],
                "reference": reference
            })
    
    print(f"OK: Loaded {len(verses)} verses from {len(set(v['book'] for v in verses))} books")
    
    # Validate against canonical counts
    if len(verses) != config.CANONICAL_VERSE_COUNT:
        print(f"WARNING: Expected {config.CANONICAL_VERSE_COUNT} verses, got {len(verses)}")
    
    return verses


def load_lexicon_metadata(data_file: Optional[str] = None) -> Dict:
    """
    Load lexicon metadata (Strong's numbers, definitions, etc.).
    
    Args:
        data_file: Path to JSON file (defaults to config.LEXICON_METADATA_FILE)
    
    Returns:
        Dictionary of lexicon entries
    """
    if data_file is None:
        data_file = config.LEXICON_METADATA_FILE
    
    # Try current directory first, then parent directory
    if not os.path.exists(data_file):
        data_file = f"../{data_file}"
    
    if not os.path.exists(data_file):
        print(f"INFO: Lexicon metadata file not found: {data_file}")
        return {}
    
    print(f"Loading lexicon metadata from {data_file}...")
    
    with open(data_file, "r", encoding="utf-8") as f:
        lexicon = json.load(f)
    
    print(f"OK: Loaded {len(lexicon)} lexicon entries")
    
    return lexicon


def get_book_list(verses: List[Dict]) -> List[Dict]:
    """
    Canonical-order book list (Genesis...Revelation) with a per-book chapter
    count and testament, for Bible Reading Mode's navigation sidebar.

    Deliberately NOT reusing reference_lookup.get_book_names() (sorted by
    name length, for regex matching - wrong order for display) or this
    file's own get_verse_stats() (alphabetical). The in-memory verses list
    is already in true canonical order as loaded from kjv_chunks.jsonl, so
    first-appearance order over it is the canonical order for free.
    """
    from lexicon_lookup import _NT_BOOKS

    order = []
    seen = set()
    chapters_by_book = {}
    for v in verses:
        book = v["book"]
        if book not in seen:
            seen.add(book)
            order.append(book)
        chapters_by_book.setdefault(book, set()).add(v["chapter"])

    return [
        {
            "name": book,
            "chapter_count": len(chapters_by_book[book]),
            "testament": "NT" if book in _NT_BOOKS else "OT"
        }
        for book in order
    ]


def get_verse_stats(verses: List[Dict]) -> Dict:
    """
    Calculate statistics about the verse collection.
    
    Args:
        verses: List of verse dictionaries
    
    Returns:
        Dictionary with stats: total_verses, books, chapters, etc.
    """
    books = set(v["book"] for v in verses)
    chapters = set((v["book"], v["chapter"]) for v in verses)
    
    return {
        "total_verses": len(verses),
        "total_books": len(books),
        "total_chapters": len(chapters),
        "books": sorted(books),
        "canonical_verse_count": config.CANONICAL_VERSE_COUNT,
        "canonical_book_count": config.CANONICAL_BOOK_COUNT,
        "is_complete": len(verses) == config.CANONICAL_VERSE_COUNT
    }
