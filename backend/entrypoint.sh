#!/bin/bash
# =============================================================================
# BioNexus India V1 — Entrypoint Script
# =============================================================================
# Runs on container startup:
#   1. Wait for PostgreSQL to be ready
#   2. Run Alembic migrations
#   3. Seed the database
#   4. Start the API server
# =============================================================================

set -e

echo "=============================================="
echo " BioNexus India V1 — Starting up..."
echo "=============================================="

# --- Wait for PostgreSQL ---
echo "[1/4] Waiting for PostgreSQL to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if python -c "
import psycopg2
try:
    conn = psycopg2.connect('${SYNC_DATABASE_URL}')
    conn.close()
    exit(0)
except:
    exit(1)
" 2>/dev/null; then
        echo "       PostgreSQL is ready!"
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "       Waiting... (attempt $RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "ERROR: PostgreSQL did not become ready in time."
    exit 1
fi

# --- Run Alembic Migrations ---
echo "[2/4] Running database migrations..."
alembic upgrade head
echo "       Migrations complete."

# --- Seed Database ---
echo "[3/4] Seeding database..."
python -m database.seed
echo "       Seeding complete."

# --- Start API Server ---
echo "[4/4] Starting API server..."
echo "=============================================="
echo " BioNexus India V1 is ready!"
echo " API:  http://0.0.0.0:${API_PORT:-8000}"
echo " Docs: http://0.0.0.0:${API_PORT:-8000}/docs"
echo "=============================================="

exec uvicorn api.main:app \
    --host "${API_HOST:-0.0.0.0}" \
    --port "${API_PORT:-8000}" \
    --log-level "${LOG_LEVEL:-info}"
