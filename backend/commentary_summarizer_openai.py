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

import lexicon_lookup
import search_commentary_corpus
import memory_store
import search_concept_documents

logger = logging.getLogger(__name__)

# Ollama configuration (FREE local)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# Cloudflare Workers AI configuration (SMART for reasoning)
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_MODEL = "@cf/meta/llama-3.1-70b-instruct"  # Best reasoning model
CLOUDFLARE_API_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CLOUDFLARE_MODEL}" if CLOUDFLARE_ACCOUNT_ID else None


def _check_cloudflare_available() -> bool:
    """Check if Cloudflare Workers AI is configured"""
    return bool(CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN and CLOUDFLARE_API_URL)


import re as _re

# Multi-word phrases that specifically indicate the answer requires a date,
# duration, or count - NOT generic connectives. The previous version of
# this list included bare words like 'to', 'from', 'after', 'before', and a
# lone '?', which matched almost any query (e.g. "how does it relate TO the
# sabbath" tripped on "to" alone, nothing about actual complexity).
_NUMERIC_FACT_PHRASES = [
    'how old', 'how many', 'how long', 'how much time', 'what year',
    'died at', 'born in', 'started at', 'began at', 'ended at',
    'years old', 'age of', 'how much longer',
]
_CALCULATION_PHRASES = [
    'calculate', 'difference between', 'add up', 'total of', 'sum of',
]

# Named doctrinal debates where mainstream Christian traditions have long
# held genuinely different, named positions - not just "hard questions" in
# general (e.g. "why do bad things happen" doesn't qualify; "predestination
# vs free will" does). These route to Cloudflare with an explicit
# instruction to name the actual frameworks (see _build_prompt), instead of
# collapsing to one sanitized, denomination-blind answer - the exact
# "user-pleasing generic pastoral answer" failure mode the Haven comparison
# flagged.
_THEOLOGICAL_PARADOX_PHRASES = [
    'predestination', 'free will', 'calvinism', 'arminianism',
    'once saved always saved', 'eternal security', 'lose your salvation',
    'lose my salvation', 'perseverance of the saints', 'falling from grace',
    'infant baptism', "believer's baptism", 'baptism necessary for salvation',
    'transubstantiation', 'what does communion mean', "lord's supper",
    'speaking in tongues', 'gift of tongues', 'cessationism',
    'spiritual gifts still', 'are spiritual gifts',
    'eternal conscious torment', 'annihilationism', 'universal reconciliation',
    'universalism', 'rapture', 'tribulation', 'millennial reign', 'end times views',
    'women pastors', 'women in ministry', 'women elders', 'women deacons',
    'faith alone', 'faith and works', 'justification by faith',
    'problem of evil', 'why does god allow suffering', 'why does a good god allow',
]

_CAPITALIZED_WORD_RE = _re.compile(r"\b[A-Z][a-zA-Z]{2,}\b")
_SIMPLE_QUESTION_WORDS = ['who', 'what', 'when', 'where', 'which', 'name', 'how many']


