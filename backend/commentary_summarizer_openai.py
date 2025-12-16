"""
Commentary Summarizer - Ollama (FREE Local LLM)
Generates concise, natural language commentary from search results.

Uses Ollama for completely FREE, local text generation.
Cost: $0 (FREE!)
Speed: 2-5 seconds (local)
Setup: Install Ollama from https://ollama.ai
"""

import os
import json
import hashlib
import requests
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")  # User's installed model


def _check_ollama_available() -> bool:
    """Check if Ollama service is running"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False


def _ensure_model_pulled(model: str) -> bool:
    """Check if model is available, if not provide helpful error"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            available = any(m['name'].startswith(model.split(':')[0]) for m in models)
            if not available:
                logger.warning(f"Model {model} not found. Run: ollama pull {model}")
            return available
        return False
    except Exception as e:
        logger.error(f"Error checking Ollama models: {e}")
        return False


def _create_cache_key(query: str, verse_ids: List[str]) -> str:
    """Create cache key from query and verse IDs"""
    content = f"{query}|{'|'.join(sorted(verse_ids))}"
    return hashlib.md5(content.encode()).hexdigest()


def _load_cache(cache_key: str, cache_dir: Path) -> Optional[str]:
    """Load cached commentary if available"""
    cache_file = cache_dir / f"{cache_key}.json"
    
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Cache hit: {data.get('query', 'unknown')}")
                return data.get('commentary')
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
    
    return None


def _save_cache(cache_key: str, query: str, commentary: str, cache_dir: Path):
    """Save commentary to cache"""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{cache_key}.json"
    
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                'query': query,
                'commentary': commentary,
                'cached_at': str(Path(__file__).stat().st_mtime)
            }, f, indent=2)
        logger.info(f"Cached commentary: {query}")
    except Exception as e:
        logger.warning(f"Cache write error: {e}")


def _build_prompt(query: str, verses: List[Dict]) -> str:
    """Build prompt for Ollama"""
    
    # Format verses concisely (top 5 only)
    verse_list = []
    for v in verses[:5]:
        verse_list.append(f"{v['reference']}: \"{v['text']}\"")
    
    verse_context = "\n".join(verse_list)
    
    # Detect simple factual questions
    query_lower = query.lower().strip()
    question_words = ['who', 'what', 'when', 'where', 'which', 'name', 'how many']
    is_simple_question = any(word in query_lower for word in question_words)
    
    # Build concise prompt
    if is_simple_question:
        prompt = f"""You are a helpful Bible assistant. Answer this question in 1-2 sentences.

Question: {query}

Bible verses:
{verse_context}

Give a direct, natural answer. Include the verse reference."""
    else:
        prompt = f"""You are a helpful Bible assistant. Explain what the Bible teaches in 3-5 sentences max.

Topic: {query}

Bible verses:
{verse_context}

Be conversational and mention key verses naturally."""
    
    return prompt


def generate_commentary(
    query: str,
    verses: List[Dict],
    cache_dir: Optional[Path] = None,
    use_cache: bool = True,
    model: str = None
) -> Dict:
    """
    Generate natural language commentary using Ollama (FREE local LLM).
    
    Args:
        query: User's search query
        verses: List of verse dicts with 'reference', 'text', 'relevance_score'
        cache_dir: Directory for caching results
        use_cache: Whether to use cached results
        model: Ollama model to use (default: llama3.2:3b)
    
    Returns:
        Dict with 'commentary', 'verses_used', 'model_info'
    """
    
    if not verses:
        return {
            'commentary': "No verses found to generate commentary.",
            'verses_used': 0,
            'model_info': None
        }
    
    # Use configured model or default
    if model is None:
        model = OLLAMA_MODEL
    
    # Setup cache
    if cache_dir is None:
        cache_dir = Path(__file__).parent.parent / "cache" / "commentary"
    
    # Check cache
    verse_ids = [v['reference'] for v in verses[:10]]
    cache_key = _create_cache_key(query, verse_ids)
    
    if use_cache:
        cached = _load_cache(cache_key, cache_dir)
        if cached:
            return {
                'commentary': cached,
                'verses_used': len(verse_ids),
                'model_info': {'source': 'cache', 'model': model}
            }
    
    # Check if Ollama is available
    if not _check_ollama_available():
        logger.error("Ollama not running. Install from https://ollama.ai and run: ollama serve")
        return {
            'commentary': (
                "Commentary unavailable - Ollama not running. "
                f"See {verses[0]['reference']} for relevant passages."
            ),
            'verses_used': len(verse_ids),
            'model_info': {'source': 'fallback', 'error': 'Ollama not available'}
        }
    
    try:
        # Build prompt
        prompt = _build_prompt(query, verses)
        
        logger.info(f"Generating commentary: {query}")
        
        # Call Ollama API
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.5,
                    "top_p": 0.9,
                    "num_predict": 150,  # Max tokens
                    "stop": ["\n\n", "Question:", "Topic:"]  # Stop at these
                }
            },
            timeout=120  # Increased for large models like gpt-oss:20b
        )
        
        if response.status_code != 200:
            raise Exception(f"Ollama API error: {response.status_code}")
        
        result = response.json()
        commentary = result.get('response', '').strip()
        
        # Validate
        if len(commentary) < 20:
            logger.warning(f"Commentary too short: {len(commentary)} chars")
            raise ValueError("Generated commentary too short")
        
        logger.info(f"Generated commentary: {len(commentary)} chars")
        
        # Cache result
        if use_cache:
            _save_cache(cache_key, query, commentary, cache_dir)
        
        return {
            'commentary': commentary,
            'verses_used': len(verse_ids),
            'model_info': {
                'model': model,
                'provider': 'Ollama (FREE)',
                'cost': '$0.00'
            }
        }
        
    except Exception as e:
        logger.error(f"Commentary generation error: {e}")
        
        # Fallback
        fallback = f"Commentary unavailable. See {verses[0]['reference']}"
        if len(verses) > 1:
            fallback += f", {verses[1]['reference']}"
        fallback += " for relevant passages."
        
        return {
            'commentary': fallback,
            'verses_used': len(verse_ids) if verses else 0,
            'model_info': {'source': 'fallback', 'error': str(e)}
        }


def get_model_status() -> Dict:
    """Get current Ollama status"""
    ollama_running = _check_ollama_available()
    
    status = {
        'provider': 'Ollama',
        'model': OLLAMA_MODEL,
        'ollama_running': ollama_running,
        'base_url': OLLAMA_BASE_URL,
        'cost': 'FREE'
    }
    
    if ollama_running:
        _ensure_model_pulled(OLLAMA_MODEL)
    
    return status
