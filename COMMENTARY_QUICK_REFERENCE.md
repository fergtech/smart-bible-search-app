# Commentary System - Quick Reference Guide

## ✅ System Status

**Backend:** http://localhost:8000  
**Frontend:** http://localhost:3000  
**Status:** Fully Operational  
**Test Success Rate:** 100% (7/7 queries)

---

## 🚀 Quick Start

### Run the Application
```powershell
cd H:\Apps\book-intel
docker-compose up -d
```

### Test Commentary Endpoint
```powershell
# Test a query
curl -X POST http://localhost:8000/commentary `
  -H "Content-Type: application/json" `
  -d '{"query": "forgiveness", "max_results": 10, "use_cache": true}'
```

### Run Validation Tests
```powershell
python test_commentary_final.py
```

---

## 📊 Commentary Response Structure

```json
{
  "query": "peace",
  "commentary": "Peace be to the brethren, and love with faith...",
  "commentary_mode": "full",
  "verses": [
    {
      "reference": "Ephesians 6:23",
      "text": "Peace be to the brethren...",
      "relevance_score": 0.7234
    }
  ],
  "metadata": {
    "verses_used": 10,
    "total_results": 25,
    "model_info": {
      "model": "google/flan-t5-large",
      "device": "cpu",
      "verses_referenced": 10
    }
  }
}
```

---

## 🎯 Commentary Modes

### `"full"` - Success ✅
AI-generated commentary successfully created from verses.

**Example:**
```json
{
  "commentary": "Love your enemies, do good to them which hate you...",
  "commentary_mode": "full"
}
```

### `"fallback"` - Error Handling ⚠️
Model failed, but helpful fallback message provided.

**Example:**
```json
{
  "commentary": "Commentary unavailable — showing direct verses instead. See Matthew 6:14...",
  "commentary_mode": "fallback"
}
```

### `"missing"` - No Results ❌
No relevant verses found for query.

**Example:**
```json
{
  "commentary": "Commentary unavailable — no relevant verses found.",
  "commentary_mode": "missing"
}
```

---

## 🔧 Troubleshooting

### Commentary Not Appearing

**Check 1: Backend Running**
```powershell
curl http://localhost:8000/
# Should return: {"service": "Bible Query API", "status": "running"}
```

**Check 2: Model Status**
```powershell
curl http://localhost:8000/commentary/status
# Should return: {"model_loaded": true/false, "device": "cpu/cuda"}
```

**Check 3: Test Commentary**
```powershell
curl -X POST http://localhost:8000/commentary `
  -H "Content-Type: application/json" `
  -d '{"query": "test", "max_results": 10}'
```

### Slow First Request

**Cause:** Model downloading (3GB FLAN-T5-large)  
**Duration:** ~85 seconds (one-time only)  
**Solution:** Wait for download to complete, subsequent requests will be fast

**Check Progress:**
```powershell
docker logs book-intel-backend-1 -f
# Look for: "Loading commentary model: google/flan-t5-large"
```

### Commentary Quality Issues

**Check Logs:**
```powershell
docker exec book-intel-backend-1 cat ../logs/commentary_log.jsonl | tail -n 5
```

**Look for:**
- `commentary_mode: "fallback"` - Model errors
- Short commentary (<50 chars) - Generation issues
- No verse references - Prompt quality

---

## 📝 Structured Logs

### Location
**Inside Container:** `/logs/commentary_log.jsonl`  
**Format:** JSON Lines (one JSON object per line)

### View Logs
```powershell
# Last 10 entries
docker exec book-intel-backend-1 tail -n 10 ../logs/commentary_log.jsonl

# Pretty print last entry
docker exec book-intel-backend-1 tail -n 1 ../logs/commentary_log.jsonl | python -m json.tool
```

### Log Fields
```json
{
  "timestamp": "2025-12-12T13:32:08.241107",
  "query": "forgiveness",
  "verses_retrieved": [...],
  "commentary": "...",
  "commentary_mode": "full|fallback|missing",
  "model_info": {
    "model": "google/flan-t5-large",
    "device": "cpu",
    "verses_referenced": 10
  }
}
```

---

## 🧪 Testing Commands

### Run Full Validation Suite
```powershell
python test_commentary_final.py
```