def assess_query_complexity(query: str, verses: List[Dict]) -> Dict:
    """
    Decide whether a commentary query needs Cloudflare's larger reasoning
    model, using signals available before any LLM call.

    Retrieval relevance score was tested as a confidence gate for the
    numeric/date signal below (only escalate if the top verse is also a
    weak match) and dropped: it doesn't discriminate. Across five real
    numeric-fact queries, top relevance clustered at 0.57-0.76 regardless
    of whether a verse actually stated the answer - "how old was Jesus
    when he died" (0.635, no verse states it - needs Luke 3:23's starting
    age plus separately-mentioned Passovers) scored *lower* than "how many
    days did it rain during the flood" (0.661, but the top verse was about
    a *different* 7-day wait, not the 40-day rain), and both scored in the
    same range as "how many sons did Jacob have" (0.757, genuinely simple).
    Semantic similarity measures topical closeness, not whether the fact
    asked for is explicitly stated vs. inferred, so it can't safely gate
    this. Given that, every numeric/date-type question is routed to
    Cloudflare unconditionally - the extra cost on the occasional simple
    count is accepted as the price of not silently under-answering the
    cases (age/duration questions) this routing exists for.
    """
    query_lower = query.lower().strip()

    wants_numeric_fact = any(p in query_lower for p in _NUMERIC_FACT_PHRASES)
    wants_calculation = any(p in query_lower for p in _CALCULATION_PHRASES)

    # Two or more distinct capitalized names/terms suggests a relational or
    # comparative question ("how does X relate to Y", "compare Paul and
    # Peter's teaching on grace") - genuinely more synthesis-heavy than a
    # single-subject lookup, and a much more precise signal than the old
    # bare 'between'/'to'/'from' substring checks.
    capitalized_words = set(_CAPITALIZED_WORD_RE.findall(query))
    distinct_entities = len(capitalized_words)

    words = query.split()
    is_long_multiclause = len(words) >= 14 and (
        ' and ' in query_lower or ' or ' in query_lower or ';' in query
    )

    is_theological_paradox = any(p in query_lower for p in _THEOLOGICAL_PARADOX_PHRASES)

    top_relevance = verses[0].get('relevance_score', 0) if verses else 0

    is_complex = (
        wants_numeric_fact
        or wants_calculation
        or distinct_entities >= 2
        or is_long_multiclause
        or is_theological_paradox
    )

    # Classification used to gate what's allowed into memory_store.py:
    # 'factual' answers can be auto-verified (grounding_check.py) and
    # auto-promoted; 'interpretive' answers have no ground truth to check
    # automatically and require an explicit human approval instead. A
    # theological paradox is interpretive even if it also happens to
    # contain a "how many/how old"-style phrase - the doctrinal disagreement
    # takes precedence. Otherwise: numeric-fact questions and classic
    # who/what/when/how-many lookups are factual; anything more open-ended
    # ("explain...", "what does X mean", "why...") defaults to interpretive,
    # since that's the safer default when it's ambiguous.
    if is_theological_paradox:
        query_type = 'interpretive'
    elif wants_numeric_fact or any(w in query_lower for w in _SIMPLE_QUESTION_WORDS):
        query_type = 'factual'
    else:
        query_type = 'interpretive'

    return {
        'is_complex': is_complex,
        'wants_numeric_fact': wants_numeric_fact,
        'wants_calculation': wants_calculation,
        'distinct_entities': distinct_entities,
        'is_long_multiclause': is_long_multiclause,
        'is_theological_paradox': is_theological_paradox,
        'top_relevance': top_relevance,
        'query_type': query_type,
    }


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


