#!/bin/bash
# =============================================================================
# BioNexus India V2 — Entrypoint Script
# =============================================================================
# This script runs when the API container starts:
#   1. Waits for PostgreSQL to accept connections
#   2. Runs Alembic migrations
#   3. Seeds the database with sample data
#   4. Starts the FastAPI server
# =============================================================================

set -e

echo "=============================================="
echo "  BioNexus India V2 — Container Startup"
echo "=============================================="

# --- Wait for PostgreSQL ---
echo "[1/4] Waiting for PostgreSQL..."
MAX_WAIT=60
WAITED=0

until pg_isready -h db -p 5432 -U bionexus -q 2>/dev/null; do
    WAITED=$((WAITED + 1))
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "ERROR: PostgreSQL did not become ready within ${MAX_WAIT}s"
        exit 1
    fi
    sleep 1
done
echo "      PostgreSQL is ready (waited ${WAITED}s)"

# --- Run Alembic Migrations ---
echo "[2/4] Running database migrations..."
alembic upgrade head
echo "      Migrations complete"

# --- Seed Database ---
echo "[3/4] Seeding database..."
python -m database.seed
echo "      Seeding complete"

# --- Start API Server ---
echo "[4/4] Starting BioNexus India V2 API..."
echo "      Host: ${API_HOST:-0.0.0.0}"
echo "      Port: ${API_PORT:-8000}"
echo "=============================================="

exec uvicorn api.main:app \
    --host "${API_HOST:-0.0.0.0}" \
    --port "${API_PORT:-8000}" \
    --log-level "${LOG_LEVEL:-info}"
