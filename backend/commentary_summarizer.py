"""
Commentary Summarizer - GPU-accelerated Bible verse synthesis
Generates natural language commentary from semantic search results.

Model: google/flan-t5-large (780M params - optimized for 8GB VRAM)
Approach: Few-shot instruction-based generation with verse grounding
"""

import json
import hashlib
from typing import List, Dict, Optional
from pathlib import Path
import logging

# Lazy imports for optional dependencies
_model = None
_tokenizer = None
_device = None

logger = logging.getLogger(__name__)


def _get_torch():
    """Lazy import PyTorch"""
    try:
        import torch
        return torch
    except ImportError:
        raise ImportError(
            "PyTorch not installed. Run: pip install torch"
        )


def _load_model():
    """Lazy load the summarization model (GPU-accelerated)"""
    global _model, _tokenizer, _device
    
    if _model is not None:
        return _model, _tokenizer, _device
    
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        import torch
        
        model_name = "google/flan-t5-large"  # 780M params, fits in 8GB VRAM
        
        logger.info(f"Loading commentary model: {model_name}")
        
        # Check GPU availability
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {_device}")
        
        if _device == "cpu":
            logger.warning("GPU not available! Commentary generation will be slower.")
        
        # Load model with GPU optimization
        _tokenizer = AutoTokenizer.from_pretrained(model_name)
        _model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if _device == "cuda" else torch.float32,
            device_map="auto" if _device == "cuda" else None
        )
        
        if _device == "cpu":
            _model = _model.to(_device)
        
        logger.info(f"Model loaded successfully on {_device}")
        
        return _model, _tokenizer, _device
        
    except ImportError as e:
        logger.error(f"Missing dependencies: {e}")
        raise ImportError(
            "transformers not installed. Run: pip install transformers accelerate"
        )


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
                logger.info(f"Cache hit for query: {data.get('query', 'unknown')}")
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
        logger.info(f"Cached commentary for: {query}")
    except Exception as e:
        logger.warning(f"Cache write error: {e}")


def _build_prompt(query: str, verses: List[Dict]) -> str:
    """Build instruction prompt for the model"""
    
    # Check if query is nonsense/gibberish or non-biblical
    query_lower = query.lower().strip()
    
    # More comprehensive nonsense detection
    nonsense_indicators = ['asdf', 'qwerty', 'recipe', 'workout', 'crypto', 'bitcoin', 'lmnop', 'hjkl', 'fdsa']
    
    # Check for keyboard mashing patterns
    has_vowels = any(c in query_lower for c in 'aeiou')
    repeating_chars = any(query_lower.count(c) > len(query_lower) * 0.4 for c in set(query_lower) if c.isalpha())
    
    # Count consecutive consonants (gibberish often has 4+ in a row like "sdfghjkl")
    consonants = 'bcdfghjklmnpqrstvwxyz'
    max_consecutive_consonants = 0
    current_consecutive = 0
    for c in query_lower:
        if c in consonants:
            current_consecutive += 1
            max_consecutive_consonants = max(max_consecutive_consonants, current_consecutive)
        else:
            current_consecutive = 0
    
    is_likely_nonsense = (
        len(query_lower) < 2 or
        not any(c.isalpha() for c in query_lower) or
        any(indicator in query_lower for indicator in nonsense_indicators) or
        (not has_vowels and len(query_lower) > 3) or  # "bcdfgh" type gibberish
        repeating_chars or  # "aaaaaaa" or similar
        max_consecutive_consonants >= 5  # "sdfghjkl" has 8 consecutive consonants
    )
    
    # Debug logging
    logger.info(f"Query: '{query}' | Nonsense: {is_likely_nonsense} | Consonants: {max_consecutive_consonants}")
    
    # Format verses with references (limit to top 5 for clarity)
    verse_list = []
    for v in verses[:5]:
        verse_list.append(f"{v['reference']}: \"{v['text']}\"")
    
    verse_context = "\n".join(verse_list)
    
    # If likely nonsense, check relevance scores
    if is_likely_nonsense:
        avg_score = sum(v.get('relevance_score', 0) for v in verses[:5]) / min(len(verses), 5) if len(verses) > 0 else 0
        logger.info(f"Nonsense query detected | Avg Score: {avg_score} | Verse Count: {len(verses)}")
        
        if len(verses) == 0:
            return f"""The query "{query}" doesn't appear to be a biblical topic. This is a Bible search tool. Please ask about biblical concepts, themes, or passages."""
        
        # For nonsense queries, be very strict - even moderate matches are likely spurious
        if avg_score < 0.6 or len(verses) < 3:
            return f"""The query "{query}" doesn't appear to be a biblical topic. Politely explain this is a Bible search tool and suggest reformulating the question in biblical terms."""
    
    # Robust prompt that demands explanation, not parroting
    prompt = f"""Explain what the Bible teaches about "{query}" using these verses. Write 2-3 sentences that EXPLAIN the meaning, not just quote the verses.

{verse_context}

Requirements:
- Explain WHAT this means in plain language
- Include verse references like "Matthew 6:14 teaches..." 
- Don't just repeat the verse words - explain the principle
- Be accurate - if verses say "seventh day" don't change it to "seventh month"

Explanation:"""
    
    return prompt