def _build_prompt(
    query: str,
    verses: List[Dict],
    use_reasoning: bool = False,
    is_theological_paradox: bool = False,
) -> str:
    """Build prompt - enhanced version for reasoning if needed"""

    # Use more verses for complex queries
    max_verses = 15 if use_reasoning else 5

    verse_list = []
    for v in verses[:max_verses]:
        verse_list.append(f"{v['reference']}: \"{v['text']}\"")

    verse_context = "\n".join(verse_list)

    word_studies = lexicon_lookup.get_word_studies(verses[:max_verses])
    word_study_block = lexicon_lookup.format_word_studies(word_studies)
    word_study_section = f"\n\n{word_study_block}" if word_study_block else ""

    gc_results = search_commentary_corpus.search_commentary_corpus(query)
    gc_block = search_commentary_corpus.format_commentary_context(gc_results)
    gc_section = f"\n\n{gc_block}" if gc_block else ""

    concept_results = search_concept_documents.search_concepts(query)
    concept_block = search_concept_documents.format_concept_context(concept_results)
    concept_section = f"\n\n{concept_block}" if concept_block else ""

    memory_results = memory_store.search_memory(query)
    memory_block = memory_store.format_memory_context(memory_results)
    memory_section = f"\n\n{memory_block}" if memory_block else ""

    # THEOLOGICAL PARADOX PROMPT: doctrines where mainstream Christian
    # traditions genuinely, historically disagree. Deliberately a separate
    # template from the age/duration reasoning prompt below (forcing a
    # predestination question through "count the Passovers" style steps
    # makes no sense). The explicit ask to NAME frameworks exists because
    # the Haven comparison's specific complaint was that LLM-backed Bible
    # apps default to a single fluid, sanitized, user-pleasing answer
    # instead of surfacing that real disagreement exists.
    if is_theological_paradox:
        prompt = f"""Question: {query}

Biblical Evidence:
{verse_context}{word_study_section}{gc_section}{concept_section}{memory_section}

Instructions: This question touches a doctrine where mainstream Christian traditions have long held genuinely different, named positions - there is no single consensus answer, and you must not pretend there is. Structure your answer as follows:

1. Name the major historic frameworks/traditions on this specific question (e.g., for predestination: Calvinism vs. Arminianism; for the Lord's Supper: transubstantiation vs. consubstantiation vs. memorial view; for spiritual gifts: cessationism vs. continuationism - use whichever pair or set actually applies to THIS question).
2. Briefly state what each framework holds, grounded in the verses above where they apply.
3. Do NOT collapse this into one "safe," denomination-blind answer, and do NOT just say "Christians disagree" without naming the actual positions.
4. Close by encouraging the reader to study further with a pastor or their local church community, since this is exactly the kind of question that benefits from guided, in-person study rather than a single AI answer.
5. Cite specific verses used. Do NOT use conversational phrases like "Hello" or "I think".

Answer:"""

    # REASONING PROMPT (for Cloudflare with complex queries)
    elif use_reasoning:
        prompt = f"""Question: {query}

Biblical Evidence:
{verse_context}{word_study_section}{gc_section}{concept_section}{memory_section}

Instructions: Answer this question by carefully analyzing the verses above. Follow these steps:

Step 1: Extract ALL relevant facts:
   - Direct statements (e.g., ages, years, durations explicitly mentioned)
   - Countable events (e.g., if 3 Passovers are mentioned during ministry, and Passover is annual, that indicates ~3 years)
   - Event sequences (e.g., "started at age X" → ministry events → death)

Step 2: Apply logical reasoning:
   - If you find a starting age AND a duration (even if inferred from counting events), add them
   - Example: "Jesus began at about 30 years" (Luke 3:23) + "John mentions 3 Passovers during ministry = ~3 years" = "approximately 33 years old at death"
   - Count mentions of annual festivals/events to determine time spans

Step 3: Provide answer with reasoning:
   - Cite specific verses used
   - Show calculation if applicable: "30 years (start) + 3 years (ministry) = approximately 33 years (death)"
   - Use "approximately" or "around" for calculated/inferred answers
   - If evidence is insufficient, state what's missing

CRITICAL REASONING RULES:
- Annual events (Passover, feasts) indicate time when counted across narrative
- Starting age + duration (even if counted from events) = ending age
- Use verses above but APPLY LOGIC to combine facts
- Always cite verses (e.g., "According to Luke 3:23...")
- If a Word Study section is present and relevant, you may cite its Strong's number; if a word has more than one listed sense, use the one that fits this context
- Do NOT use conversational phrases

Think step-by-step:

Answer:"""
    
    # SIMPLE FACTUAL PROMPT (for Ollama)
    else:
        query_lower = query.lower().strip()
        is_simple_question = any(word in query_lower for word in _SIMPLE_QUESTION_WORDS)
        
        if is_simple_question:
            prompt = f"""Question: {query}

Biblical Verses:
{verse_context}{word_study_section}{gc_section}{concept_section}{memory_section}

Instructions: Write a concise 2-3 sentence answer using ONLY what these exact verses state. If the information is not in the verses above, say "The provided verses do not contain this information." Do NOT use knowledge from outside these verses. Do NOT make connections to similar-sounding names or assume different people are the same person. Do NOT use conversational phrases like "Hello", "Let's talk about", "I'm happy to help", "I think", or "Interesting". Start directly with the biblical information. ALWAYS cite specific verse references (e.g., "According to Numbers 3:35"). If the query name appears in only one verse, describe ONLY what that specific verse says about that specific person. If the Word Study section above lists a relevant original-language term, you may briefly mention it - but NEVER write a bare Strong's number like "(H158)" alone, always pair it with its plain-English meaning in the same breath (e.g. "loved (Strong's G25, meaning selfless love)"), since a bare code means nothing to a reader; if a word has more than one listed sense, use the one that fits this context.

Answer:"""
        else:
            prompt = f"""Topic: {query}

Biblical Verses:
{verse_context}{word_study_section}{gc_section}{concept_section}{memory_section}

Instructions: Write a concise 2-4 sentence explanation using ONLY what these verses teach. If these verses do not address the topic, say "The provided verses do not directly address this topic." Do NOT use knowledge from outside these verses. Do NOT use conversational phrases. Start directly with the biblical teaching. ALWAYS reference specific verses. Only use what is directly stated in these verses. If the Word Study section above lists a relevant original-language term, you may briefly mention it - but NEVER write a bare Strong's number like "(H158)" alone, always pair it with its plain-English meaning in the same breath (e.g. "loved (Strong's G25, meaning selfless love)"), since a bare code means nothing to a reader; if a word has more than one listed sense, use the one that fits this context.

Summary:"""
    
    return prompt


