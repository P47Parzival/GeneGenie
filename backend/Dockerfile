# =============================================================================
# BioNexus India V2 — Dockerfile
# =============================================================================
# Multi-stage build: slim Python 3.11 image
# =============================================================================

FROM python:3.11-slim AS base

# System deps for psycopg2, reportlab, and crypto
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/raw data/uploads/documents data/uploads/feed_forms

# Make entrypoint executable
RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