def generate_commentary(
    query: str,
    verses: List[Dict],
    cache_dir: Optional[Path] = None,
    use_cache: bool = True
) -> Dict:
    """
    Generate natural language commentary from verse search results.
    
    Args:
        query: User's search query
        verses: List of verse dicts with 'reference', 'text', 'relevance_score'
        cache_dir: Directory for caching results
        use_cache: Whether to use cached results
    
    Returns:
        Dict with 'commentary', 'verses_used', 'model_info'
    """
    
    if not verses:
        return {
            'commentary': "No verses found to generate commentary.",
            'verses_used': 0,
            'model_info': None
        }
    
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
                'model_info': {'source': 'cache'}
            }
    
    # Load model
    model, tokenizer, device = _load_model()
    torch = _get_torch()
    
    # Build prompt
    prompt = _build_prompt(query, verses)
    
    logger.info(f"Generating commentary for query: {query}")
    logger.debug(f"Prompt length: {len(prompt)} chars")
    
    try:
        # Tokenize
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            max_length=1024,
            truncation=True
        ).to(device)
        
        # Generate with optimized parameters
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_length=120,  # Shorter for concise output
                min_length=30,
                temperature=0.3,  # Lower for more focused output
                top_p=0.85,
                do_sample=True,
                num_beams=4,  # Beam search for better quality
                repetition_penalty=2.5,  # Strong penalty against repetition
                no_repeat_ngram_size=3,  # Prevent 3-gram repetition
                early_stopping=True
            )
        
        # Decode
        commentary = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Post-process: Clean up formatting and validate
        import re
        # Remove leading numbers like "1.", "2.", etc.
        commentary = re.sub(r'^\d+\.\s*', '', commentary)
        commentary = re.sub(r'\s+\d+\.\s+', ' ', commentary)
        
        # Remove instruction echoing (if model repeats the prompt)
        instruction_patterns = [
            r'Explain what .*? teaches',
            r'Requirements:.*',
            r'Don\'t just repeat.*',
            r'Include verse references.*',
            r'WHAT this means.*'
        ]
        for pattern in instruction_patterns:
            commentary = re.sub(pattern, '', commentary, flags=re.IGNORECASE)
        
        commentary = commentary.strip()
        
        # Validate commentary quality
        if len(commentary) < 20:
            logger.warning(f"Commentary too short ({len(commentary)} chars), using fallback")
            raise ValueError("Generated commentary too short")
        
        # Check if it's just repeating the prompt/instructions
        if any(phrase in commentary.lower() for phrase in ['explain what', 'requirements:', 'provide a meaningful']):
            logger.warning("Commentary appears to echo instructions, using fallback")
            raise ValueError("Commentary echoing instructions")
        
        logger.info(f"Generated commentary: {len(commentary)} chars")
        
        # Cache result
        if use_cache:
            _save_cache(cache_key, query, commentary, cache_dir)
        
        return {
            'commentary': commentary.strip(),
            'verses_used': len(verse_ids),
            'commentary_mode': 'full',
            'model_info': {
                'model': 'google/flan-t5-large',
                'device': device,
                'verses_referenced': len(verse_ids)
            }
        }
        
    except Exception as e:
        logger.error(f"Commentary generation error: {e}")
        
        # Enhanced fallback with better messaging
        if not verses or len(verses) == 0:
            fallback = "Commentary unavailable — no relevant verses found."
            commentary_mode = 'missing'
        else:
            fallback = f"Commentary unavailable — showing direct verses instead. "
            fallback += f"See {verses[0]['reference']}"
            if len(verses) > 1:
                fallback += f", {verses[1]['reference']}"
            if len(verses) > 2:
                fallback += f", and {verses[2]['reference']}"
            fallback += " below for relevant passages."
            commentary_mode = 'fallback'
        
        return {
            'commentary': fallback,
            'verses_used': len(verse_ids) if verses else 0,
            'commentary_mode': commentary_mode,
            'model_info': {'source': 'fallback', 'error': str(e)}
        }


def get_model_status() -> Dict:
    """Get current model status and GPU info"""
    torch = _get_torch()
    
    status = {
        'model_loaded': _model is not None,
        'device': str(_device) if _device else 'not_loaded',
        'gpu_available': torch.cuda.is_available()
    }
    
    if torch.cuda.is_available():
        status['gpu_name'] = torch.cuda.get_device_name(0)
        status['gpu_memory_allocated_gb'] = round(
            torch.cuda.memory_allocated(0) / 1024**3, 2
        )
        status['gpu_memory_reserved_gb'] = round(
            torch.cuda.memory_reserved(0) / 1024**3, 2
        )
    
    return status
