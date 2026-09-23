# ==============================================================================
# Multi-Stage Dockerfile for FinLens (AI Financial Research & RAG Platform)
# Optimized for Free Tiers (Render, Railway - 512MB RAM Limit) & Cloud Platforms
# - Image size: ~350 MB (down from 4.5 GB)
# - Idle RAM: ~100-140 MB (down from 700+ MB)
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build Frontend (React + Vite)
# ------------------------------------------------------------------------------
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Production Python Backend Runtime (Lightweight, No PyTorch in RAM)
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runner

WORKDIR /app

# Install system utilities and build dependencies for PyMuPDF and Chroma
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install backend Python dependencies (lean: no PyTorch, no heavy transformer weights)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code, documentation, and data directories
COPY backend/ ./backend/
COPY data/ ./data/

# Copy compiled frontend from Stage 1 into the backend's expected directory
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Set permissions for directory writes (SQLite database, ChromaDB, uploads)
RUN mkdir -p /app/data/uploads /app/data/chroma_db && chmod -R 777 /app/data

# Memory-conservative environment settings for 512MB RAM free tier
ENV PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=7860 \
    DEBUG=False \
    ENVIRONMENT=production \
    LOW_MEMORY_MODE=true \
    USE_CROSS_ENCODER=false \
    EMBEDDING_PROVIDER=hf_api \
    MALLOC_ARENA_MAX=2 \
    WEB_CONCURRENCY=1 \
    OMP_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false

# Expose default port
EXPOSE 7860

# Start production server with single worker and concurrency limiter to fit within 512MB
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1 --limit-concurrency 20"]
