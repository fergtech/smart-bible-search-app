"""
Bible Query System - Backend API
Modular FastAPI service for keyword and semantic search across KJV verses.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
import data_loader
import search_keyword
import search_semantic
import explain
import commentary_summarizer
import logger as structured_logger

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get structured logger instance
app_logger = structured_logger.get_logger()

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


class CommentaryRequest(BaseModel):
    query: str
    max_results: Optional[int] = 10
    use_cache: Optional[bool] = True


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
    import time
    start_time = time.time()
    
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        results = search_keyword.search_keyword(
            verses, 
            request.query, 
            request.max_results
        )
        
        # Log the search request
        response_time = time.time() - start_time
        app_logger.log_search(
            query=request.query,
            query_type='keyword',
            module='search_keyword',
            verses_retrieved=results,
            response_time=response_time,
            status='success'
        )
        
        return results
        
    except Exception as e:
        response_time = time.time() - start_time
        app_logger.log_error(
            error_type='search_error',
            error_message=str(e),
            context={'query': request.query, 'module': 'search_keyword'}
        )
        raise


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
    import time
    start_time = time.time()
    
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
        
        # Log the search request
        response_time = time.time() - start_time
        app_logger.log_search(
            query=request.query,
            query_type='semantic',
            module='search_semantic',
            verses_retrieved=results,
            response_time=response_time,
            status='success'
        )
        
        return results
        
    except Exception as e:
        response_time = time.time() - start_time
        app_logger.log_error(
            error_type='semantic_search_error',
            error_message=str(e),
            context={'query': request.query, 'module': 'search_semantic'}
        )
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
    import time
    start_time = time.time()
    
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
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
        
        # Log the explain request
        response_time = time.time() - start_time
        app_logger.log_explain(
            verse_reference=f"{len(results)} verses for '{request.query}'",
            explanation=explanation,
            response_time=response_time,
            status='success'
        )
        
        return {
            "query": request.query,
            "search_type": "semantic" if request.semantic else "keyword",
            "total_results": len(results),
            "explanation": explanation,
            "verses": results[:request.max_verses]
        }
        
    except Exception as e:
        response_time = time.time() - start_time
        app_logger.log_error(
            error_type='explain_error',
            error_message=str(e),
            context={'query': request.query, 'module': 'explain'}
        )
        raise


@app.post("/commentary")
async def generate_commentary(request: CommentaryRequest):
    """
    Generate AI-powered commentary from semantic search results.
    
    Uses GPU-accelerated language model (FLAN-T5-large) to synthesize 
    top search results into a natural language commentary.
    
    Args:
        query: User's question or search query
        max_results: Number of verses to use for commentary (default: 10)
        use_cache: Whether to use cached results (default: true)
    
    Returns:
        Commentary text, verses used, and model metadata
    """
    import time
    start_time = time.time()
    
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
        # Get top verses via semantic search
        logger.info(f"Commentary request: {request.query}")
        
        results = search_semantic.search_semantic(
            verses,
            request.query,
            request.max_results,
            min_similarity=0.3  # Filter low-quality matches
        )
        
        if not results:
            response_time = time.time() - start_time
            app_logger.log_commentary(
                query=request.query,
                verses_used=[],
                commentary="No relevant verses found for this query.",
                commentary_mode='missing',
                response_time=response_time,
                status='no_results'
            )
            
            return {
                "query": request.query,
                "commentary": "No relevant verses found for this query.",
                "verses": [],
                "metadata": {"verses_used": 0}
            }
        
        # Generate commentary
        commentary_result = commentary_summarizer.generate_commentary(
            query=request.query,
            verses=results,
            use_cache=request.use_cache
        )
        
        response_time = time.time() - start_time
        
        # Log the commentary request with structured logger
        app_logger.log_commentary(
            query=request.query,
            verses_used=results[:10],
            commentary=commentary_result['commentary'],
            commentary_mode=commentary_result.get('commentary_mode', 'full'),
            response_time=response_time,
            model_info=commentary_result.get('model_info', {}),
            status='success'
        )
        
        return {
            "query": request.query,
            "commentary": commentary_result['commentary'],
            "commentary_mode": commentary_result.get('commentary_mode', 'full'),
            "verses": results[:10],
            "metadata": {
                "verses_used": commentary_result['verses_used'],
                "model_info": commentary_result.get('model_info'),
                "total_results": len(results)
            }
        }
        
    except Exception as e:
        response_time = time.time() - start_time
        logger.error(f"Commentary generation error: {e}")
        
        app_logger.log_error(
            error_type='commentary_error',
            error_message=str(e),
            context={'query': request.query, 'module': 'commentary_summarizer'}
        )
        
        raise HTTPException(
            status_code=500, 
            detail=f"Commentary generation failed: {str(e)}"
        )


@app.get("/commentary/status")
async def commentary_status():
    """Get commentary model status and GPU info"""
    try:
        status = commentary_summarizer.get_model_status()
        return status
    except Exception as e:
        return {
            "model_loaded": False,
            "error": str(e)
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
    import time
    start_time = time.time()
    
    try:
        chapter_verses = search_keyword.search_by_reference(verses, book, chapter)
        
        if not chapter_verses:
            raise HTTPException(
                status_code=404, 
                detail=f"Chapter not found: {book} {chapter}"
            )
        
        response_time = time.time() - start_time
        app_logger.log_chapter(
            book=book,
            chapter=chapter,
            verses_count=len(chapter_verses),
            response_time=response_time,
            status='success'
        )
        
        return chapter_verses
        
    except HTTPException:
        raise
    except Exception as e:
        response_time = time.time() - start_time
        app_logger.log_error(
            error_type='chapter_error',
            error_message=str(e),
            context={'book': book, 'chapter': chapter}
        )
        raise


# Frontend logging endpoint
class FrontendLogRequest(BaseModel):
    action: str
    context: dict
    session_id: Optional[str] = None


@app.post("/log")
async def log_frontend_action(request: FrontendLogRequest):
    """
    Log frontend user actions for analytics.
    
    Args:
        action: Action type (e.g., 'search_submitted', 'commentary_displayed')
        context: Additional context data
        session_id: Optional session identifier
    
    Returns:
        Status confirmation
    """
    try:
        app_logger.log_frontend_action(
            action=request.action,
            context=request.context,
            session_id=request.session_id
        )
        return {"status": "logged"}
    except Exception as e:
        logger.error(f"Frontend logging error: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=config.API_HOST, 
        port=config.API_PORT
    )
