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
import search_hybrid
import explain
import commentary_summarizer_openai as commentary_summarizer
import crisis_detection
import reference_lookup
import lexicon_lookup
import grounding_check
import memory_store
import logger as structured_logger
import search_commentary_corpus
import search_concept_documents

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


class ApproveMemoryRequest(BaseModel):
    memory_id: str


class SessionTitleRequest(BaseModel):
    query: str


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


@app.post("/hybrid_search", response_model=List[Verse])
async def hybrid_search(request: SemanticSearchRequest):
    """
    Merged keyword + semantic search (see search_hybrid.py).

    Replaces the frontend's old all-or-nothing logic, which used keyword
    results outright whenever any verse scored above 0.3, hiding semantic
    results even when they were clearly the better match (confirmed:
    "fruits of the spirit" never surfaced Galatians 5:22 under that logic,
    because the KJV's singular "fruit of the Spirit" doesn't word-match the
    plural query, and other spirit-related verses "won" via keyword mode
    before semantic search ever got a chance).

    Also applies the same exact-reference guarantee and meta-question
    rewriting /commentary uses (see reference_lookup.py), so the results
    list and the commentary panel converge on the same answer for the same
    query without needing to couple the two calls together - confirmed
    live that without this, "give me the exact text of John 14:27" showed
    a clean verbatim answer in the commentary panel while the results list
    below it showed 20 unrelated verses, and "what does John 3:16 mean"
    didn't even surface John 3:16 in its own results list.
    """
    import time
    start_time = time.time()

    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    embedding_stats = search_semantic.get_embedding_stats()
    if not embedding_stats['index_exists']:
        raise HTTPException(
            status_code=503,
            detail="Semantic search not available. Run generate_embeddings.py first."
        )

    try:
        book_names = reference_lookup.get_book_names(verses)
        ref = reference_lookup.extract_reference(request.query, book_names)
        exact_verses = reference_lookup.lookup_reference(verses, ref) if ref else []

        search_query = reference_lookup.extract_topic_for_search(request.query)
        results = search_hybrid.hybrid_search(verses, search_query, request.max_results)

        if exact_verses:
            existing_keys = {(v['book'], v['chapter'], v['verse']) for v in exact_verses}
            results = exact_verses + [
                r for r in results
                if (r['book'], r['chapter'], r['verse']) not in existing_keys
            ]
            results = results[:request.max_results]

        response_time = time.time() - start_time
        app_logger.log_search(
            query=request.query,
            query_type='hybrid',
            module='search_hybrid',
            verses_retrieved=results,
            response_time=response_time,
            status='success'
        )

        return results

    except Exception as e:
        response_time = time.time() - start_time
        app_logger.log_error(
            error_type='hybrid_search_error',
            error_message=str(e),
            context={'query': request.query, 'module': 'search_hybrid'}
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

    # CRISIS CHECK: runs before any retrieval or LLM call, so a crisis
    # resource is guaranteed regardless of what verses would have matched
    # or how a model would have responded. See crisis_detection.py.
    if crisis_detection.detect_crisis(request.query):
        response_time = time.time() - start_time
        crisis_response = crisis_detection.build_crisis_response(request.query)

        logger.warning(f"Crisis language detected in commentary request")
        app_logger.log_event('crisis_detected', {
            'query': request.query,
            'response_time': response_time,
        })

        return {
            "query": request.query,
            "commentary": crisis_response['commentary'],
            "commentary_mode": crisis_response['commentary_mode'],
            "verses": crisis_response['verses'],
            "metadata": {
                "verses_used": crisis_response['verses_used'],
                "model_info": crisis_response['model_info'],
                "total_results": len(crisis_response['verses'])
            }
        }

    # EXACT REFERENCE CHECK: if the query names a specific book:chapter:verse,
    # look it up directly rather than relying on semantic search, which is
    # the wrong tool for a deterministic reference lookup (confirmed: "give
    # me the exact text of John 14:27" failed retrieval entirely despite the
    # word-perfect verse being stored and instantly retrievable via
    # /chapter). See reference_lookup.py.
    book_names = reference_lookup.get_book_names(verses)
    ref = reference_lookup.extract_reference(request.query, book_names)
    exact_verses = reference_lookup.lookup_reference(verses, ref) if ref else []

    if exact_verses and reference_lookup.wants_exact_text(request.query):
        response_time = time.time() - start_time
        if len(exact_verses) == 1:
            commentary = f"{exact_verses[0]['reference']}: \"{exact_verses[0]['text']}\""
        else:
            commentary = "\n".join(f"{v['reference']}: \"{v['text']}\"" for v in exact_verses)

        app_logger.log_commentary(
            query=request.query,
            verses_used=exact_verses,
            commentary=commentary,
            commentary_mode='exact_reference',
            response_time=response_time,
            model_info={'source': 'direct_lookup', 'model': None},
            status='success'
        )

        return {
            "query": request.query,
            "commentary": commentary,
            "commentary_mode": "exact_reference",
            "verses": exact_verses,
            "metadata": {
                "verses_used": len(exact_verses),
                "model_info": {'source': 'direct_lookup', 'model': None},
                "total_results": len(exact_verses)
            }
        }

    # Check if semantic search is available
    embedding_stats = search_semantic.get_embedding_stats()
    if not embedding_stats['index_exists']:
        raise HTTPException(
            status_code=503,
            detail="Semantic search not available. Run generate_embeddings.py first."
        )

    try:
        # COMMENTARY SEARCH STRATEGY:
        # Use broad semantic search to find ALL potentially relevant verses
        # No arbitrary "top N" limit - use relevance threshold instead
        # AI reads everything above threshold to find the actual answer

        logger.info(f"Commentary request: {request.query}")

        # Meta-questions like "where does Paul discuss the armor of God"
        # embed toward the named person, not the actual topic, and can miss
        # the passage entirely (confirmed: this exact query failed to
        # retrieve Ephesians 6 even though "armor of God" alone finds it at
        # 0.62 similarity). Strip that framing for the embedding call only -
        # the LLM prompt still sees the user's original question.
        search_query = reference_lookup.extract_topic_for_search(request.query)

        # Cast wide net: semantic search with low threshold, high limit
        # This ensures we don't miss verses like Luke 3:23 that might rank #147
        # but contain the exact answer to "jesus age"
        results = search_semantic.search_semantic(
            verses,
            search_query,
            max_results=500,  # High limit to capture everything relevant
            min_similarity=0.12  # Low threshold to cast wide net
        )

        # If the query named a specific verse but wasn't asking for the
        # literal text (e.g. "what does John 3:16 mean"), guarantee that
        # verse is present for the commentary LLM instead of leaving it to
        # semantic search chance.
        if exact_verses:
            existing_keys = {(v['book'], v['chapter'], v['verse']) for v in exact_verses}
            results = exact_verses + [
                r for r in results
                if (r['book'], r['chapter'], r['verse']) not in existing_keys
            ]

        logger.info(
            f"Commentary semantic search: {len(results)} verses above 0.12 similarity "
            f"(search query: '{search_query}')"
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

        # Record the memory-search outcome BEFORE this query is itself
        # stored below (otherwise it would just match itself). This is the
        # concrete data a later concept-document pass reads to find
        # recurring topics that keep landing near, but under, the match
        # threshold - seeing this logged was the whole point of adding
        # get_best_match_debug(), not just theorizing about it.
        memory_debug = memory_store.get_best_match_debug(request.query)
        app_logger.log_event('memory_search', {
            'query': request.query,
            'best_match_query': memory_debug['query'] if memory_debug else None,
            'similarity': memory_debug['similarity'] if memory_debug else None,
            'matched': memory_debug['matched'] if memory_debug else False,
        })

        # MEMORY: classify the query, run the deterministic grounding check,
        # and store the answer. Factual answers that pass grounding are
        # promoted automatically; interpretive answers are stored pending a
        # human thumbs-up via /commentary/approve (see memory_store.py for
        # why these two gates are different - there's no automated way to
        # verify a theological interpretation the way there is a citation).
        complexity = commentary_summarizer.assess_query_complexity(request.query, results)
        grounding = grounding_check.check_grounding(
            commentary_result['commentary'], results[:10], book_names
        )
        memory_entry = memory_store.add_entry(
            query=request.query,
            commentary=commentary_result['commentary'],
            verses_used=results[:10],
            query_type=complexity['query_type'],
            grounded=grounding['grounded'],
            model_info=commentary_result.get('model_info'),
        )

        return {
            "query": request.query,
            "commentary": commentary_result['commentary'],
            "commentary_mode": commentary_result.get('commentary_mode', 'full'),
            "verses": results[:10],
            "metadata": {
                "verses_used": commentary_result['verses_used'],
                "model_info": commentary_result.get('model_info'),
                "total_results": len(results),
                "memory_id": memory_entry['id'],
                "query_type": complexity['query_type'],
                "grounded": grounding['grounded'],
                "pending_review": complexity['query_type'] == 'interpretive' and not memory_entry['promoted']
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


@app.post("/commentary/approve")
async def approve_commentary(request: ApproveMemoryRequest):
    """
    Human thumbs-up on an interpretive commentary answer, promoting it into
    reusable memory (see memory_store.py). This is the ONLY way an
    interpretive/theological answer becomes eligible to be surfaced as
    prior-discussion context for future similar questions - there's no
    automated confidence score for theological soundness, so a real human
    judgment call is the gate.
    """
    entry = memory_store.approve_entry(request.memory_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Memory entry not found: {request.memory_id}")

    app_logger.log_event('memory_approved', {'memory_id': request.memory_id})

    return {"memory_id": entry['id'], "promoted": entry['promoted']}


@app.post("/session/title")
async def session_title(request: SessionTitleRequest):
    """
    Short auto-generated title for a history entry, called once after a
    session's first exchange (see history.js). Never blocks the commentary
    response itself - the frontend fires this separately and patches the
    title in afterward.
    """
    title = commentary_summarizer.generate_session_title(request.query)
    return {"title": title}


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


# Cached lazily on first /books request - the canonical book/chapter-count
# list is static for the life of the process, same reasoning as
# reference_lookup's own cached book-names list.
_book_list_cache: Optional[List[dict]] = None


@app.get("/books")
async def get_books():
    """
    Canonical-order (Genesis...Revelation) book list with chapter counts and
    testament, for Bible Reading Mode's navigation sidebar.
    """
    global _book_list_cache
    if _book_list_cache is None:
        _book_list_cache = data_loader.get_book_list(verses)
    return _book_list_cache


def _get_chapter_or_404(book: str, chapter: int) -> List[dict]:
    """Shared by /chapter and /chapter/.../study so the two routes can't
    drift on what counts as a valid chapter."""
    chapter_verses = search_keyword.search_by_reference(verses, book, chapter)
    if not chapter_verses:
        raise HTTPException(status_code=404, detail=f"Chapter not found: {book} {chapter}")
    return chapter_verses


@app.get("/chapter/{book}/{chapter}/study")
async def get_chapter_study(book: str, chapter: int):
    """
    Study Tools for Bible Reading Mode's right rail: Strong's word studies
    plus related commentary/concept excerpts for a whole chapter. No LLM
    call anywhere in this path - word studies are a local lookup, and the
    corpus searches are the same free semantic search the /commentary
    pipeline uses internally, just called directly here.
    """
    chapter_verses = _get_chapter_or_404(book, chapter)

    word_studies = lexicon_lookup.get_word_studies(chapter_verses, max_terms=8)

    query = " ".join(v["text"] for v in chapter_verses)
    commentary = search_commentary_corpus.search_commentary_corpus(query, max_results=3, min_similarity=0.58)
    concepts = search_concept_documents.search_concepts(query, max_results=2, min_similarity=0.45)

    return {
        "word_studies": word_studies,
        "commentary": commentary,
        "concepts": concepts
    }


@app.get("/strongs/{number}")
async def get_strongs_definition(number: str):
    """
    Look up a Strong's number directly (e.g. "G25", "H2580") for the
    clickable Strong's number feature in the commentary panel - a plain
    forward lookup, unrelated to lexicon_lookup.py's English-word reverse
    index used during commentary generation.
    """
    definition = lexicon_lookup.get_definition(number)
    if definition is None:
        raise HTTPException(status_code=404, detail=f"Strong's number not found: {number}")
    return definition


@app.get("/blessing")
async def get_blessing():
    """
    'I'm Feeling Blessed' - previously a button with no handler at all
    anywhere in the frontend JS. Picks a random verse and generates a
    short reflection + prayer (see commentary_summarizer.generate_blessing).
    """
    import random
    verse = random.choice(verses)
    blessing = commentary_summarizer.generate_blessing(verse)
    return {
        'reference': verse['reference'],
        'text': verse['text'],
        'reflection': blessing['reflection'],
        'prayer': blessing['prayer'],
    }


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
