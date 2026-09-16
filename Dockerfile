# ==============================================================================
# Multi-Stage Dockerfile for FinLens (AI Financial Research & RAG Platform)
# Supports: Hugging Face Spaces (16GB RAM Free), Render, Railway, Fly.io, Docker
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
# Stage 2: Production Python Backend Runtime
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runner

WORKDIR /app

# Install system utilities and build dependencies for PyMuPDF and Chroma
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Optimize PyTorch: Install CPU-only wheel (reduces image size by >2 GB)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install backend Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code, documentation, and data directories
COPY backend/ ./backend/
COPY data/ ./data/

# Copy compiled frontend from Stage 1 into the backend's expected directory
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Set permissions for directory writes (SQLite database, ChromaDB, uploads)
RUN mkdir -p /app/data/uploads /app/data/chroma_db && chmod -R 777 /app/data

# Environment settings
ENV PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=7860 \
    DEBUG=False \
    ENVIRONMENT=production

# Hugging Face Spaces uses 7860; Render/Railway pass dynamic $PORT
EXPOSE 7860

# Start production server with dynamic port fallback
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
