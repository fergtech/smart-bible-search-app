# Bible Query System - Local Prototype

A simple, Dockerized Bible search system that performs keyword searches across 30,638 KJV verses.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- `kjv_chunks.jsonl` in the project root

### Run the System

```bash
docker-compose up --build
```

This will:
1. Build and start the backend API (Python FastAPI) on port 8000
2. Build and start the frontend UI (Nginx) on port 3000
3. Load all KJV verses into memory

### Access the Application

Open your browser to: **http://localhost:3000**

### Stop the System

```bash
docker-compose down
```

## 📁 Project Structure

```
book-intel/
├── backend/
│   ├── app.py              # FastAPI application
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile          # Backend container config
├── frontend/
│   ├── index.html          # Search UI
│   └── Dockerfile          # Frontend container config
├── docker-compose.yml      # Multi-container orchestration
├── kjv_chunks.jsonl        # KJV verse data (30,638 verses)
└── PROTOTYPE_README.md     # This file
```

## 🔍 How It Works

### Backend (FastAPI)
- Loads `kjv_chunks.jsonl` into memory on startup
- Provides `/search` endpoint for keyword queries
- Simple relevance scoring:
  - Exact phrase match: +10 points
  - Each matching term: +2 points
  - Term match ratio: +5 points
- Returns top N results sorted by relevance

### Frontend (HTML/JS)
- Clean, responsive search interface
- Query input with configurable result limit
- Highlights matching terms in results
- Shows verse reference, text, and relevance score

### Search Features
- Case-insensitive keyword matching
- Phrase search support
- Multi-term queries
- Relevance-based ranking

## 🧪 Testing

### Test the Backend API Directly

```bash
# Health check
curl http://localhost:8000/

# Search example
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "love thy neighbor", "max_results": 5}'

# Get stats
curl http://localhost:8000/stats
```

### Sample Searches
- Single word: `faith`
- Phrase: `valley of the shadow of death`
- Multiple terms: `love hope faith`
- Specific concept: `forgiveness`

## 🔧 Configuration

### Adjust Result Limit
Edit `frontend/index.html`:
```html
<input type="number" id="maxResults" value="10" min="1" max="100">
```

### Change Ports
Edit `docker-compose.yml`:
```yaml
services:
  backend:
    ports:
      - "8000:8000"  # Change first number for different host port
  frontend:
    ports:
      - "3000:80"    # Change first number for different host port
```

## 📊 System Stats

- **Total Verses**: 30,638 (entire KJV)
- **Data Format**: JSONL (JSON Lines)
- **Search Method**: In-memory keyword matching
- **Backend**: Python 3.11 + FastAPI
- **Frontend**: Static HTML/JS + Nginx
- **Deployment**: Docker Compose

## 🔮 Phase 2 Preparation

The backend is structured to support future enhancements:

### Ready for Embeddings
- Add embedding generation in `load_verses()`
- Store vectors alongside verse data
- Replace `search_verses()` with semantic search

### Lexicon Integration
- `lexicon_metadata.json` available for Greek enrichment
- Add enrichment endpoint: `/enrich/{reference}`
- Display Strong's definitions in UI

### Future Features
- Vector similarity search (embeddings)
- Greek/Hebrew word analysis
- Cross-reference linking
- Advanced filtering (book, chapter, testament)
- User annotations and bookmarks

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check logs
docker-compose logs backend

# Verify kjv_chunks.jsonl exists
ls -lh kjv_chunks.jsonl
```

### Frontend can't connect to backend
- Verify backend is running: `docker-compose ps`
- Check CORS settings in `backend/app.py`
- Ensure API_URL in `index.html` matches your setup

### Search returns no results
- Check if verses loaded: http://localhost:8000/stats
- Try simpler queries first (single words)
- Verify query encoding (avoid special characters)

## 📝 Development

### Run Backend Locally (without Docker)
```bash
cd backend
pip install -r requirements.txt
# Copy kjv_chunks.jsonl to backend/
python app.py
```

### Run Frontend Locally
```bash
cd frontend
# Use any static server, e.g.:
python -m http.server 3000
```

## 🎯 Current Capabilities

✅ Keyword search across entire KJV  
✅ Phrase matching  
✅ Relevance scoring  
✅ Fast in-memory search  
✅ Clean, responsive UI  
✅ Dockerized deployment  

❌ Semantic search (Phase 2)  
❌ Greek/Hebrew analysis (Phase 2)  
❌ AI inference (Phase 2)  

## 📄 License

This project uses public domain biblical texts (KJV).

---

**Built with**: FastAPI • Python • Docker • Nginx  
**Data**: King James Version (KJV) - 30,638 verses
