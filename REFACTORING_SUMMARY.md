# Smart Bible Search - Modular Architecture

## Quick Summary

This refactoring transforms the monolithic Bible Query System into a clean, modular architecture with semantic search capabilities.

### ✅ What's New

**Backend Modules** (all in `/backend`):
- `config.py` - Configuration & constants
- `data_loader.py` - Verse and lexicon loading
- `search_keyword.py` - Traditional text search
- `search_semantic.py` - AI-powered semantic search (sentence transformers + FAISS)
- `explain.py` - Natural language result synthesis
- `app_refactored.py` - Clean API routes (routes only, no business logic)

**New Endpoints**:
- `POST /semantic_search` - Natural language queries
- `POST /explain` - Search with explanation synthesis

**Infrastructure**:
- `generate_embeddings.py` - Build FAISS index for semantic search
- Updated `Dockerfile` and `docker-compose.yml` for new dependencies
- `ARCHITECTURE.md` - Comprehensive documentation

### 📊 Validation Results

```
✓ 31,102 verses loaded (100% complete)
✓ 66 books detected
✓ Keyword search: Working (avg 20-30ms)
✓ Explanation synthesis: Working
✓ All modules import successfully
```

**Sample Search**:
- Query: "faith"
- Results: 5 verses
- Top: James 2:18 (score: 27.03)

### 🚀 Usage

**1. Local Development (without semantic search)**:
```bash
cd backend
python app_refactored.py
# Runs on http://localhost:8000
```

**2. Docker (full system)**:
```bash
docker-compose up --build
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

**3. Enable Semantic Search**:
```bash
# Install dependencies
pip install sentence-transformers faiss-cpu torch

# Generate embeddings (5-10 minutes)
python generate_embeddings.py

# Restart backend
docker-compose restart backend
```

### 🧪 Test Endpoints

```bash
# Keyword search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "love", "max_results": 5}'

# Semantic search (after running generate_embeddings.py)
curl -X POST http://localhost:8000/semantic_search \
  -H "Content-Type: application/json" \
  -d '{"query": "divine forgiveness and grace"}'

# Explanation
curl -X POST http://localhost:8000/explain \
  -H "Content-Type: application/json" \
  -d '{"query": "wisdom", "max_verses": 3}'
```

### 📁 File Overview

| File | Lines | Purpose |
|------|-------|---------|
| `config.py` | 45 | Configuration constants |
| `data_loader.py` | 105 | Data loading & validation |
| `search_keyword.py` | 140 | Keyword search algorithm |
| `search_semantic.py` | 215 | Semantic search (embeddings) |
| `explain.py` | 170 | Result synthesis |
| `app_refactored.py` | 250 | API routes only |

**Total backend code**: ~925 lines (down from 1 monolithic file)

### 🎯 Design Principles

1. **Single Responsibility**: Each module has one clear job
2. **Plug-and-Play**: Easy to swap implementations
3. **No File > 250 Lines**: Enforced readability
4. **Lazy Loading**: Heavy dependencies loaded on-demand
5. **Windows Compatible**: No unicode symbols in output

### 🔮 Next Steps

- [ ] Frontend JS modularization (search.js, semantic.js, ui.js)
- [ ] Unit tests for each module
- [ ] Strong's lexicon integration
- [ ] Multi-language support (LXX, SBLGNT)

---

See [ARCHITECTURE.md](ARCHITECTURE.md) for full documentation.
