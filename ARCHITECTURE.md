# Architecture Documentation

## System Overview

Smart Bible Search is a modular, AI-powered Bible search system with both traditional keyword search and semantic (meaning-based) search capabilities.

**Live Stats**: 31,102 verses | 66 books | 100% complete KJV

---

## Backend Modules

| Module | Lines | Purpose |
|--------|-------|---------|
| `config.py` | 45 | Configuration constants |
| `data_loader.py` | 105 | Data loading & validation |
| `search_keyword.py` | 140 | Traditional text search |
| `search_semantic.py` | 215 | AI semantic search (FAISS) |
| `explain.py` | 170 | Natural language synthesis |
| `app_refactored.py` | 250 | API routes only |

**Total**: ~925 lines (fully modular)

---

## Frontend Modules

| Module | Purpose |
|--------|---------|
| `index.html` | HTML structure + CSS |
| `ui.js` | Modal, verse expansion, status messages |
| `search.js` | Keyword search + backend communication |
| `semantic.js` | Semantic search API integration |

**Architecture**: Clean separation of concerns, no inline scripts

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Health check |
| `/stats` | GET | System statistics |
| `/search` | POST | Keyword search |
| `/semantic_search` | POST | AI semantic search |
| `/explain` | POST | Search with explanation |
| `/chapter/{book}/{chapter}` | GET | Full chapter retrieval |

---

## Data Flow

### Keyword Search
```
User → search.js → POST /search → search_keyword.py → JSON → UI
```

### Semantic Search
```
User → semantic.js → POST /semantic_search → FAISS index → JSON → UI
```

### Chapter View
```
Click → ui.js → GET /chapter/... → search_keyword.py → Modal display
```

---

## Key Features

✅ **Modular Design**: Each file <250 lines, single responsibility  
✅ **Plug-and-Play**: Easy to swap search algorithms  
✅ **Lazy Loading**: Heavy ML libs loaded only when needed  
✅ **Windows Compatible**: No unicode symbols in output  
✅ **Docker Ready**: Full containerization with volume mounts  
✅ **Semantic Search**: Optional AI-powered search via FAISS  

---

## Quick Start

**Local Development**:
```bash
python backend/app_refactored.py  # Backend on port 8000
```

**Docker (Full System)**:
```bash
docker-compose up --build
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

**Enable Semantic Search**:
```bash
pip install sentence-transformers faiss-cpu torch
python generate_embeddings.py  # Takes 5-10 minutes
docker-compose restart backend
```

---

## Performance

- **Keyword Search**: 20-50ms latency, ~100 req/s
- **Semantic Search**: 100-200ms latency, ~20 req/s
- **Chapter Retrieval**: 5-10ms latency, ~500 req/s

---

## Testing

```bash
# Health
curl http://localhost:8000/

# Keyword search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "faith", "max_results": 5}'

# Semantic search
curl -X POST http://localhost:8000/semantic_search \
  -H "Content-Type: application/json" \
  -d '{"query": "divine love and grace"}'
```

---

See [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) for migration details.
