"""
Bible Query System - Backend API
FastAPI service for keyword search across KJV verses.
"""

import json
import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re

app = FastAPI(title="Bible Query API", version="1.0.0")

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory verse storage
verses = []


class SearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = 10


class Verse(BaseModel):
    book: str
    chapter: int
    verse: int
    text: str
    reference: str
    relevance_score: Optional[float] = None


@app.on_event("startup")
async def load_verses():
    """Load KJV verses into memory on startup."""
    global verses
    print("Loading KJV verses...")
    
    try:
        # Try current directory first, then parent directory
        data_file = "kjv_chunks.jsonl"
        if not os.path.exists(data_file):
            data_file = "../kjv_chunks.jsonl"
        
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
        
        print(f"OK: Loaded {len(verses)} verses")
    except Exception as e:
        print(f"Error loading verses: {e}")
        raise


def search_verses(query: str, max_results: int = 10) -> List[dict]:
    """
    Perform simple keyword search across verse text.
    Returns verses containing query terms, ranked by relevance.
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
            # Improved relevance scoring
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
            length_penalty = len(verse["text"]) / 500
            score -= length_penalty
            
            results.append({
                **verse,
                "relevance_score": round(score, 2)
            })
    
    # Sort by relevance score (highest first)
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return results[:max_results]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Bible Query API",
        "status": "running",
        "verses_loaded": len(verses)
    }


@app.post("/search", response_model=List[Verse])
async def search(request: SearchRequest):
    """
    Search for verses matching the query.
    
    Args:
        query: Search terms or phrase
        max_results: Maximum number of results to return (default: 10)
    
    Returns:
        List of matching verses with relevance scores
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    results = search_verses(request.query, request.max_results)
    
    return results


@app.get("/stats")
async def stats():
    """Get system statistics."""
    return {
        "total_verses": len(verses),
        "books": len(set(v["book"] for v in verses)),
        "ready": len(verses) > 0
    }


@app.get("/chapter/{book}/{chapter}", response_model=List[Verse])
async def get_chapter(book: str, chapter: int):
    """
    Get all verses from a specific chapter.
    
    Args:
        book: Book name (e.g., "Genesis", "John")
        chapter: Chapter number
    
    Returns:
        List of all verses in the chapter
    """
    chapter_verses = [
        v for v in verses 
        if v["book"].lower() == book.lower() and v["chapter"] == chapter
    ]
    
    if not chapter_verses:
        raise HTTPException(status_code=404, detail=f"Chapter not found: {book} {chapter}")
    
    return chapter_verses


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