def _generate_with_cloudflare(
    query: str,
    verses: List[Dict],
    cache_dir: Path,
    cache_key: str,
    use_cache: bool,
    is_theological_paradox: bool = False
) -> Dict:
    """Generate commentary using Cloudflare Workers AI (for complex reasoning)"""

    # Build reasoning-enhanced prompt
    prompt = _build_prompt(
        query, verses, use_reasoning=True, is_theological_paradox=is_theological_paradox
    )
    
    logger.info(f"Calling Cloudflare Workers AI with {CLOUDFLARE_MODEL}")

    # Theological-paradox answers need room for multiple named frameworks
    # plus a closing pastoral note - 300 tokens (fine for the age/duration
    # reasoning case) was confirmed to cut this response off mid-sentence,
    # right as it started the second framework, before ever reaching the
    # "study further with a pastor" instruction.
    max_tokens = 700 if is_theological_paradox else 300

    # Call Cloudflare API
    response = requests.post(
        CLOUDFLARE_API_URL,
        headers={
            "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "messages": [
                {"role": "system", "content": "You are a biblical scholar analyzing scripture. Provide factual, verse-based answers only."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens
        },
        timeout=30
    )
    
    if response.status_code != 200:
        raise Exception(f"Cloudflare API error: {response.status_code} - {response.text}")
    
    result = response.json()
    commentary = result.get('result', {}).get('response', '').strip()
    
    if not commentary:
        raise Exception("Empty response from Cloudflare")
    
    # Post-processing - remove conversational fluff
    import re
    conversational_phrases = [
        r'^Hello[!,\.\s]+', r'^Hi[!,\.\s]+', r'^Hey[!,\.\s]+',
        r'^OK[,\.\s]+', r'^Okay[,\.\s]+', r'^Alright[,\.\s]+', r'^Well[,\.\s]+',
        r'^Let\'s\s+(?:talk about|discuss|explore|look at)',
        r'^I think', r'^I believe', r'^Hmm[,\.\s]+', r'^Interesting[!,\.\s]+',
    ]
    for pattern in conversational_phrases:
        commentary = re.sub(pattern, '', commentary, flags=re.IGNORECASE)
    
    commentary = commentary.strip()
    if commentary:
        commentary = commentary[0].upper() + commentary[1:]
    
    logger.info(f"Cloudflare generated: {len(commentary)} chars")
    
    # Cache result
    if use_cache:
        _save_cache(cache_key, query, commentary, cache_dir)
    
    return {
        'commentary': commentary,
        'verses_used': len(verses),
        'model_info': {
            'model': CLOUDFLARE_MODEL,
            'provider': 'Cloudflare Workers AI',
            'reasoning': 'advanced'
        }
    }


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
    
    # Check cache - use all verses for commentary generation
    verse_ids = [v['reference'] for v in verses]
    cache_key = _create_cache_key(query, verse_ids)
    
    if use_cache:
        cached = _load_cache(cache_key, cache_dir)
        if cached:
            return {
                'commentary': cached,
                'verses_used': len(verse_ids),
                'model_info': {'source': 'cache', 'model': model}
            }
    
    # SIMPLE FAILSAFE: For single-verse queries with exact name match, just use the verse directly
    if len(verses) == 1:
        verse = verses[0]
        query_lower = query.lower().strip()
        verse_text_lower = verse['text'].lower()
        
        # Check if query is a single word (likely a name) and appears in the verse
        if len(query_lower.split()) == 1 and query_lower in verse_text_lower:
            simple_commentary = f"According to {verse['reference']}, {verse['text']}"
            
            logger.info(f"Using simple direct approach for single-verse name query: {query}")
            
            if use_cache:
                _save_cache(cache_key, query, simple_commentary, cache_dir)
            
            return {
                'commentary': simple_commentary,
                'verses_used': 1,
                'model_info': {'approach': 'direct_verse_citation', 'model': 'direct'}
            }
    
    # INTELLIGENT ROUTING: Complex queries → Cloudflare, Simple → Ollama
    complexity = assess_query_complexity(query, verses)
    use_cloudflare = complexity['is_complex'] and _check_cloudflare_available()

    if use_cloudflare:
        logger.info(f"Routing to Cloudflare Workers AI (complexity signals: {complexity}): {query}")
        try:
            return _generate_with_cloudflare(
                query, verses, cache_dir, cache_key, use_cache,
                is_theological_paradox=complexity['is_theological_paradox']
            )
        except Exception as e:
            logger.error(f"Cloudflare failed, falling back to Ollama: {e}")
            # Fall through to Ollama

    # Use Ollama (free local model)
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
        # Build prompt (theological-paradox framing still applies even on
        # the Ollama fallback path, so the "name the frameworks" behavior
        # isn't lost if Cloudflare is unavailable)
        prompt = _build_prompt(
            query, verses, is_theological_paradox=complexity['is_theological_paradox']
        )
        
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
        
        # Aggressive post-processing - Remove ALL conversational phrases
        import re
        conversational_phrases = [
            r'^Hello[!,\.\s]+', r'^Hi[!,\.\s]+', r'^Hey[!,\.\s]+',
            r'^OK[,\.\s]+', r'^Okay[,\.\s]+', r'^Alright[,\.\s]+', r'^Well[,\.\s]+',
            r'^Let\'s\s+(?:talk about|discuss|explore|look at)',
            r'^I think', r'^I believe', r'^Hmm[,\.\s]+', r'^Interesting[!,\.\s]+',
            r'^Great question[!,\.\s]+', r'^Good question[!,\.\s]+',
            r'(?:I\'d be happy to|I can) help you (?:understand|learn)',
            r'(?:there may be|there might be) (?:a bit of )?confusion',
            r'^(?:In terms of|As for|Regarding)',
            r'(?:I couldn\'t find|There is no).*?in the Bible',
            r'However, I (?:can tell you|believe)',
        ]
        for pattern in conversational_phrases:
            commentary = re.sub(pattern, '', commentary, flags=re.IGNORECASE)
        
        commentary = re.sub(r'^Answer:\s*', '', commentary, flags=re.IGNORECASE)
        commentary = re.sub(r'^Summary:\s*', '', commentary, flags=re.IGNORECASE)
        commentary = commentary.strip()
        
        # Capitalize first letter
        if commentary:
            commentary = commentary[0].upper() + commentary[1:]
        
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


def generate_blessing(verse: Dict) -> Dict:
    """
    'Today's Blessing' - a random verse with a short reflection and prayer.
    Previously "I'm Feeling Blessed" was a button in the markup with no
    event listener anywhere in the JS - this makes it a real feature.

    Deliberately much simpler than generate_commentary(): one verse in, no
    retrieval, no complexity routing, no memory/grounding gate - it's a
    devotional aside, not a sourced answer, so it doesn't need any of that.
    """
    prompt = f"""Verse: {verse['reference']} - "{verse['text']}"

Write a short devotional for this verse with exactly two parts, in this exact format:

Reflection: 2-3 sentences reflecting on what this verse means for daily life.
Prayer: A short 1-2 sentence prayer inspired by this verse.

Do NOT use conversational phrases like "Hello" or "Let's explore". Start directly with "Reflection:"."""

    fallback = {
        'reflection': 'Take a moment to sit with this verse today.',
        'prayer': 'Lord, help me understand and apply Your word.',
    }

    if not _check_ollama_available():
        return fallback

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 200}
            },
            timeout=30
        )
        if response.status_code != 200:
            return fallback

        text = response.json().get('response', '').strip()

        if 'Prayer:' in text:
            reflection_part, prayer_part = text.split('Prayer:', 1)
            reflection = reflection_part.replace('Reflection:', '').strip()
            prayer = prayer_part.strip()
        else:
            reflection = text.replace('Reflection:', '').strip()
            prayer = ''

        return {
            'reflection': reflection or fallback['reflection'],
            'prayer': prayer or fallback['prayer'],
        }
    except Exception as e:
        logger.error(f"Blessing generation error: {e}")
        return fallback


def generate_session_title(query: str) -> str:
    """
    Short 3-6 word title for a history entry (e.g. "Grace in Scripture"
    instead of the raw first question truncated mid-sentence). Always uses
    the free local Ollama model, never Cloudflare - this is cosmetic, not
    a sourced answer, and shouldn't spend paid quota on every new session.
    Falls back to the raw query untouched if Ollama isn't running or the
    call fails, so history never breaks over a missing title.
    """
    if not _check_ollama_available():
        return query

    prompt = (
        "Write a short 3-6 word title summarizing the topic of this Bible "
        "study question. Reply with ONLY the title itself - no punctuation, "
        "no quotation marks, no explanation.\n\n"
        f"Question: {query}\n\nTitle:"
    )

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 16, "stop": ["\n"]}
            },
            timeout=15
        )
        if response.status_code != 200:
            return query

        title = response.json().get('response', '').strip().strip('"\'.,')
        return title or query
    except Exception as e:
        logger.warning(f"Session title generation failed, using raw query: {e}")
        return query
