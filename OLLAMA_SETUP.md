# Setup Guide for FREE Commentary Feature

## Ollama Setup (One-Time, 5 minutes)

### 1. Install Ollama
Download and install from: **https://ollama.ai**

### 2. Pull the Model (one time, ~2GB download)
```powershell
ollama pull llama3.2:3b
```

### 3. Verify it's running
Ollama runs automatically as a service. Test it:
```powershell
ollama list
```

You should see `llama3.2:3b` in the list.

### 4. Done!
The commentary feature will now work automatically.

## Alternative Models (optional)

- **llama3.2:3b** - Default, fast, good quality (~2GB)
- **llama3.2:1b** - Faster, smaller (~1.3GB) 
- **llama3:8b** - Better quality, slower (~4.7GB)
- **phi3:mini** - Microsoft, fast (~2.3GB)

Change model in `.env`:
```
OLLAMA_MODEL=phi3:mini
```

## Cost
**$0.00** - Completely FREE!

## Speed
- First request: ~3-5 seconds
- Cached requests: < 0.1 seconds