### Test Specific Query
```powershell
# PowerShell
$result = Invoke-RestMethod -Uri "http://localhost:8000/commentary" `
  -Method Post `
  -Body (@{query="YOUR QUERY"; max_results=10; use_cache=$true} | ConvertTo-Json) `
  -ContentType "application/json"

Write-Host "Commentary: $($result.commentary)"
Write-Host "Mode: $($result.commentary_mode)"
```

### Test Cache Performance
```powershell
# First request (slow)
Measure-Command {
  Invoke-RestMethod -Uri "http://localhost:8000/commentary" `
    -Method Post `
    -Body (@{query="peace"} | ConvertTo-Json) `
    -ContentType "application/json"
}

# Second request (cached - fast)
Measure-Command {
  Invoke-RestMethod -Uri "http://localhost:8000/commentary" `
    -Method Post `
    -Body (@{query="peace"} | ConvertTo-Json) `
    -ContentType "application/json"
}
```

---

## 📁 Key Files

### Backend
- `backend/commentary_summarizer.py` - AI commentary generation
- `backend/app_refactored.py` - API endpoints
- `backend/config.py` - Configuration
- `backend/search_semantic.py` - FAISS semantic search

### Frontend
- `frontend/commentary.js` - Commentary UI logic
- `frontend/index.html` - HTML structure
- `frontend/style.css` - Styling

### Testing
- `test_commentary_final.py` - Validation suite
- `commentary_validation_results.json` - Test results

### Docker
- `docker-compose.yml` - Container orchestration
- `backend/Dockerfile` - Backend image
- `frontend/Dockerfile` - Frontend image

---

## 🎨 Frontend UI

### Commentary Section Location
**Position:** Between search bar and verse results  
**Behavior:** Auto-appears on search, collapsible  

### HTML Structure
```html
<section id="commentarySection">
  <div class="commentary-card">
    <div class="commentary-header">
      <h3>Biblical Commentary</h3>
      <button id="commentaryToggle">−</button>
    </div>
    <div id="commentaryContent">
      <!-- Commentary text appears here -->
    </div>
  </div>
</section>
```

### JavaScript Usage
```javascript
// Trigger commentary generation
window.commentaryManager.generateCommentary("peace", 10);

// Clear commentary
window.commentaryManager.clear();
```

---

## 🔍 Performance Benchmarks

### Response Times (CPU Mode)
- **First request:** 5-9 seconds (model generation)
- **Cached request:** <0.2 seconds (instant)
- **Model loading:** 85 seconds (first run only)

### With GPU (Theoretical)
- **First request:** <1 second (5-10x faster)
- **Cached request:** <0.2 seconds (same)

### Commentary Quality
- **Length:** 150-250 characters (2-3 sentences)
- **Verses used:** 10 (top semantic matches)
- **Success rate:** 100% (7/7 test queries)

---

## 🚨 Common Issues

### Issue: "Commentary unavailable"

**Possible Causes:**
1. Model not loaded yet (check `/commentary/status`)
2. Model generation error (check logs)
3. No relevant verses found (check query)

**Solutions:**
1. Wait for model to load
2. Check backend logs for errors
3. Try different query terms

### Issue: Commentary is generic/poor quality

**Possible Causes:**
1. Query too vague
2. Low-quality semantic matches
3. Model prompt needs tuning

**Solutions:**
1. Use more specific queries
2. Check verse relevance scores in logs
3. Adjust prompt in `commentary_summarizer.py`

---

## 📚 Sample Queries

### Tested & Validated ✅
- "forgiveness"
- "true sabbath day"
- "how to beat addictions"
- "faith without works"
- "love your enemies"
- "do not worry about tomorrow"
- "what is the kingdom of heaven"
- "peace"

### Good Query Patterns
- Theological concepts: "salvation", "grace", "redemption"
- Practical questions: "how to pray", "dealing with fear"
- Doctrine: "trinity", "baptism", "communion"
- Ethics: "lying", "honesty", "integrity"

---

## 🎓 Next Steps

1. **Test on mobile devices** - Verify responsive design
2. **Monitor logs** - Track commentary quality over time
3. **Collect user feedback** - Identify improvement areas
4. **Enable GPU** (optional) - For faster generation
5. **Expand test suite** - Add edge cases

---

**Last Updated:** December 12, 2025  
**Version:** 2.0 (Reinforced Commentary System)  
**Status:** Production Ready ✅
