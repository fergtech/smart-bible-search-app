# Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for torch/numpy
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and modules
COPY backend/*.py .

# Note: kjv_chunks.jsonl and cache/ are mounted via docker-compose volumes
# No need to copy them during build

# Expose API port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app_refactored:app", "--host", "0.0.0.0", "--port", "8000"]
