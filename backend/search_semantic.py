"""
Semantic search for Bible verses using sentence embeddings.
Uses sentence-transformers and FAISS for efficient similarity search.
"""

import json
from typing import List, Dict, Optional
from pathlib import Path
import config

# Lazy imports for heavy dependencies
_model = None
_faiss_index = None
_verse_ids = None
_np = None


def _get_numpy():
    """Lazy import numpy."""
    global _np
    if _np is None:
        try:
            import numpy as np
            _np = np
        except ImportError:
            raise ImportError("numpy not installed. Run: pip install numpy")
    return _np


def _load_model():
    """Lazy load the sentence transformer model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print(f"Loading embedding model: {config.EMBEDDING_MODEL}...")
            _model = SentenceTransformer(config.EMBEDDING_MODEL)
            print("OK: Model loaded")
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )
    return _model


def _load_index():
    """Lazy load the FAISS index and verse mapping."""
    global _faiss_index, _verse_ids
    
    if _faiss_index is None:
        try:
            import faiss
            
            print(f"DEBUG: Checking for FAISS index at: {config.FAISS_INDEX_FILE}")
            print(f"DEBUG: File exists: {config.FAISS_INDEX_FILE.exists()}")
            
            if not config.FAISS_INDEX_FILE.exists():
                raise FileNotFoundError(
                    f"FAISS index not found at {config.FAISS_INDEX_FILE}. "
                    "Run generate_embeddings.py first."
                )
            
            if not config.VERSE_MAPPING_FILE.exists():
                raise FileNotFoundError(
                    f"Verse mapping not found at {config.VERSE_MAPPING_FILE}. "
                    "Run generate_embeddings.py first."
                )
            
            print(f"Loading FAISS index from {config.FAISS_INDEX_FILE}...")
            _faiss_index = faiss.read_index(str(config.FAISS_INDEX_FILE))
            
            with open(config.VERSE_MAPPING_FILE, 'r') as f:
                _verse_ids = json.load(f)
            
            print(f"OK: Loaded FAISS index with {_faiss_index.ntotal} vectors")
            
        except ImportError:
            raise ImportError(
                "faiss-cpu not installed. "
                "Run: pip install faiss-cpu"
            )
    
    return _faiss_index, _verse_ids


def search_semantic(
    verses: List[Dict], 
    query: str, 
    max_results: int = 10,
    min_similarity: float = None
) -> List[Dict]:
    """
    Perform semantic search using sentence embeddings.
    
    Args:
        verses: List of verse dictionaries
        query: Natural language query
        max_results: Maximum number of results to return
        min_similarity: Minimum similarity threshold (0-1)
    
    Returns:
        List of matching verses with similarity scores, sorted by relevance
    """
    if not query or not query.strip():
        return []
    
    if min_similarity is None:
        min_similarity = config.SEMANTIC_SEARCH_SIMILARITY_THRESHOLD
    
    # Load model and index
    model = _load_model()
    index, verse_ids = _load_index()
    np = _get_numpy()
    
    # Encode query
    query_embedding = model.encode([query], convert_to_numpy=True)
    
    # Normalize for cosine similarity
    query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
    
    # Search FAISS index
    # Request more than max_results to allow for filtering
    k = min(max_results * 3, index.ntotal)
    similarities, indices = index.search(query_embedding.astype('float32'), k)
    
    # Build results
    results = []
    for similarity, idx in zip(similarities[0], indices[0]):
        if similarity < min_similarity:
            continue
        
        verse_id = verse_ids[idx]
        verse = verses[verse_id]
        
        results.append({
            **verse,
            "relevance_score": round(float(similarity), 4)
        })
        
        if len(results) >= max_results:
            break
    
    return results


def generate_embeddings(verses: List[Dict], force: bool = False) -> None:
    """
    Generate embeddings for all verses and build FAISS index.
    Caches results to disk for fast loading.
    
    Args:
        verses: List of verse dictionaries
        force: Force regeneration even if cache exists
    """
    if not force and config.FAISS_INDEX_FILE.exists() and config.VERSE_MAPPING_FILE.exists():
        print("OK: Embeddings already cached. Use force=True to regenerate.")
        return
    
    try:
        import faiss
    except ImportError:
        raise ImportError("faiss-cpu not installed. Run: pip install faiss-cpu")
    
    model = _load_model()
    np = _get_numpy()
    
    print(f"Generating embeddings for {len(verses)} verses...")
    print("This may take a few minutes...")
    
    # Extract verse texts
    texts = [v["text"] for v in verses]
    
    # Generate embeddings in batches
    batch_size = 256
    embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = model.encode(batch, show_progress_bar=True, convert_to_numpy=True)
        embeddings.append(batch_embeddings)
        print(f"  Progress: {min(i + batch_size, len(texts))}/{len(texts)}")
    
    embeddings = np.vstack(embeddings).astype('float32')
    
    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings)
    
    # Build FAISS index
    print("Building FAISS index...")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
    index.add(embeddings)
    
    # Save index
    print(f"Saving FAISS index to {config.FAISS_INDEX_FILE}...")
    faiss.write_index(index, str(config.FAISS_INDEX_FILE))
    
    # Save verse ID mapping
    verse_ids = list(range(len(verses)))
    with open(config.VERSE_MAPPING_FILE, 'w') as f:
        json.dump(verse_ids, f)
    
    # Save embeddings (optional, for debugging)
    if config.EMBEDDINGS_FILE:
        print(f"Saving embeddings to {config.EMBEDDINGS_FILE}...")
        np.save(config.EMBEDDINGS_FILE, embeddings)
    
    print(f"OK: Generated and cached {len(verses)} embeddings")


def get_embedding_stats() -> Dict:
    """
    Get statistics about the embedding cache.
    
    Returns:
        Dictionary with cache status and metadata
    """
    stats = {
        "index_exists": config.FAISS_INDEX_FILE.exists(),
        "embeddings_exist": config.EMBEDDINGS_FILE.exists(),
        "mapping_exists": config.VERSE_MAPPING_FILE.exists(),
        "model_name": config.EMBEDDING_MODEL,
        "embedding_dim": config.EMBEDDING_DIM
    }
    
    if stats["index_exists"]:
        try:
            import faiss
            index = faiss.read_index(str(config.FAISS_INDEX_FILE))
            stats["total_vectors"] = index.ntotal
            stats["index_size_mb"] = config.FAISS_INDEX_FILE.stat().st_size / (1024 * 1024)
        except Exception as e:
            stats["error"] = str(e)
    
    return stats
