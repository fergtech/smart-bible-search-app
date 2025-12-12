"""
Bible Query System - Backend API
Modular FastAPI service for keyword and semantic search across KJV verses.
"""

from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
import data_loader
import search_keyword
import search_semantic
import explain

# Initialize FastAPI
app = FastAPI(title=config.API_TITLE, version=config.API_VERSION)

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global verse storage
verses = []


# === Pydantic Models ===

class SearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = config.DEFAULT_MAX_RESULTS


class SemanticSearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = config.DEFAULT_MAX_RESULTS
    min_similarity: Optional[float] = None


class ExplainRequest(BaseModel):
    query: str
    max_results: Optional[int] = config.DEFAULT_MAX_RESULTS
    max_verses: Optional[int] = 5
    semantic: Optional[bool] = False


class Verse(BaseModel):
    book: str
    chapter: int
    verse: int
    text: str
    reference: str
    relevance_score: Optional[float] = None


# === Startup/Shutdown ===

@app.on_event("startup")
async def startup():
    """Load verses and initialize search indices on startup."""
    global verses
    print("=" * 60)
    print(f"Starting {config.API_TITLE} v{config.API_VERSION}")
    print("=" * 60)
    
    # Load verses
    verses = data_loader.load_verses()
    
    # Display stats
    stats = data_loader.get_verse_stats(verses)
    print(f"\n📊 Loaded {stats['total_verses']} verses from {stats['total_books']} books")
    print(f"   Canonical count: {stats['canonical_verse_count']} verses expected")
    print(f"   Status: {'COMPLETE' if stats['is_complete'] else 'INCOMPLETE'}")
    
    # Check for embeddings
    embedding_stats = search_semantic.get_embedding_stats()
    if embedding_stats['index_exists']:
        print(f"\n🔍 Semantic search: Enabled ({embedding_stats.get('total_vectors', 0)} embeddings)")
    else:
        print(f"\nWARNING: Semantic search: Disabled (run generate_embeddings.py to enable)")
    
    print("\n" + "=" * 60)
    print("OK: Server ready")
    print("=" * 60 + "\n")


# === API Endpoints ===

@app.get("/")
async def root():
    """Health check endpoint."""
    stats = data_loader.get_verse_stats(verses)
    embedding_stats = search_semantic.get_embedding_stats()
    
    return {
        "service": config.API_TITLE,
        "version": config.API_VERSION,
        "status": "running",
        "verses_loaded": len(verses),
        "semantic_search_enabled": embedding_stats['index_exists']
    }


@app.get("/stats")
async def get_stats():
    """Get detailed system statistics."""
    stats = data_loader.get_verse_stats(verses)
    embedding_stats = search_semantic.get_embedding_stats()
    
    return {
        **stats,
        "embedding_stats": embedding_stats
    }


@app.post("/search", response_model=List[Verse])
async def search(request: SearchRequest):
    """
    Keyword-based search for verses matching the query.
    
    Args:
        query: Search terms or phrase
        max_results: Maximum number of results to return
    
    Returns:
        List of matching verses with relevance scores
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    results = search_keyword.search_keyword(
        verses, 
        request.query, 
        request.max_results
    )
    
    return results


@app.post("/semantic_search", response_model=List[Verse])
async def semantic_search(request: SemanticSearchRequest):
    """
    Semantic search using natural language understanding.
    
    Args:
        query: Natural language query
        max_results: Maximum number of results to return
        min_similarity: Minimum similarity threshold (0-1)
    
    Returns:
        List of semantically similar verses with similarity scores
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Check if semantic search is available
    embedding_stats = search_semantic.get_embedding_stats()
    if not embedding_stats['index_exists']:
        raise HTTPException(
            status_code=503,
            detail="Semantic search not available. Run generate_embeddings.py first."
        )
    
    try:
        results = search_semantic.search_semantic(
            verses,
            request.query,
            request.max_results,
            request.min_similarity
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.post("/explain")
async def explain_search(request: ExplainRequest):
    """
    Search and generate natural language explanation of results.
    
    Args:
        query: Search query
        max_results: Maximum search results to consider
        max_verses: Maximum verses to include in explanation
        semantic: Use semantic search (default: keyword search)
    
    Returns:
        Natural language explanation with relevant verses
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Perform search
    if request.semantic:
        # Check if semantic search is available
        embedding_stats = search_semantic.get_embedding_stats()
        if not embedding_stats['index_exists']:
            raise HTTPException(
                status_code=503,
                detail="Semantic search not available. Run generate_embeddings.py first."
            )
        
        results = search_semantic.search_semantic(
            verses,
            request.query,
            request.max_results
        )
        explanation = explain.explain_semantic_results(
            results,
            request.query,
            request.max_verses
        )
    else:
        results = search_keyword.search_keyword(
            verses,
            request.query,
            request.max_results
        )
        explanation = explain.explain_results(
            results,
            request.query,
            request.max_verses
        )
    
    return {
        "query": request.query,
        "search_type": "semantic" if request.semantic else "keyword",
        "total_results": len(results),
        "explanation": explanation,
        "verses": results[:request.max_verses]
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
    chapter_verses = search_keyword.search_by_reference(verses, book, chapter)
    
    if not chapter_verses:
        raise HTTPException(
            status_code=404, 
            detail=f"Chapter not found: {book} {chapter}"
        )
    
    return chapter_verses


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=config.API_HOST, 
        port=config.API_PORT
    )
