"""
Configuration settings for Bible Query System.
Contains paths, constants, and configurable parameters.
"""

import os
from pathlib import Path

# === Paths ===
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR.parent

# Check if running in Docker (workdir is /app, so parent is /)
# In Docker, cache is mounted at /app/cache, not /cache
if BASE_DIR.parent == Path("/"):
    # Running in Docker container
    CACHE_DIR = BASE_DIR / "cache"
else:
    # Running locally (backend/ directory)
    CACHE_DIR = DATA_DIR / "cache"

# Data files
KJV_CHUNKS_FILE = "kjv_chunks.jsonl"
LEXICON_METADATA_FILE = "lexicon_metadata.json"

# Embeddings and FAISS index
EMBEDDINGS_FILE = CACHE_DIR / "verse_embeddings.npy"
FAISS_INDEX_FILE = CACHE_DIR / "verse_index.faiss"
VERSE_MAPPING_FILE = CACHE_DIR / "verse_mapping.json"

# === Model Configuration ===
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384  # Dimension for all-MiniLM-L6-v2

# === Search Configuration ===
DEFAULT_MAX_RESULTS = 10
SEMANTIC_SEARCH_SIMILARITY_THRESHOLD = 0.3

# === KJV Canonical Counts ===
CANONICAL_VERSE_COUNT = 31102  # Actual KJV count from our parsed data
CANONICAL_BOOK_COUNT = 66

# === API Configuration ===
API_TITLE = "Bible Query API"
API_VERSION = "2.0.0"
API_HOST = "0.0.0.0"
API_PORT = 8000

# Ensure cache directory exists
CACHE_DIR.mkdir(parents=True, exist_ok=True)
